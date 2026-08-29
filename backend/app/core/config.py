from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "local")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://disputeiq:disputeiq@127.0.0.1:5433/disputeiq",
    )
    ai_enabled: bool = os.getenv("AI_ENABLED", "false").lower() == "true"
    rag_enabled: bool = os.getenv("RAG_ENABLED", "false").lower() == "true"


settings = Settings()
