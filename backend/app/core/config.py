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
    ai_kill_switch_enabled: bool = os.getenv("AI_KILL_SWITCH_ENABLED", "false").lower() == "true"
    classification_confidence_threshold: float = float(
        os.getenv("CLASSIFICATION_CONFIDENCE_THRESHOLD", "0.70")
    )
    model_gateway_token_budget: int = int(os.getenv("MODEL_GATEWAY_TOKEN_BUDGET", "1200"))
    model_gateway_timeout_ms: int = int(os.getenv("MODEL_GATEWAY_TIMEOUT_MS", "2000"))
    model_gateway_retry_limit: int = int(os.getenv("MODEL_GATEWAY_RETRY_LIMIT", "1"))


settings = Settings()
