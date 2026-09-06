from __future__ import annotations

from app.core.config import Settings, settings
from app.domain.schemas import (
    ClassificationCategory,
    ClassificationDecision,
    ClassificationInput,
    ClassificationOutput,
    ModelGatewayFailureReason,
    ModelGatewayRequest,
    ModelGatewayStatus,
    ModelRouteConfig,
    PromptReference,
)
from app.services.model_gateway import ModelGateway


class ClassificationService:
    def __init__(
        self,
        *,
        gateway: ModelGateway | None = None,
        app_settings: Settings = settings,
        route: ModelRouteConfig | None = None,
    ) -> None:
        self.settings = app_settings
        self.gateway = gateway or ModelGateway(app_settings=app_settings)
        self.route = route or ModelRouteConfig(
            token_budget=app_settings.model_gateway_token_budget,
            timeout_ms=app_settings.model_gateway_timeout_ms,
            retry_limit=app_settings.model_gateway_retry_limit,
        )

    def classify(self, request: ClassificationInput) -> ClassificationDecision:
        gateway_request = ModelGatewayRequest(
            capability="classification",
            case_id=request.case_id,
            workflow_id=request.workflow_id,
            correlation_id=request.correlation_id,
            prompt=PromptReference(),
            route=self.route,
            response_schema_version="classification-output-v1",
            input_text=self._input_text(request),
            untrusted_inputs={
                "transaction_ref": request.transaction_ref,
                "channel": request.channel.value if request.channel is not None else None,
                "evidence_count": request.evidence_count,
            },
        )
        gateway_response = self.gateway.invoke_classification(gateway_request)
        if gateway_response.status is not ModelGatewayStatus.accepted:
            return ClassificationDecision(
                accepted=False,
                manual_classification_required=True,
                reason=gateway_response.failure_reason,
                threshold=self.settings.classification_confidence_threshold,
                telemetry=gateway_response.telemetry,
                evaluation_metadata=self._evaluation_metadata(None, None),
            )

        output = ClassificationOutput.model_validate(gateway_response.validated_output)
        reason = self._routing_reason(output)
        accepted = reason is None
        return ClassificationDecision(
            accepted=accepted,
            output=output,
            manual_classification_required=not accepted,
            reason=reason,
            threshold=self.settings.classification_confidence_threshold,
            telemetry=gateway_response.telemetry,
            evaluation_metadata=self._evaluation_metadata(output, reason),
        )

    def _routing_reason(self, output: ClassificationOutput) -> ModelGatewayFailureReason | None:
        if output.category is ClassificationCategory.unsupported:
            return ModelGatewayFailureReason.unsupported_category
        if output.confidence < self.settings.classification_confidence_threshold:
            return ModelGatewayFailureReason.low_confidence
        return None

    @staticmethod
    def _input_text(request: ClassificationInput) -> str:
        dispute_hint = request.dispute_type_hint.value if request.dispute_type_hint else ""
        return "\n".join(
            [
                f"description: {request.description}",
                f"dispute_type_hint: {dispute_hint}",
                f"channel: {request.channel.value if request.channel else ''}",
                f"transaction_ref: {request.transaction_ref or ''}",
                f"evidence_count: {request.evidence_count}",
            ]
        )

    def _evaluation_metadata(
        self,
        output: ClassificationOutput | None,
        reason: ModelGatewayFailureReason | None,
    ) -> dict[str, object]:
        return {
            "original_category": output.category.value if output is not None else None,
            "corrected_category": None,
            "original_confidence": output.confidence if output is not None else None,
            "reviewer_rationale": None,
            "schema_version": output.schema_version
            if output is not None
            else "classification-output-v1",
            "prompt_version": output.prompt_version
            if output is not None
            else "classification-router-v1",
            "model_route_version": output.model_route_version
            if output is not None
            else "model-route-classification-v1",
            "routing_reason": reason.value if reason is not None else None,
            "financial_outcome_authorized": False,
        }
