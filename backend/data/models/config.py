"""Configuration for document ingestion."""

from pydantic import BaseModel, Field, field_validator


class IngestionConfig(BaseModel):
    """Configuration for document ingestion."""

    max_file_size_mb: int = Field(default=100, ge=1, le=1000)
    supported_extensions: list[str] = Field(
        default_factory=lambda: [".pdf", ".docx", ".txt", ".md", ".html", ".pptx", ".xlsx"]
    )
    default_encoding: str = "utf-8"
    default_language: str = "en"
    validate_checksum: bool = True

    @field_validator("supported_extensions")
    @classmethod
    def validate_extensions(cls, v: list[str]) -> list[str]:
        """Ensure all extensions start with a dot."""
        normalized = []
        for ext in v:
            if not ext.startswith("."):
                normalized.append(f".{ext}")
            else:
                normalized.append(ext)
        return normalized


class PreprocessingConfig(BaseModel):
    """Configuration for text preprocessing."""

    normalize_unicode: bool = True
    normalize_whitespace: bool = True
    remove_excessive_blank_lines: bool = True
    max_consecutive_blanks: int = Field(default=2, ge=1, le=5)
    preserve_paragraphs: bool = True
    detect_language: bool = True


class LoaderConfig(BaseModel):
    """Configuration for document loaders."""

    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.ingestion.max_file_size_mb * 1024 * 1024


def get_loader_config() -> LoaderConfig:
    """Get loader configuration (placeholder for future env var loading)."""
    return LoaderConfig()
