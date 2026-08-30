from __future__ import annotations

from fastapi import APIRouter, status

from app.api.v1.cases import create_case, get_case, get_case_service
from app.domain.schemas import CaseResponse, ErrorResponse

router = APIRouter(prefix="/api/v1/disputes", tags=["disputes-compatibility"])

router.add_api_route(
    "",
    create_case,
    methods=["POST"],
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
router.add_api_route(
    "/{case_id}",
    get_case,
    methods=["GET"],
    response_model=CaseResponse,
    deprecated=True,
    responses={404: {"model": ErrorResponse}},
)

__all__ = ["get_case_service", "router"]
