from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.adapters.repositories import (
    AuditWriteError,
    PolicyPromotionError,
    PolicyRunNotFoundError,
    PolicyVersionConflictError,
)
from app.core.correlation import CORRELATION_HEADER, resolve_correlation_id
from app.core.database import get_db
from app.domain.schemas import (
    ErrorResponse,
    PolicyIngestionRequest,
    PolicyIngestionRunOut,
    PolicyLineageResponse,
    PolicyPromotionRequest,
    PolicyPromotionResponse,
)
from app.services.policy_ingestion import (
    PolicyAuthorizationError,
    PolicyIngestionService,
    PolicyValidationError,
)

router = APIRouter(prefix="/api/v1/policies", tags=["policy-ingestion"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


def get_policy_service(db: Annotated[Session, Depends(get_db)]) -> PolicyIngestionService:
    return PolicyIngestionService(db)


def _error(
    status_code: int,
    code: str,
    message: str,
    correlation_id: str,
    details: list[dict[str, object]] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": code,
            "message": message,
            "correlation_id": correlation_id,
            "details": details or [],
        },
    )


def _require_policy_admin(token: str | None, correlation_id: str) -> None:
    if token is None:
        raise _error(
            401,
            "POLICY_ADMIN_AUTH_REQUIRED",
            "X-Policy-Admin header is required for controlled policy ingestion.",
            correlation_id,
        )
    if token != "true":
        raise _error(
            403,
            "POLICY_ADMIN_FORBIDDEN",
            "Caller is not authorized for controlled policy ingestion.",
            correlation_id,
        )


@router.post(
    "/ingestions",
    response_model=PolicyIngestionRunOut,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def ingest_policy_documents(
    request: PolicyIngestionRequest,
    response: Response,
    service: Annotated[PolicyIngestionService, Depends(get_policy_service)],
    x_policy_admin: Annotated[str | None, Header(alias="X-Policy-Admin")] = None,
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> PolicyIngestionRunOut:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    _require_policy_admin(x_policy_admin, correlation_id)
    try:
        return service.ingest(request, correlation_id=correlation_id)
    except PolicyValidationError as exc:
        raise _error(
            422,
            "POLICY_INGESTION_VALIDATION_FAILED",
            str(exc),
            correlation_id,
            exc.errors,
        ) from exc
    except PolicyVersionConflictError as exc:
        raise _error(409, "POLICY_VERSION_CONFLICT", str(exc), correlation_id) from exc
    except PolicyAuthorizationError as exc:
        raise _error(403, "POLICY_ADMIN_FORBIDDEN", str(exc), correlation_id) from exc
    except AuditWriteError as exc:
        raise _error(500, "POLICY_AUDIT_APPEND_FAILED", str(exc), correlation_id) from exc


@router.get(
    "/ingestions/{run_id}",
    response_model=PolicyIngestionRunOut,
    responses=ERROR_RESPONSES,
)
def get_policy_ingestion_run(
    run_id: UUID,
    response: Response,
    service: Annotated[PolicyIngestionService, Depends(get_policy_service)],
    x_policy_admin: Annotated[str | None, Header(alias="X-Policy-Admin")] = None,
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> PolicyIngestionRunOut:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    _require_policy_admin(x_policy_admin, correlation_id)
    try:
        return service.get_run(run_id)
    except PolicyRunNotFoundError as exc:
        raise _error(404, "POLICY_RUN_NOT_FOUND", str(exc), correlation_id) from exc


@router.post(
    "/promotions",
    response_model=PolicyPromotionResponse,
    responses=ERROR_RESPONSES,
)
def promote_policy_corpus(
    request: PolicyPromotionRequest,
    response: Response,
    service: Annotated[PolicyIngestionService, Depends(get_policy_service)],
    x_policy_admin: Annotated[str | None, Header(alias="X-Policy-Admin")] = None,
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> PolicyPromotionResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    _require_policy_admin(x_policy_admin, correlation_id)
    try:
        return service.promote(request, correlation_id=correlation_id)
    except PolicyRunNotFoundError as exc:
        raise _error(404, "POLICY_RUN_NOT_FOUND", str(exc), correlation_id) from exc
    except PolicyPromotionError as exc:
        raise _error(409, "POLICY_PROMOTION_BLOCKED", str(exc), correlation_id) from exc
    except AuditWriteError as exc:
        raise _error(500, "POLICY_AUDIT_APPEND_FAILED", str(exc), correlation_id) from exc


@router.get(
    "/chunks/{chunk_id}/lineage",
    response_model=PolicyLineageResponse,
    responses=ERROR_RESPONSES,
)
def get_policy_chunk_lineage(
    chunk_id: str,
    response: Response,
    service: Annotated[PolicyIngestionService, Depends(get_policy_service)],
    x_policy_admin: Annotated[str | None, Header(alias="X-Policy-Admin")] = None,
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> PolicyLineageResponse:
    correlation_id = resolve_correlation_id(x_correlation_id)
    response.headers[CORRELATION_HEADER] = correlation_id
    _require_policy_admin(x_policy_admin, correlation_id)
    try:
        return service.lineage(chunk_id, correlation_id=correlation_id)
    except PolicyRunNotFoundError as exc:
        raise _error(404, "POLICY_CHUNK_NOT_FOUND", str(exc), correlation_id) from exc


__all__ = ["get_policy_service", "router"]
