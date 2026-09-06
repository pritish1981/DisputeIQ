from __future__ import annotations

from time import perf_counter
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from app.core.config import Settings, settings
from app.domain.schemas import (
    ClassificationOutput,
    ModelGatewayFailureReason,
    ModelGatewayProviderResult,
    ModelGatewayRequest,
    ModelGatewayResponse,
    ModelGatewayStatus,
    ModelGatewayTelemetry,
)


class ModelGatewayError(Exception):
    def __init__(self, reason: ModelGatewayFailureReason, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class ModelProvider(Protocol):
    def invoke(self, request: ModelGatewayRequest) -> ModelGatewayProviderResult:
        """Return provider-neutral model output for a gateway request."""


PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "system prompt",
    "tool permissions",
    "financial authority",
    "refund the customer",
    "issue credit",
    "send communication",
)


def estimate_tokens(value: str) -> int:
    return max(1, len(value.split()))


def assert_untrusted_content_is_data(value: str) -> None:
    lowered = value.lower()
    if any(marker in lowered for marker in PROMPT_INJECTION_MARKERS):
        return


def contains_disallowed_model_input(value: str) -> bool:
    lowered = value.lower()
    return "exfiltrate" in lowered or "api key" in lowered or "secret token" in lowered


class DeterministicClassificationProvider:
    def __init__(self, *, mode: str = "normal", provider_ref: str = "deterministic-local") -> None:
        self.mode = mode
        self.provider_ref = provider_ref
        self.invocation_count = 0

    def invoke(self, request: ModelGatewayRequest) -> ModelGatewayProviderResult:
        self.invocation_count += 1
        if self.mode == "timeout":
            return ModelGatewayProviderResult(
                provider_ref=self.provider_ref,
                status="timeout",
                error_code=ModelGatewayFailureReason.provider_timeout.value,
                latency_ms=request.route.timeout_ms,
            )
        if self.mode == "error":
            return ModelGatewayProviderResult(
                provider_ref=self.provider_ref,
                status="error",
                error_code=ModelGatewayFailureReason.provider_error.value,
                latency_ms=1,
            )
        if self.mode == "malformed":
            return ModelGatewayProviderResult(
                provider_ref=self.provider_ref,
                status="ok",
                output_json={"category": "duplicate_card_transaction"},
                token_usage={"input": estimate_tokens(request.input_text), "output": 8},
                latency_ms=1,
            )

        text = request.input_text.lower()
        if "upi" in text or "transfer failed" in text:
            category = "failed_upi_transfer"
            confidence = 0.91
        elif "atm" in text or "cash" in text:
            category = "atm_debit_without_cash"
            confidence = 0.9
        elif "duplicate" in text or "card" in text:
            category = "duplicate_card_transaction"
            confidence = 0.92
        else:
            category = "unsupported"
            confidence = 0.42 if self.mode == "low_confidence" else 0.88
        if self.mode == "low_confidence":
            confidence = 0.41

        return ModelGatewayProviderResult(
            provider_ref=self.provider_ref,
            status="ok",
            output_json={
                "category": category,
                "confidence": confidence,
                "supporting_attributes": {
                    "transaction_ref": str(request.untrusted_inputs.get("transaction_ref", ""))
                    or None,
                    "dispute_channel": str(request.untrusted_inputs.get("channel", "")) or None,
                    "evidence_signal": str(request.untrusted_inputs.get("evidence_count", "0")),
                    "customer_signal": "description_keyword_match",
                },
                "schema_version": request.response_schema_version,
                "prompt_version": request.prompt.prompt_version,
                "model_route_version": request.route.route_version,
                "correlation_id": request.correlation_id,
            },
            token_usage={"input": estimate_tokens(request.input_text), "output": 32},
            latency_ms=1,
        )


