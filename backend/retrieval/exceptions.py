from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.core.exceptions import RipError


class RetrievalError(RipError):
    code = "RETRIEVAL_ERROR"


class RetrievalTimeoutError(RetrievalError):
    code = "RETRIEVAL_TIMEOUT_ERROR"


class RetrievalConfigurationError(RetrievalError):
    code = "RETRIEVAL_CONFIGURATION_ERROR"


class EmptyRetrievalResultError(RetrievalError):
    code = "RETRIEVAL_EMPTY_RESULT_ERROR"

    def __init__(self, message: str = "Retrieval returned no results", details: dict[str, Any] | None = None):
        super().__init__(message, details=details)


# Convenience builder for timestamped details (kept local to avoid extra dependencies)
def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
