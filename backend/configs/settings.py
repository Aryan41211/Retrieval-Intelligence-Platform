"""Application settings using pydantic-settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingValidationSettings(BaseSettings):
    """Settings for embedding validation."""

    expected_dimension: int | None = Field(default=None, description="Expected embedding dimension")
    duplicate_tolerance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Tolerance threshold for duplicate detection (0.0 = exact only)",
    )
    validation_enabled: bool = Field(default=True, description="Enable embedding validation")
    strict_mode: bool = Field(
        default=False,
        description="Raise exceptions on validation failures instead of collecting errors",
    )
    warning_mode: bool = Field(
        default=False,
        description="Treat all validation failures as warnings",
    )

    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING_VALIDATION_",
        env_file=".env",
        extra="ignore",
    )


class VectorStoreSettings(BaseSettings):
    """Settings for vector store."""

    provider: str = Field(default="faiss", description="Vector store provider (faiss, chromadb, etc.)")
    storage_dir: str = Field(default="./data/vectorstore", description="Directory for storing vector indexes")
    index_type: str = Field(default="flat", description="Default index type (flat, hnsw, ivf, pq)")
    distance_metric: str = Field(default="cosine", description="Default distance metric (cosine, euclidean, inner_product)")
    auto_save: bool = Field(default=True, description="Automatically save index after modifications")
    auto_load: bool = Field(default=True, description="Automatically load index on initialization")

    model_config = SettingsConfigDict(
        env_prefix="VECTOR_STORE_",
        env_file=".env",
        extra="ignore",
    )


class BM25Settings(BaseSettings):
    """Settings for BM25 sparse retrieval."""

    enabled: bool = Field(default=True, description="Enable BM25 sparse retrieval")
    k1: float = Field(default=1.5, ge=0.0, le=10.0, description="BM25 k1 parameter")
    b: float = Field(default=0.75, ge=0.0, le=1.0, description="BM25 b parameter")
    lowercase: bool = Field(default=True, description="Lowercase query and documents for BM25")
    enabled_query_language_filter: bool = Field(
        default=False,
        description="If true, apply request/language filters to BM25 corpus during scoring",
    )
    # Build strategy: use in-memory index built from FAISSVectorStore records.
    # This is intentionally lightweight for sprint 3.
    rebuild_on_start: bool = Field(
        default=False, description="Rebuild BM25 index on start (in-memory)."
    )

    model_config = SettingsConfigDict(
        env_prefix="BM25_",
        env_file=".env",
        extra="ignore",
    )


class RRFSettings(BaseSettings):
    """Settings for Reciprocal Rank Fusion."""

    enabled: bool = Field(default=True, description="Enable RRF fusion for hybrid retrieval")
    k: int = Field(default=60, ge=1, le=200, description="RRF k parameter")
    remove_duplicates: bool = Field(default=True, description="Remove duplicate chunks in fused results")
    stable_ranking: bool = Field(
        default=True, description="Preserve stable ordering for ties"
    )

    model_config = SettingsConfigDict(
        env_prefix="RRF_",
        env_file=".env",
        extra="ignore",
    )


class CrossEncoderRerankSettings(BaseSettings):
    """Settings for optional cross-encoder reranking."""

    enabled: bool = Field(default=False, description="Enable cross-encoder reranking stage")
    provider: str = Field(default="sentence_transformers", description="Reranker provider")
    model_name: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2", description="CrossEncoder model name")
    top_n: int = Field(default=20, ge=1, le=2000, description="Number of top candidates to rerank")
    batch_size: int = Field(default=16, ge=1, le=256, description="CrossEncoder batch size")
    max_length: int = Field(default=512, ge=16, le=4096, description="Max text length for cross-encoder inputs")

    model_config = SettingsConfigDict(
        env_prefix="CROSS_ENCODER_",
        env_file=".env",
        extra="ignore",
    )


class QueryExpansionSettings(BaseSettings):
    """Settings for lightweight query expansion."""

    enabled: bool = Field(default=True, description="Enable query expansion stage")
    synonyms_enabled: bool = Field(default=True, description="Enable synonym expansion")
    stopword_cleanup: bool = Field(default=True, description="Remove stopwords from expanded query")
    punctuation_cleanup: bool = Field(default=True, description="Cleanup punctuation")
    lowercase: bool = Field(default=True, description="Lowercase query for normalization")

    # Very lightweight builtin synonyms; future: pluggable + external sources / LLM.
    synonyms: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "ai": ["artificial intelligence"],
            "llm": ["large language model"],
            "retrieval": ["search", "information retrieval"],
        },
        description="Synonym mapping for lightweight expansion",
    )

    model_config = SettingsConfigDict(
        env_prefix="QUERY_EXPANSION_",
        env_file=".env",
        extra="ignore",
    )


class DynamicTopKSettings(BaseSettings):
    """Settings for adaptive Top-K selection."""

    enabled: bool = Field(default=True, description="Enable dynamic top-k selection")
    min_k: int = Field(default=5, ge=1, le=1000, description="Minimum number of final chunks")
    max_k: int = Field(default=30, ge=1, le=1000, description="Maximum number of final chunks")
    # Confidence mapping: use score spread to decide k.
    min_confidence: float = Field(default=0.2, ge=0.0, le=1.0, description="Minimum confidence to increase k")
    max_confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Maximum confidence to cap k")

    model_config = SettingsConfigDict(
        env_prefix="DYNAMIC_TOP_K_",
        env_file=".env",
        extra="ignore",
    )


class IntelligentRetrievalSettings(BaseSettings):
    """Settings for Intelligent Retrieval pipeline."""

    enabled: bool = Field(default=False, description="Enable IntelligentRetrievalPipeline")
    dense_enabled: bool = Field(default=True, description="Enable dense retrieval stage")
    sparse_enabled: bool = Field(default=True, description="Enable sparse BM25 retrieval stage")
    retrieval_weight_dense: float = Field(default=1.0, ge=0.0, le=10.0, description="Weight for dense in fusion (optional)")
    retrieval_weight_sparse: float = Field(default=1.0, ge=0.0, le=10.0, description="Weight for sparse in fusion (optional)")

    rerank: CrossEncoderRerankSettings = Field(default_factory=CrossEncoderRerankSettings)
    bm25: BM25Settings = Field(default_factory=BM25Settings)
    rrf: RRFSettings = Field(default_factory=RRFSettings)
    query_expansion: QueryExpansionSettings = Field(default_factory=QueryExpansionSettings)
    dynamic_top_k: DynamicTopKSettings = Field(default_factory=DynamicTopKSettings)

    model_config = SettingsConfigDict(
        env_prefix="INTELLIGENT_RETRIEVAL_",
        env_file=".env",
        extra="ignore",
    )


class GenerationSettings(BaseSettings):
    """Settings for generation pipeline."""

    provider: str = Field(default="fake", description="LLM provider (fake, openai_compatible, ollama, nim)")
    model_name: str = Field(default="fake-model", description="Model name for the selected provider")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=512, ge=1, le=8192, description="Maximum tokens to generate")
    timeout_s: float = Field(default=60.0, gt=0.0, description="Generation timeout in seconds")

    model_config = SettingsConfigDict(
        env_prefix="GENERATION_",
        env_file=".env",
        extra="ignore",
    )


class RetrievalSettings(BaseSettings):
    """Settings for retrieval engine."""

    top_k: int = Field(default=10, ge=1, le=1000, description="Default number of results to retrieve")
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    batch_size: int = Field(default=32, ge=1, le=1000, description="Batch size for batch retrieval operations")
    auto_load: bool = Field(default=True, description="Automatically load index on initialization")
    auto_save: bool = Field(default=True, description="Automatically save index after modifications")

    # Default filters (optional)
    default_languages: list[str] | None = Field(default=None, description="Default language filters")
    default_source_filenames: list[str] | None = Field(default=None, description="Default source filename filters")

    intelligent: IntelligentRetrievalSettings = Field(default_factory=IntelligentRetrievalSettings)

    model_config = SettingsConfigDict(
        env_prefix="RETRIEVAL_",
        env_file=".env",
        extra="ignore",
    )


class IngestionSettings(BaseSettings):
    """Settings for document ingestion."""

    max_file_size_mb: int = Field(default=100, ge=1, le=1000)
    supported_extensions: list[str] = Field(
        default_factory=lambda: [".pdf", ".docx", ".txt", ".md", ".markdown"]
    )
    default_encoding: str = "utf-8"
    default_language: str = "en"
    validate_checksum: bool = True

    model_config = SettingsConfigDict(
        env_prefix="INGESTION_",
        env_file=".env",
        extra="ignore",
    )

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


class PreprocessingSettings(BaseSettings):
    """Settings for text preprocessing."""

    normalize_unicode: bool = True
    normalize_whitespace: bool = True
    remove_excessive_blank_lines: bool = True
    max_consecutive_blanks: int = Field(default=2, ge=1, le=5)
    preserve_paragraphs: bool = True

    model_config = SettingsConfigDict(
        env_prefix="PREPROCESSING_",
        env_file=".env",
        extra="ignore",
    )


class Settings(BaseSettings):
    """Main application settings."""

    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    preprocessing: PreprocessingSettings = Field(default_factory=PreprocessingSettings)
    embedding_validation: EmbeddingValidationSettings = Field(
        default_factory=EmbeddingValidationSettings
    )
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings instance with loaded configuration.
    """
    return Settings()
