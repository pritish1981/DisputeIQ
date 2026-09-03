from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.cases import router as cases_router
from app.api.v1.disputes import router as disputes_router
from app.api.v1.policies import router as policies_router
from app.core.correlation import CORRELATION_HEADER, resolve_correlation_id


def _error_payload(
    *,
    error_code: str,
    message: str,
    correlation_id: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error_code": error_code,
        "message": message,
        "correlation_id": correlation_id,
        "details": details or [],
    }
    payload["detail"] = dict(payload)
    return payload


def create_app() -> FastAPI:
    app = FastAPI(
        title="DisputeIQ API",
        version="0.3.0",
        description=(
            "Deterministic case APIs and controlled policy ingestion "
            "for synthetic pilot data."
        ),
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        correlation_id = resolve_correlation_id(request.headers.get(CORRELATION_HEADER))
        details = jsonable_encoder(exc.errors())
        missing_idempotency = any(
            error.get("loc") == ("header", "Idempotency-Key")
            or error.get("loc") == ("header", "idempotency-key")
            for error in exc.errors()
        )
        code = "MISSING_IDEMPOTENCY_KEY" if missing_idempotency else "VALIDATION_FAILED"
        message = (
            "Idempotency-Key header is required."
            if missing_idempotency
            else "Request validation failed."
        )
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                error_code=code,
                message=message,
                correlation_id=correlation_id,
                details=details,
            ),
            headers={CORRELATION_HEADER: correlation_id},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        correlation_id = resolve_correlation_id(request.headers.get(CORRELATION_HEADER))
        if isinstance(exc.detail, dict):
            correlation_id = str(exc.detail.get("correlation_id") or correlation_id)
            content = _error_payload(
                error_code=str(exc.detail.get("error_code", "REQUEST_FAILED")),
                message=str(exc.detail.get("message", "Request failed.")),
                correlation_id=correlation_id,
                details=list(exc.detail.get("details", [])),
            )
        else:
            content = _error_payload(
                error_code="REQUEST_FAILED",
                message=str(exc.detail),
                correlation_id=correlation_id,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers={CORRELATION_HEADER: correlation_id},
        )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(cases_router)
    app.include_router(disputes_router)
    app.include_router(policies_router)
    return app


app = create_app()
