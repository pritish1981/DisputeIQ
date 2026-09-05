from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.models import Base
from app.api.v1.disputes import get_case_service
from app.api.v1.policies import get_policy_retrieval_service, get_policy_service
from app.api.v1.workflows import get_workflow_service
from app.main import create_app
from app.services.case_service import CaseService
from app.services.policy_ingestion import PolicyIngestionService
from app.services.policy_retrieval import PolicyRetrievalService
from app.services.workflow_service import WorkflowService


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with TestingSessionLocal() as session:
        yield session


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_case_service() -> CaseService:
        return CaseService(db_session)

    app.dependency_overrides[get_case_service] = override_case_service
    app.dependency_overrides[get_policy_service] = lambda: PolicyIngestionService(db_session)
    app.dependency_overrides[get_policy_retrieval_service] = lambda: PolicyRetrievalService(
        db_session
    )
    app.dependency_overrides[get_workflow_service] = lambda: WorkflowService(db_session)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def valid_payload() -> dict[str, object]:
    return {
        "customer_ref": "cust_1001",
        "account_ref": "acct_2001",
        "transaction_ref": "txn_3001",
        "channel": "web",
        "description": "Customer reports a duplicate card transaction at Synthetic Books.",
        "dispute_type": "duplicate_card_transaction",
        "evidence_metadata": [
            {
                "file_name": "receipt.png",
                "content_type": "image/png",
                "size_bytes": 1204,
                "checksum_sha256": "a" * 64,
                "uploader_ref": "customer:cust_1001",
            }
        ],
    }
