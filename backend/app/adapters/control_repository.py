from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.models import (
    ConfidenceEvaluationModel,
    ControlConfigModel,
    ControlEvaluationModel,
    ControlRequestFulfillmentModel,
    ControlReviewRequestModel,
    ControlStageColumns,
    EvidenceAssessmentModel,
    PolicyEligibilityModel,
    RuleExecutionModel,
)
from app.domain.controls import (
    ControlEvaluationOut,
    ControlProfile,
    EvaluationBundle,
    EvidenceItem,
    ReviewRequestOut,
    digest,
    utc,
)

STAGES: dict[
    str,
    type[EvidenceAssessmentModel]
    | type[PolicyEligibilityModel]
    | type[RuleExecutionModel]
    | type[ConfidenceEvaluationModel],
] = {
    "evidence": EvidenceAssessmentModel,
    "policy": PolicyEligibilityModel,
    "rules": RuleExecutionModel,
    "confidence": ConfidenceEvaluationModel,
}


class ControlConfigurationError(ValueError):
    pass


class ControlRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def profile(self, config_id: str) -> ControlProfile:
        row = self.db.get(ControlConfigModel, config_id)
        if row is None:
            raise ControlConfigurationError("PINNED_CONFIGURATION_UNAVAILABLE")
        profile = ControlProfile.model_validate(row.payload)
        if digest(profile) != row.content_hash:
            raise ControlConfigurationError("CONFIGURATION_INTEGRITY_MISMATCH")
        return profile

    def resolve(
        self,
        *,
        environment: str,
        dispute_type: str,
        product: str,
        channel: str,
        jurisdiction: str,
        at: datetime,
    ) -> tuple[str, ControlProfile]:
        candidates = []
        for row in self.db.scalars(
            select(ControlConfigModel).where(ControlConfigModel.environment == environment)
        ):
            profile = self.profile(row.config_id)
            if (
                profile.dispute_type == dispute_type
                and profile.product == product
                and (
                    channel in profile.channels
                    and jurisdiction in profile.jurisdictions
                    and profile.effective_from <= utc(at)
                    and (profile.effective_to is None or utc(at) <= profile.effective_to)
                )
            ):
                candidates.append((row.config_id, profile))
        if len(candidates) != 1:
            raise ControlConfigurationError("NO_UNIQUE_APPROVED_CONTROL_PROFILE")
        return candidates[0]

    def get(self, workflow_id: str, evaluation_id: str) -> ControlEvaluationModel:
        row = self.db.scalar(
            select(ControlEvaluationModel).where(
                ControlEvaluationModel.workflow_id == workflow_id,
                ControlEvaluationModel.evaluation_id == evaluation_id,
            )
        )
        if row is None:
            raise LookupError("Control evaluation not found in this workflow")
        self.verify(row)
        return row

    def verify(self, row: ControlEvaluationModel) -> None:
        bundle = EvaluationBundle.model_validate(row.bundle)
        if (
            digest(bundle) != row.bundle_hash
            or digest(row.inputs) != bundle.inputs_hash
            or digest(row.inputs["facts"]) != bundle.facts_hash
            or digest(
                [EvidenceItem.model_validate(i) for i in cast(list[Any], row.inputs["evidence"])]
            )
            != bundle.evidence_hash
            or digest(row.inputs["classification"]) != bundle.classification_hash
        ):
            raise ControlConfigurationError("EVALUATION_INTEGRITY_MISMATCH")

    def stage(self, evaluation_id: str, stage: str) -> dict[str, Any] | None:
        model = STAGES[stage]
        row = cast(
            ControlStageColumns | None,
            self.db.scalar(select(model).where(model.evaluation_id == evaluation_id)),
        )
        if row is None:
            return None
        if digest(row.result) != row.result_hash:
            raise ControlConfigurationError("CONTROL_RESULT_INTEGRITY_MISMATCH")
        return row.result

    def add_stage(
        self,
        evaluation: ControlEvaluationModel,
        stage: str,
        result: dict[str, Any],
        at: datetime,
    ) -> str:
        model = STAGES[stage]
        existing = cast(
            ControlStageColumns | None,
            self.db.scalar(select(model).where(model.evaluation_id == evaluation.evaluation_id)),
        )
        if existing:
            if existing.result_hash != digest(result):
                raise ControlConfigurationError("IMMUTABLE_RESULT_CONFLICT")
            return existing.result_id
        row = model(
            result_id=str(uuid4()),
            evaluation_id=evaluation.evaluation_id,
            result=result,
            result_hash=digest(result),
            correlation_id=evaluation.correlation_id,
            created_at=at,
        )
        self.db.add(row)
        self.db.flush()
        return row.result_id

    def output(self, evaluation: ControlEvaluationModel) -> ControlEvaluationOut:
        self.verify(evaluation)
        stages = {
            name: result
            for name in STAGES
            if (result := self.stage(evaluation.evaluation_id, name)) is not None
        }
        requests = []
        for row in self.db.scalars(
            select(ControlReviewRequestModel)
            .where(ControlReviewRequestModel.evaluation_id == evaluation.evaluation_id)
            .order_by(ControlReviewRequestModel.kind)
        ):
            fulfilled = self.db.get(ControlRequestFulfillmentModel, row.request_id)
            requests.append(
                ReviewRequestOut(
                    request_id=row.request_id,
                    kind=row.kind,
                    required_role=row.required_role,
                    reasons=row.reasons,
                    required_items=row.required_items,
                    status="FULFILLED" if fulfilled else "OPEN",
                    fulfilled_by=fulfilled.evaluation_id if fulfilled else None,
                )
            )
        return ControlEvaluationOut(
            evaluation_id=evaluation.evaluation_id,
            bundle=EvaluationBundle.model_validate(evaluation.bundle),
            stages=stages,
            requests=requests,
        )

    def list(self, workflow_id: str) -> list[ControlEvaluationOut]:
        return [
            self.output(row)
            for row in self.db.scalars(
                select(ControlEvaluationModel)
                .where(ControlEvaluationModel.workflow_id == workflow_id)
                .order_by(
                    ControlEvaluationModel.state_version, ControlEvaluationModel.evaluation_id
                )
            )
        ]
