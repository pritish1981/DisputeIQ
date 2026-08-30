from __future__ import annotations

from pathlib import Path


def test_phase_002_migration_covers_required_persistence_fields() -> None:
    migration = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "20260830_0002_case_api_persistence.py"
    ).read_text(encoding="utf-8")
    required_tokens = [
        "channel_metadata",
        "state_version",
        "opened_at",
        "closed_at",
        "replay_count",
        "evidence_type",
        "registered_at",
        "state_version",
        "ix_cases_customer_ref",
        "ix_cases_opened_at",
        "ix_evidence_case_registered",
    ]
    assert all(token in migration for token in required_tokens)
