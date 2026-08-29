from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.adapters.repositories import AuditWriteError, IdempotencyConflictError
from app.adapters.synthetic_providers import SyntheticProviderError
from app.core.correlation import CORRELATION_HEADER, resolve_correlation_id
from app.core.database import get_db
from app.domain.schemas import CreateDisputeRequest, DisputeCaseResponse, ErrorResponse
from app.services.case_service import CaseNotFoundError, CaseService

router = APIRouter(prefix="/api/v1/disputes", tags=["disputes"])


def get_case_service(db: Annotated[Session, Depends(get_db)]) -> CaseService:
    return CaseService(db)


@router.post(
    "",
    response_model=DisputeCaseResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse},
        422: {"description": "Field-level validation error"},
    },
)
def create_dispute(
    request: CreateDisputeRequest,
    response: Response,
    service: Annotated[CaseService, Depends(get_case_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> DisputeCaseResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    try:
        result, replayed = service.create_case(request, idempotency_key, correlation_id)
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "IDEMPOTENCY_CONFLICT",
                "message": str(exc),
                "correlation_id": correlation_id,
            },
        ) from exc
    except SyntheticProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "AUTHORITATIVE_RECORD_NOT_FOUND",
                "message": str(exc),
                "correlation_id": correlation_id,
            },
        ) from exc
    except AuditWriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "AUDIT_APPEND_FAILED",
                "message": "Case creation could not be completed because audit recording failed.",
                "correlation_id": correlation_id,
            },
        ) from exc

    if replayed:
        response.status_code = status.HTTP_201_CREATED
    return result


@router.get("/{case_id}", response_model=DisputeCaseResponse)
def get_dispute(
    case_id: str,
    service: Annotated[CaseService, Depends(get_case_service)],
) -> DisputeCaseResponse:
    try:
        return service.get_case(case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
