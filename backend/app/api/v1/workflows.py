from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.adapters.control_repository import ControlConfigurationError, ControlRepository
from app.adapters.repositories import (
    IdempotencyConflictError,
    WorkflowConflictError,
    WorkflowRunNotFoundError,
)
from app.core.config import settings
from app.core.correlation import CORRELATION_HEADER, resolve_correlation_id
from app.core.database import get_db
from app.domain.controls import CONTROL_GRAPH_VERSION, ControlEvaluationList, ControlEvaluationOut
from app.domain.schemas import (
    ErrorResponse,
    WorkflowResponse,
    WorkflowResumeRequest,
    WorkflowStartRequest,
    parse_if_match,
)
from app.services.case_service import CaseNotFoundError
from app.services.workflow_service import WorkflowAuditError, WorkflowService

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


def get_workflow_service(db: Annotated[Session, Depends(get_db)]) -> WorkflowService:
    return WorkflowService(db)


def require_control_reader(
    x_control_reader: Annotated[str | None, Header(alias="X-Control-Reader")] = None,
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> None:
    # Matches the pilot's explicit policy-admin header convention; never production identity.
    if settings.app_env not in {"local", "test"} or x_control_reader != "true":
        raise _error(
            403,
            "CONTROL_ACCESS_DENIED",
            "Local control reader access required",
            resolve_correlation_id(x_correlation_id),
        )


@router.get(
    "/{workflow_id}/control-evaluations",
    response_model=ControlEvaluationList,
    dependencies=[Depends(require_control_reader)],
    responses=ERROR_RESPONSES,
)
def list_control_evaluations(
    workflow_id: UUID,
    response: Response,
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> ControlEvaluationList:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    try:
        service.get_workflow(workflow_id)
        return ControlEvaluationList(items=ControlRepository(service.db).list(str(workflow_id)))
    except WorkflowRunNotFoundError as exc:
        raise _error(404, "WORKFLOW_NOT_FOUND", "Workflow not found", correlation_id) from exc
    except ControlConfigurationError as exc:
        raise _error(409, "CONTROL_INTEGRITY_ERROR", str(exc), correlation_id) from exc


@router.get(
    "/{workflow_id}/control-evaluations/{evaluation_id}",
    response_model=ControlEvaluationOut,
    dependencies=[Depends(require_control_reader)],
    responses=ERROR_RESPONSES,
)
def get_control_evaluation(
    workflow_id: UUID,
    evaluation_id: UUID,
    response: Response,
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> ControlEvaluationOut:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    repository = ControlRepository(service.db)
    try:
        return repository.output(repository.get(str(workflow_id), str(evaluation_id)))
    except LookupError as exc:
        raise _error(
            404, "EVALUATION_NOT_FOUND", "Control evaluation not found", correlation_id
        ) from exc
    except ControlConfigurationError as exc:
        raise _error(409, "CONTROL_INTEGRITY_ERROR", str(exc), correlation_id) from exc


def _error(status_code: int, code: str, message: str, correlation_id: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": code,
            "message": message,
            "correlation_id": correlation_id,
            "details": [],
        },
    )


@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
def start_workflow(
    request: WorkflowStartRequest,
    response: Response,
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
    x_control_reader: Annotated[str | None, Header(alias="X-Control-Reader")] = None,
) -> WorkflowResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    if request.graph_version == CONTROL_GRAPH_VERSION:
        require_control_reader(x_control_reader, correlation_id)
    try:
        return service.start_workflow(
            request,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
    except CaseNotFoundError as exc:
        raise _error(404, "CASE_NOT_FOUND", "Case not found", correlation_id) from exc
    except IdempotencyConflictError as exc:
        raise _error(409, "IDEMPOTENCY_CONFLICT", str(exc), correlation_id) from exc
    except WorkflowConflictError as exc:
        raise _error(409, "WORKFLOW_CONFLICT", str(exc), correlation_id) from exc
    except WorkflowAuditError as exc:
        raise _error(500, "WORKFLOW_AUDIT_APPEND_FAILED", str(exc), correlation_id) from exc


@router.get("/{workflow_id}", response_model=WorkflowResponse, responses=ERROR_RESPONSES)
def get_workflow(
    workflow_id: UUID,
    response: Response,
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> WorkflowResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    try:
        return service.get_workflow(workflow_id)
    except WorkflowRunNotFoundError as exc:
        raise _error(404, "WORKFLOW_NOT_FOUND", "Workflow not found", correlation_id) from exc


@router.post(
    "/{workflow_id}/resume",
    response_model=WorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
def resume_workflow(
    workflow_id: UUID,
    request: WorkflowResumeRequest,
    response: Response,
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    if_match: Annotated[str, Header(alias="If-Match", min_length=1)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
    x_control_reader: Annotated[str | None, Header(alias="X-Control-Reader")] = None,
) -> WorkflowResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    try:
        if service.get_workflow(workflow_id).graph_version == CONTROL_GRAPH_VERSION:
            require_control_reader(x_control_reader, correlation_id)
        return service.resume_workflow(
            workflow_id,
            request,
            idempotency_key=idempotency_key,
            expected_version=parse_if_match(if_match),
            correlation_id=correlation_id,
        )
    except ControlConfigurationError as exc:
        raise _error(409, "CONTROL_INTEGRITY_ERROR", str(exc), correlation_id) from exc
    except ValueError as exc:
        raise _error(422, "INVALID_IF_MATCH", str(exc), correlation_id) from exc
    except IdempotencyConflictError as exc:
        raise _error(409, "IDEMPOTENCY_CONFLICT", str(exc), correlation_id) from exc
    except WorkflowRunNotFoundError as exc:
        raise _error(404, "WORKFLOW_NOT_FOUND", "Workflow not found", correlation_id) from exc
    except WorkflowConflictError as exc:
        raise _error(409, "WORKFLOW_CONFLICT", str(exc), correlation_id) from exc
    except WorkflowAuditError as exc:
        raise _error(500, "WORKFLOW_AUDIT_APPEND_FAILED", str(exc), correlation_id) from exc
