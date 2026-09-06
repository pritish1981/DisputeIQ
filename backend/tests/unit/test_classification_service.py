from __future__ import annotations

from dataclasses import replace

from app.core.config import settings
from app.domain.schemas import ClassificationInput, ModelGatewayFailureReason, ModelRouteConfig
from app.services.classification import ClassificationService
from app.services.model_gateway import DeterministicClassificationProvider, ModelGateway


def _classification_input(description: str) -> ClassificationInput:
    return ClassificationInput(
        description=description,
        transaction_ref="txn_3001",
        channel="web",
        evidence_count=1,
        correlation_id="corr-classification",
    )


def test_classification_service_accepts_three_supported_categories() -> None:
    service = ClassificationService()

    duplicate = service.classify(_classification_input("duplicate card transaction"))
    upi = service.classify(_classification_input("failed UPI transfer not credited"))
    atm = service.classify(_classification_input("ATM debit happened but cash was not dispensed"))

    assert duplicate.accepted is True
    assert duplicate.output is not None
    assert duplicate.output.category == "duplicate_card_transaction"
    assert upi.output is not None
    assert upi.output.category == "failed_upi_transfer"
    assert atm.output is not None
    assert atm.output.category == "atm_debit_without_cash"


def test_classification_service_routes_manual_for_low_confidence_unsupported_and_malformed() -> (
    None
):
    low = ClassificationService(
        gateway=ModelGateway(provider=DeterministicClassificationProvider(mode="low_confidence"))
    ).classify(_classification_input("duplicate card transaction"))
    unsupported = ClassificationService().classify(_classification_input("travel booking problem"))
    malformed = ClassificationService(
        gateway=ModelGateway(provider=DeterministicClassificationProvider(mode="malformed"))
    ).classify(_classification_input("duplicate card transaction"))

    assert low.manual_classification_required is True
    assert low.reason is ModelGatewayFailureReason.low_confidence
    assert unsupported.manual_classification_required is True
    assert unsupported.reason is ModelGatewayFailureReason.unsupported_category
    assert malformed.manual_classification_required is True
    assert malformed.reason is ModelGatewayFailureReason.schema_validation_failed


def test_classification_service_routes_manual_for_kill_switch_and_missing_config() -> None:
    killed = ClassificationService(app_settings=replace(settings, ai_kill_switch_enabled=True))
    disabled = ClassificationService(route=ModelRouteConfig(enabled=False))

    killed_result = killed.classify(_classification_input("duplicate card transaction"))
    disabled_result = disabled.classify(_classification_input("duplicate card transaction"))

    assert killed_result.reason is ModelGatewayFailureReason.ai_kill_switch
    assert disabled_result.reason is ModelGatewayFailureReason.missing_configuration
    assert killed_result.evaluation_metadata["financial_outcome_authorized"] is False
