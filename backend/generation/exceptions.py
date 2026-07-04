from __future__ import annotations

from backend.core.exceptions import RipError


class GenerationError(RipError):
    code = "GENERATION_ERROR"


class LLMProviderUnavailableError(GenerationError):
    code = "LLM_PROVIDER_UNAVAILABLE_ERROR"


class GenerationTimeoutError(GenerationError):
    code = "GENERATION_TIMEOUT_ERROR"


class PromptBuildError(GenerationError):
    code = "PROMPT_BUILD_ERROR"


class CitationExtractionError(GenerationError):
    code = "CITATION_EXTRACTION_ERROR"


class ResponseValidationError(GenerationError):
    code = "RESPONSE_VALIDATION_ERROR"


class EmptyContextError(GenerationError):
    code = "EMPTY_CONTEXT_ERROR"
