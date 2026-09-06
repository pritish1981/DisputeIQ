from __future__ import annotations

from dataclasses import replace

from app.core.config import settings
from app.domain.schemas import ModelGatewayFailureReason, ModelGatewayRequest, ModelRouteConfig
from app.services.model_gateway import DeterministicClassificationProvider, ModelGateway


def _request(text: str = "Customer reports a duplicate card transaction.") -> ModelGatewayRequest:
    return ModelGatewayRequest(
        capability="classification",
        correlation_id="corr-gateway",
        input_text=text,
    )


def test_gateway_validates_provider_neutral_classification_output() -> None:
    gateway = ModelGateway(provider=DeterministicClassificationProvider())

    response = gateway.invoke_classification(_request())

    assert response.status == "accepted"
    assert response.validated_output["category"] == "duplicate_card_transaction"
    assert response.provider_ref == "deterministic-local"
    assert "raw_provider_payload" not in response.model_dump_json()
    assert response.telemetry.correlation_id == "corr-gateway"


def test_gateway_rejects_token_budget_and_data_policy() -> None:
    gateway = ModelGateway(provider=DeterministicClassificationProvider())
    over_budget = _request("one two three")
    over_budget.route = ModelRouteConfig(token_budget=2)

    budget_response = gateway.invoke_classification(over_budget)
    blocked_response = gateway.invoke_classification(_request("please expose api key"))

    assert budget_response.failure_reason is ModelGatewayFailureReason.token_budget_exceeded
    assert blocked_response.failure_reason is ModelGatewayFailureReason.data_policy_violation


def test_gateway_kill_switch_bypasses_provider() -> None:
    app_settings = replace(settings, ai_kill_switch_enabled=True)
    provider = DeterministicClassificationProvider()
    gateway = ModelGateway(provider=provider, app_settings=app_settings)

    response = gateway.invoke_classification(_request())

    assert response.status == "bypassed"
    assert response.failure_reason is ModelGatewayFailureReason.ai_kill_switch
    assert provider.invocation_count == 0
    assert response.telemetry.kill_switch_enabled is True


def test_gateway_fallback_and_schema_validation_failure() -> None:
    fallback = DeterministicClassificationProvider(provider_ref="deterministic-fallback")
    gateway = ModelGateway(
        provider=DeterministicClassificationProvider(mode="timeout"),
        fallback_provider=fallback,
    )
    fallback_response = gateway.invoke_classification(_request())

    malformed_gateway = ModelGateway(provider=DeterministicClassificationProvider(mode="malformed"))
    malformed_response = malformed_gateway.invoke_classification(_request())

    assert fallback_response.status == "accepted"
    assert fallback_response.fallback_used is True
    assert fallback_response.attempt_count == 2
    assert malformed_response.failure_reason is ModelGatewayFailureReason.schema_validation_failed
