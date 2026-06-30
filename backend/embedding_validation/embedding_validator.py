"""Extended embedding validator for comprehensive quality control."""

import hashlib
import math
from dataclasses import dataclass, field

from backend.data.embeddings.base_embedding_provider import (
    EmbeddingDimensionError,
)
from backend.data.models.embedding import Embedding


@dataclass
class ValidationResult:
    """Result of embedding validation with detailed metrics."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_embeddings: int = 0
    valid_embeddings: int = 0
    invalid_embeddings: int = 0
    dimension_consistent: bool = True
    dimensions: set[int] = field(default_factory=set)
    duplicate_count: int = 0
    near_duplicate_count: int = 0
    nan_count: int = 0
    inf_count: int = 0
    zero_vector_count: int = 0
    normalized_count: int = 0

    @property
    def validation_rate(self) -> float:
        """Return the validation pass rate."""
        if self.total_embeddings == 0:
            return 0.0
        return self.valid_embeddings / self.total_embeddings

    @property
    def duplicate_rate(self) -> float:
        """Return the duplicate rate."""
        if self.total_embeddings == 0:
            return 0.0
        return self.duplicate_count / self.total_embeddings


class ExtendedEmbeddingValidator:
    """Extended validator with comprehensive embedding quality checks."""

    def __init__(
        self,
        expected_dimension: int | None = None,
        allow_nan: bool = False,
        allow_inf: bool = False,
        nan_tolerance: float = 0.0,
        detect_near_duplicates: bool = True,
        near_duplicate_threshold: float = 0.99,
    ):
        self.expected_dimension = expected_dimension
        self.allow_nan = allow_nan
        self.allow_inf = allow_inf
        self.nan_tolerance = nan_tolerance
        self.detect_near_duplicates = detect_near_duplicates
        self.near_duplicate_threshold = near_duplicate_threshold

    def validate_single(self, embedding: Embedding) -> tuple[bool, list[str], list[str]]:
        """Validate a single embedding vector.

        Returns:
            Tuple of (is_valid, errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not embedding.embedding_vector:
            errors.append("Embedding vector cannot be empty")
            return False, errors, warnings

        vector = embedding.embedding_vector

        if not self._validate_numeric(vector):
            errors.append("Embedding vector must contain only numeric values")

        nan_errors = self._validate_nan_values(vector)
        if nan_errors:
            if self.allow_nan:
                warnings.extend(nan_errors)
            else:
                errors.extend(nan_errors)

        inf_errors = self._validate_inf_values(vector)
        if inf_errors:
            if self.allow_inf:
                warnings.extend(inf_errors)
            else:
                errors.extend(inf_errors)

        if self._is_zero_vector(vector):
            warnings.append("Embedding is a zero vector")

        dimension_error = self._validate_dimension(embedding.embedding_dimension, len(vector))
        if dimension_error:
            warnings.append(dimension_error)

        return len(errors) == 0, errors, warnings

    def validate_all(self, embeddings: list[Embedding]) -> ValidationResult:
        """Validate multiple embeddings comprehensively.

        Args:
            embeddings: List of embeddings to validate.

        Returns:
            ValidationResult with detailed metrics.
        """
        errors: list[str] = []
        warnings: list[str] = []
        dimensions: set[int] = set()
        nan_count = 0
        inf_count = 0
        zero_vector_count = 0
        normalized_count = 0
        valid_count = 0

        for i, embedding in enumerate(embeddings):
            is_valid, emb_errors, emb_warnings = self.validate_single(embedding)

            if emb_errors:
                errors.extend([f"Embedding {i} ({embedding.embedding_id}): {e}" for e in emb_errors])

            warnings.extend([f"Embedding {i} ({embedding.embedding_id}): {w}" for w in emb_warnings])

            if is_valid:
                valid_count += 1

            if embedding.embedding_dimension:
                dimensions.add(embedding.embedding_dimension)

            nan_count += sum(1 for _ in self._validate_nan_values(embedding.embedding_vector))

            inf_count += sum(1 for _ in self._validate_inf_values(embedding.embedding_vector))

            if self._is_zero_vector(embedding.embedding_vector):
                zero_vector_count += 1

            if self.is_normalized(embedding.embedding_vector):
                normalized_count += 1

        duplicate_pairs = self.check_duplicates(embeddings)
        near_duplicate_pairs = (
            self._find_near_duplicates(embeddings) if self.detect_near_duplicates else []
        )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            total_embeddings=len(embeddings),
            valid_embeddings=valid_count,
            invalid_embeddings=len(embeddings) - valid_count,
            dimension_consistent=len(dimensions) <= 1,
            dimensions=dimensions,
            duplicate_count=len(duplicate_pairs) + len(near_duplicate_pairs),
            near_duplicate_count=len(near_duplicate_pairs),
            nan_count=nan_count,
            inf_count=inf_count,
            zero_vector_count=zero_vector_count,
            normalized_count=normalized_count,
        )

    def _validate_numeric(self, vector: list[float]) -> bool:
        """Check if vector contains only numeric values."""
        return all(isinstance(v, int | float) for v in vector)

    def _validate_nan_values(self, vector: list[float]) -> list[str]:
        """Check for NaN values and return error messages."""
        return [f"NaN at index {i}" for i, v in enumerate(vector) if math.isnan(v)]

    def _validate_inf_values(self, vector: list[float]) -> list[str]:
        """Check for Inf values and return error messages."""
        return [f"Inf at index {i}" for i, v in enumerate(vector) if math.isinf(v)]

    def _is_zero_vector(self, vector: list[float]) -> bool:
        """Check if vector is a zero vector."""
        return all(abs(v) < 1e-10 for v in vector)

    def _validate_dimension(self, declared_dim: int, actual_dim: int) -> str | None:
        """Validate dimension consistency and return error message if mismatch."""
        if declared_dim != actual_dim:
            return f"Dimension mismatch: declared {declared_dim}, actual {actual_dim}"
        if self.expected_dimension is not None and declared_dim != self.expected_dimension:
            return f"Unexpected dimension: expected {self.expected_dimension}, got {declared_dim}"
        return None

    def is_normalized(self, vector: list[float]) -> bool:
        """Check if vector is normalized (unit magnitude)."""
        if not vector:
            return False
        magnitude = math.sqrt(sum(v * v for v in vector))
        return abs(magnitude - 1.0) < 1e-6

    def normalize(self, vector: list[float]) -> list[float]:
        """Normalize vector to unit magnitude."""
        if not vector:
            return vector
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude == 0:
            return vector
        return [v / magnitude for v in vector]

    def compute_cosine_similarity(
        self, embedding1: Embedding, embedding2: Embedding
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        if len(embedding1.embedding_vector) != len(embedding2.embedding_vector):
            raise EmbeddingDimensionError(
                f"Cannot compute similarity: dimension mismatch "
                f"{len(embedding1.embedding_vector)} vs {len(embedding2.embedding_vector)}"
            )

        vec1 = embedding1.embedding_vector
        vec2 = embedding2.embedding_vector

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = math.sqrt(sum(v * v for v in vec1))
        magnitude2 = math.sqrt(sum(v * v for v in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def check_duplicates(self, embeddings: list[Embedding]) -> list[tuple[int, int]]:
        """Find duplicate embeddings by checksum."""
        duplicates: list[tuple[int, int]] = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                ci = embeddings[i].checksum
                cj = embeddings[j].checksum
                if ci and cj and ci == cj:
                    duplicates.append((i, j))
        return duplicates

    def _find_near_duplicates(
        self, embeddings: list[Embedding], threshold: float | None = None
    ) -> list[tuple[int, int, float]]:
        """Find near-duplicate embeddings by cosine similarity.

        Args:
            embeddings: List of embeddings to compare.
            threshold: Similarity threshold (defaults to near_duplicate_threshold).

        Returns:
            List of tuples (index_i, index_j, similarity_score).
        """
        threshold = threshold or self.near_duplicate_threshold
        if threshold <= 0 or threshold >= 1:
            raise ValueError("Threshold must be between 0 and 1 (exclusive)")

        near_duplicates: list[tuple[int, int, float]] = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                try:
                    similarity = self.compute_cosine_similarity(embeddings[i], embeddings[j])
                    if similarity >= threshold:
                        near_duplicates.append((i, j, similarity))
                except EmbeddingDimensionError:
                    continue

        return near_duplicates

    def check_near_duplicates(
        self, embeddings: list[Embedding], threshold: float | None = None
    ) -> list[tuple[int, int, float]]:
        """Find near-duplicate embeddings by cosine similarity.

        Args:
            embeddings: List of embeddings to compare.
            threshold: Similarity threshold (defaults to near_duplicate_threshold).

        Returns:
            List of tuples (index_i, index_j, similarity_score).
        """
        return self._find_near_duplicates(embeddings, threshold)

    def compute_vector_hash(self, vector: list[float]) -> str:
        """Compute a stable hash for a vector."""
        content = "".join(f"{v:.6f}" for v in vector)
        return hashlib.sha256(content.encode()).hexdigest()
