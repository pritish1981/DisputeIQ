from __future__ import annotations

from pprint import pprint
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from app.policy_fixture_loader import synthetic_duplicate_card_retrieval_request


def run_smoke() -> dict[str, object]:
    suffix = uuid4().hex[:8]
    headers = {"X-Policy-Admin": "true", "X-Correlation-ID": f"corr-policy-retrieval-{suffix}"}
    app = create_app()
    with TestClient(app) as client:
        ingestion = client.post(
            "/api/v1/policies/ingestions",
            json=synthetic_duplicate_card_retrieval_request(suffix).model_dump(mode="json"),
            headers=headers,
        )
        ingestion.raise_for_status()
        run = ingestion.json()
        corpus_version = f"retrieval-smoke-corpus-{suffix}"
        index_version = f"retrieval-smoke-index-{suffix}"
        promotion = client.post(
            "/api/v1/policies/promotions",
            json={
                "ingestion_run_id": run["run_id"],
                "actor_ref": "policy-admin:retrieval-smoke",
                "corpus_version": corpus_version,
                "index_version": index_version,
            },
            headers=headers,
        )
        promotion.raise_for_status()
        retrieval = client.post(
            "/api/v1/policies/retrievals",
            json={
                "query": "duplicate card transaction issuer review merchant context",
                "effective_date": "2026-09-04T00:00:00Z",
                "product": "card",
                "channel": "web",
                "jurisdiction": "US",
                "actor_ref": "policy-retrieval:smoke",
                "retrieval_config": {
                    "version": "retrieval-config-smoke-v1",
                    "ambiguity_threshold": 0.0,
                },
            },
            headers=headers,
        )
        retrieval.raise_for_status()
        evaluation = client.post(
            "/api/v1/policies/retrieval-evaluations",
            json={
                "actor_ref": "policy-admin:retrieval-smoke",
                "retrieval_config": {
                    "version": "retrieval-config-smoke-v1",
                    "ambiguity_threshold": 0.0,
                },
            },
            headers=headers,
        )
        evaluation.raise_for_status()
        body = retrieval.json()
        return {
            "path": (
                "promoted corpus -> deterministic eligibility -> PostgreSQL lexical search -> "
                "pgvector similarity -> fusion/rerank -> cited context -> "
                "confidence/audit/evaluation"
            ),
            "run_id": run["run_id"],
            "corpus_version": corpus_version,
            "index_version": index_version,
            "retrieval_config_version": body["retrieval_config"]["version"],
            "selected_citations": [item["citation"] for item in body["results"]],
            "retrieval_status": body["status"],
            "abstention_reason": body["abstention_reason"],
            "telemetry": body["telemetry"],
            "confidence": body["confidence"],
            "correlation_id": body["correlation_id"],
            "audit_event_id": body["audit_event_id"],
            "evaluation": evaluation.json()["evaluation"],
            "excluded_fixture_ids": [
                f"POL-DUP-CARD-STALE-{suffix}",
                f"POL-DUP-CARD-WRONG-PRODUCT-{suffix}",
            ],
        }


if __name__ == "__main__":
    pprint(run_smoke())
