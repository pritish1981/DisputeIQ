from __future__ import annotations

import json
from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from app.core.database import SessionLocal
from app.domain.schemas import CreateCaseRequest, WorkflowStartRequest
from app.services.case_service import CaseService
from app.services.workflow_service import WorkflowService


def main() -> None:
    correlation_id = f"workflow-smoke-{uuid4()}"
    with SessionLocal() as db:
        case_service = CaseService(db)
        workflow_service = WorkflowService(db, case_service=case_service)
        case, _ = case_service.create_case(
            CreateCaseRequest.model_validate(
                {
                    "customer_ref": "cust_1001",
                    "account_ref": "acct_2001",
                    "transaction_ref": "txn_3001",
                    "channel": "web",
                    "description": (
                        "Customer reports a duplicate card transaction at Synthetic Books."
                    ),
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
            ),
            idempotency_key=f"workflow-smoke-case-{uuid4()}",
            correlation_id=correlation_id,
        )
        workflow = workflow_service.start_workflow(
            WorkflowStartRequest(case_id=case.case_id),
            idempotency_key=f"workflow-smoke-start-{uuid4()}",
            correlation_id=correlation_id,
        )
        payload = {
            "case_id": str(workflow.case_id),
            "workflow_id": str(workflow.workflow_id),
            "status": workflow.status,
            "current_node": workflow.current_node,
            "state_version": workflow.state_version,
            "checkpoint_seq": workflow.checkpoint.checkpoint_seq
            if workflow.checkpoint is not None
            else None,
            "correlation_id": workflow.correlation_id,
            "interrupt": workflow.interrupt.model_dump(mode="json"),
            "stage_summaries": workflow.stage_summaries,
            "telemetry": workflow.telemetry.model_dump(mode="json"),
        }
        print(json.dumps(jsonable_encoder(payload), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
