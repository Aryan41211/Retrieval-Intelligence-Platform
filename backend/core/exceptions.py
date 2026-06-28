"""Custom exceptions for the Retrieval Intelligence Platform."""

from typing import Any


class RipError(Exception):
    """Base exception for all RIP errors."""

    code: str = "RIP_ERROR"
    details: dict[str, Any] | None = None

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details

    def to_response(self) -> dict:
        """Convert to structured error response."""
        return {
            "code": self.code,
            "message": str(self),
            "details": self.details or {},
        }


class DocumentLoadError(RipError):
    """Error loading a document from source."""

    code = "DOCUMENT_LOAD_ERROR"


class UnsupportedDocumentTypeError(RipError):
    """Document format is not supported."""

    code = "UNSUPPORTED_DOCUMENT_TYPE"


class EmptyDocumentError(RipError):
    """Document has no content after loading."""

    code = "EMPTY_DOCUMENT_ERROR"


class CorruptedDocumentError(RipError):
    """Document is corrupted or unreadable."""

    code = "CORRUPTED_DOCUMENT_ERROR"


class ValidationError(RipError):
    """Document validation failed."""

    code = "VALIDATION_ERROR"


class FileSizeError(ValidationError):
    """File exceeds maximum allowed size."""

    code = "FILE_SIZE_ERROR"


class EncodingError(DocumentLoadError):
    """Document encoding could not be determined or is invalid."""

    code = "ENCODING_ERROR"
