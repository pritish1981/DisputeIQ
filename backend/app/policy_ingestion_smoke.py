from __future__ import annotations

from pprint import pprint

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.models import Base
from app.api.v1.policies import get_policy_service
from app.main import create_app
from app.policy_fixture_loader import synthetic_duplicate_card_policy_request
from app.services.policy_ingestion import PolicyIngestionService


def run_smoke() -> dict[str, object]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = session_factory()
    app = create_app()
    app.dependency_overrides[get_policy_service] = lambda: PolicyIngestionService(session)
    headers = {"X-Policy-Admin": "true", "X-Correlation-ID": "corr-policy-smoke"}
    with TestClient(app) as client:
        ingestion = client.post(
            "/api/v1/policies/ingestions",
            json=synthetic_duplicate_card_policy_request().model_dump(mode="json"),
            headers=headers,
        )
        ingestion.raise_for_status()
        run = ingestion.json()
        promotion = client.post(
            "/api/v1/policies/promotions",
            json={
                "ingestion_run_id": run["run_id"],
                "actor_ref": "policy-admin:smoke",
                "corpus_version": "smoke-corpus",
                "index_version": "smoke-index",
            },
            headers=headers,
        )
        promotion.raise_for_status()
        chunk = run["documents"][0]["chunks"][0]
        lineage = client.get(
            f"/api/v1/policies/chunks/{chunk['chunk_id']}/lineage",
            headers=headers,
        )
        lineage.raise_for_status()
        return {
            "path": (
                "validated -> chunked -> embedded -> indexed -> evaluated -> promoted -> audited"
            ),
            "run_id": run["run_id"],
            "run_status": run["status"],
            "corpus_version": promotion.json()["corpus_version"],
            "index_version": promotion.json()["index_version"],
            "promoted": promotion.json()["promoted"],
            "correlation_id": promotion.json()["correlation_id"],
            "chunk_id": chunk["chunk_id"],
            "lineage": lineage.json(),
            "audit_events": [event["event_type"] for event in run["audit_events"]],
        }


if __name__ == "__main__":
    pprint(run_smoke())
