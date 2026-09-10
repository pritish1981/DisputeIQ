from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.control_repository import ControlConfigurationError
from app.adapters.models import ControlConfigModel
from app.adapters.repositories import PolicyAuditRepository
from app.domain.controls import ControlProfile, digest


class ControlRegistry:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, profile: ControlProfile, actor_ref: str) -> ControlConfigModel:
        # A local controlled loader, not a public endpoint. Do not trust a caller's `passed` flag.
        from app.control_regression import evaluate_profile

        if not actor_ref.strip():
            raise ControlConfigurationError("Registry actor required")
        report = evaluate_profile(profile)
        if not report["passed"]:
            raise ControlConfigurationError(f"CONTROL_REGRESSION_FAILED:{report['failures']}")
        existing = self.db.scalar(
            select(ControlConfigModel).where(
                ControlConfigModel.profile_id == profile.profile_id,
                ControlConfigModel.version == profile.version,
            )
        )
        if existing:
            if existing.content_hash != digest(profile):
                raise ControlConfigurationError("IMMUTABLE_CONFIGURATION_CONFLICT")
            return existing
        at = datetime.now(UTC)
        row = ControlConfigModel(
            config_id=str(uuid4()),
            profile_id=profile.profile_id,
            version=profile.version,
            environment=profile.environment,
            content_hash=digest(profile),
            payload=profile.model_dump(mode="json"),
            regression=report,
            actor_ref=actor_ref,
            created_at=at,
        )
        self.db.add(row)
        PolicyAuditRepository(self.db).append(
            event_type="CONTROL_CONFIG_REGISTERED",
            actor_ref=actor_ref,
            source="control-registry-loader",
            decision_status="registered",
            correlation_id=f"control-config:{row.config_id}",
            now=at,
            metadata={
                "config_id": row.config_id,
                "content_hash": row.content_hash,
                "version": row.version,
                "approval_ref": profile.approval_ref,
                "regression": report,
            },
        )
        self.db.flush()
        return row
