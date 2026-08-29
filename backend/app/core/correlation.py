from __future__ import annotations

from uuid import uuid4

CORRELATION_HEADER = "X-Correlation-ID"


def resolve_correlation_id(value: str | None) -> str:
    if value and value.strip():
        return value.strip()
    return f"corr_{uuid4()}"
