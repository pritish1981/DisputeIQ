from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.adapters.repositories import (
    AuditWriteError,
    IdempotencyConflictError,
    OptimisticLockError,
)
from app.adapters.synthetic_providers import SyntheticProviderError
from app.core.correlation import CORRELATION_HEADER, resolve_correlation_id
from app.core.database import get_db
from app.domain.schemas import (
    CaseListResponse,
    CaseResponse,
    CaseStatus,
    Channel,
    CreateCaseRequest,
    ErrorResponse,
    EvidenceListResponse,
    EvidenceMetadataIn,
    EvidenceRegistrationResponse,
    TimelineResponse,
    parse_if_match,
)
from app.services.case_service import CaseNotFoundError, CaseService

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


def get_case_service(db: Annotated[Session, Depends(get_db)]) -> CaseService:
    return CaseService(db)


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
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_case(
    request: CreateCaseRequest,
    response: Response,
    service: Annotated[CaseService, Depends(get_case_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> CaseResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    try:
        result, _ = service.create_case(request, idempotency_key, correlation_id)
        return result
    except IdempotencyConflictError as exc:
        raise _error(409, "IDEMPOTENCY_CONFLICT", str(exc), correlation_id) from exc
    except SyntheticProviderError as exc:
        raise _error(422, "AUTHORITATIVE_RECORD_NOT_FOUND", str(exc), correlation_id) from exc
    except AuditWriteError as exc:
        raise _error(
            500,
            "AUDIT_APPEND_FAILED",
            "Case creation could not be completed because audit recording failed.",
            correlation_id,
        ) from exc


@router.get("", response_model=CaseListResponse, responses=ERROR_RESPONSES)
def list_cases(
    request: Request,
    response: Response,
    service: Annotated[CaseService, Depends(get_case_service)],
    case_status: Annotated[CaseStatus | None, Query(alias="status")] = None,
    customer_ref: str | None = None,
    transaction_ref: str | None = None,
    channel: Channel | None = None,
    opened_from: datetime | None = None,
    opened_to: datetime | None = None,
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> CaseListResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    supported = {
        "status",
        "customer_ref",
        "transaction_ref",
        "channel",
        "opened_from",
        "opened_to",
    }
    unsupported = sorted(set(request.query_params) - supported)
    if unsupported:
        raise _error(
            422,
            "UNSUPPORTED_FILTER",
            f"Unsupported case filter(s): {', '.join(unsupported)}",
            correlation_id,
        )
    if opened_from is not None and opened_to is not None and opened_from > opened_to:
        raise _error(
            422,
            "VALIDATION_FAILED",
            "opened_from must be before or equal to opened_to",
            correlation_id,
        )
    return service.list_cases(
        status=case_status,
        customer_ref=customer_ref,
        transaction_ref=transaction_ref,
        channel=channel,
        opened_from=opened_from,
        opened_to=opened_to,
    )


@router.get("/{case_id}", response_model=CaseResponse, responses=ERROR_RESPONSES)
def get_case(
    case_id: str,
    response: Response,
    service: Annotated[CaseService, Depends(get_case_service)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> CaseResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    try:
        return service.get_case(case_id)
    except CaseNotFoundError as exc:
        raise _error(404, "CASE_NOT_FOUND", "Case not found", correlation_id) from exc


@router.post(
    "/{case_id}/evidence",
    response_model=EvidenceRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def register_evidence(
    case_id: str,
    request: EvidenceMetadataIn,
    response: Response,
    service: Annotated[CaseService, Depends(get_case_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    if_match: Annotated[str, Header(alias="If-Match", min_length=1)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> EvidenceRegistrationResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    try:
        expected_version = parse_if_match(if_match)
        return service.register_evidence(
            case_id=case_id,
            request=request,
            idempotency_key=idempotency_key,
            expected_version=expected_version,
            correlation_id=correlation_id,
        )
    except ValueError as exc:
        raise _error(422, "INVALID_IF_MATCH", str(exc), correlation_id) from exc
    except CaseNotFoundError as exc:
        raise _error(404, "CASE_NOT_FOUND", "Case not found", correlation_id) from exc
    except IdempotencyConflictError as exc:
        raise _error(409, "IDEMPOTENCY_CONFLICT", str(exc), correlation_id) from exc
    except OptimisticLockError as exc:
        raise _error(409, "OPTIMISTIC_LOCK_CONFLICT", str(exc), correlation_id) from exc
    except AuditWriteError as exc:
        raise _error(
            500,
            "AUDIT_APPEND_FAILED",
            "Evidence registration could not be completed because audit recording failed.",
            correlation_id,
        ) from exc


@router.get(
    "/{case_id}/evidence",
    response_model=EvidenceListResponse,
    responses=ERROR_RESPONSES,
)
def list_evidence(
    case_id: str,
    response: Response,
    service: Annotated[CaseService, Depends(get_case_service)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> EvidenceListResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    try:
        return service.list_evidence(case_id)
    except CaseNotFoundError as exc:
        raise _error(404, "CASE_NOT_FOUND", "Case not found", correlation_id) from exc


@router.get(
    "/{case_id}/timeline",
    response_model=TimelineResponse,
    responses=ERROR_RESPONSES,
)
def get_timeline(
    case_id: str,
    response: Response,
    service: Annotated[CaseService, Depends(get_case_service)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> TimelineResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    try:
        return service.get_timeline(case_id)
    except CaseNotFoundError as exc:
        raise _error(404, "CASE_NOT_FOUND", "Case not found", correlation_id) from exc