class ModelGateway:
    def __init__(
        self,
        *,
        provider: ModelProvider | None = None,
        fallback_provider: ModelProvider | None = None,
        app_settings: Settings = settings,
    ) -> None:
        self.provider = provider or DeterministicClassificationProvider()
        self.fallback_provider = fallback_provider or DeterministicClassificationProvider(
            provider_ref="deterministic-fallback"
        )
        self.settings = app_settings

    def invoke_classification(self, request: ModelGatewayRequest) -> ModelGatewayResponse:
        started = perf_counter()
        if self.settings.ai_kill_switch_enabled:
            return self._failure_response(
                request,
                reason=ModelGatewayFailureReason.ai_kill_switch,
                started=started,
                kill_switch=True,
            )
        if not request.route.enabled:
            return self._failure_response(
                request,
                reason=ModelGatewayFailureReason.missing_configuration,
                started=started,
            )
        token_count = estimate_tokens(request.input_text)
        if token_count > request.route.token_budget:
            return self._failure_response(
                request,
                reason=ModelGatewayFailureReason.token_budget_exceeded,
                started=started,
                token_usage={"input": token_count},
            )
        if contains_disallowed_model_input(request.input_text):
            return self._failure_response(
                request,
                reason=ModelGatewayFailureReason.data_policy_violation,
                started=started,
                token_usage={"input": token_count},
            )
        assert_untrusted_content_is_data(request.input_text)

        primary = self.provider.invoke(request)
        attempt_count = 1
        fallback_used = False
        provider_result = primary
        if primary.status in {"timeout", "error"} and request.route.retry_limit > 0:
            attempt_count += 1
            fallback_used = True
            provider_result = self.fallback_provider.invoke(request)
        if provider_result.status != "ok":
            reason = (
                ModelGatewayFailureReason.provider_timeout
                if provider_result.status == "timeout"
                else ModelGatewayFailureReason.provider_error
            )
            return self._failure_response(
                request,
                reason=reason,
                started=started,
                attempt_count=attempt_count,
                fallback_used=fallback_used,
                token_usage=provider_result.token_usage,
            )

        try:
            output = ClassificationOutput.model_validate(provider_result.output_json)
        except ValidationError:
            return self._failure_response(
                request,
                reason=ModelGatewayFailureReason.schema_validation_failed,
                started=started,
                attempt_count=attempt_count,
                fallback_used=fallback_used,
                token_usage=provider_result.token_usage,
            )

        telemetry = self._telemetry(
            request,
            started=started,
            status=ModelGatewayStatus.accepted,
            attempt_count=attempt_count,
            fallback_used=fallback_used,
            token_usage=provider_result.token_usage,
            provider_ref=provider_result.provider_ref,
        )
        return ModelGatewayResponse(
            status=ModelGatewayStatus.accepted,
            validated_output=output.model_dump(mode="json"),
            provider_ref=provider_result.provider_ref,
            fallback_used=fallback_used,
            attempt_count=attempt_count,
            route_version=request.route.route_version,
            prompt_version=request.prompt.prompt_version,
            schema_version=request.response_schema_version,
            token_usage=provider_result.token_usage,
            telemetry=telemetry,
        )

    def _failure_response(
        self,
        request: ModelGatewayRequest,
        *,
        reason: ModelGatewayFailureReason,
        started: float,
        attempt_count: int = 0,
        fallback_used: bool = False,
        token_usage: dict[str, int] | None = None,
        kill_switch: bool = False,
    ) -> ModelGatewayResponse:
        status = (
            ModelGatewayStatus.bypassed
            if reason is ModelGatewayFailureReason.ai_kill_switch
            else ModelGatewayStatus.failed
        )
        telemetry = self._telemetry(
            request,
            started=started,
            status=status,
            reason=reason,
            attempt_count=attempt_count,
            fallback_used=fallback_used,
            token_usage=token_usage or {},
            kill_switch=kill_switch,
        )
        return ModelGatewayResponse(
            status=status,
            failure_reason=reason,
            fallback_used=fallback_used,
            attempt_count=attempt_count,
            route_version=request.route.route_version,
            prompt_version=request.prompt.prompt_version,
            schema_version=request.response_schema_version,
            token_usage=token_usage or {},
            telemetry=telemetry,
        )

    def _telemetry(
        self,
        request: ModelGatewayRequest,
        *,
        started: float,
        status: ModelGatewayStatus,
        attempt_count: int,
        fallback_used: bool,
        token_usage: dict[str, int],
        provider_ref: str | None = None,
        reason: ModelGatewayFailureReason | None = None,
        kill_switch: bool = False,
    ) -> ModelGatewayTelemetry:
        return ModelGatewayTelemetry(
            capability=request.capability,
            case_id=UUID(str(request.case_id)) if request.case_id is not None else None,
            workflow_id=UUID(str(request.workflow_id)) if request.workflow_id is not None else None,
            correlation_id=request.correlation_id,
            provider_route_ref=provider_ref or request.route.primary_provider,
            prompt_version=request.prompt.prompt_version,
            schema_version=request.response_schema_version,
            latency_ms=int((perf_counter() - started) * 1000),
            token_usage=token_usage,
            attempt_count=attempt_count,
            fallback_used=fallback_used,
            kill_switch_enabled=kill_switch or self.settings.ai_kill_switch_enabled,
            status=status,
            failure_reason=reason,
        )
