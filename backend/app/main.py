from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.disputes import router as disputes_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="DisputeIQ Foundation API",
        version="0.1.0",
        description="Deterministic foundation APIs for synthetic dispute cases.",
    )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(disputes_router)
    return app


app = create_app()
