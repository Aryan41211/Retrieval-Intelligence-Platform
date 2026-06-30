"""Embedding validation for quality control."""

import math
from typing import Final

from backend.data.embeddings.base_embedding_provider import (
    EmbeddingDimensionError,
    EmbeddingValidationError,
)
from backend.data.models.embedding import Embedding

NORMALIZATION_EPSILON: Final[float] = 1e-6


class EmbeddingValidator:
    """Validates embedding vectors for correctness and quality."""

    def __init__(
        self,
        expected_dimension: int | None = None,
        allow_nan: bool = False,
        allow_inf: bool = False,
    ):
        self.expected_dimension = expected_dimension
        self.allow_nan = allow_nan
        self.allow_inf = allow_inf

    def validate(self, embedding: Embedding) -> None:
        """Validate a single embedding.

        Args:
            embedding: Embedding to validate.

        Raises:
            EmbeddingValidationError: If embedding is invalid.
            EmbeddingDimensionError: If dimension mismatch.
        """
        if not embedding.embedding_vector:
            raise EmbeddingValidationError("Embedding vector cannot be empty")

        vector = embedding.embedding_vector
        self._validate_numeric(vector)
        self._validate_values(vector)
        self._validate_dimension(embedding.embedding_dimension, len(vector))

    def validate_all(self, embeddings: list[Embedding]) -> list[str]:
        """Validate multiple embeddings.

        Returns:
            List of error messages (empty if all valid).
        """
        errors: list[str] = []

        for i, embedding in enumerate(embeddings):
            try:
                self.validate(embedding)
            except (EmbeddingValidationError, EmbeddingDimensionError) as e:
                errors.append(f"Embedding {i} ({embedding.embedding_id}): {e}")

        # Duplicate detection (same checksum implies identical vector content).
        duplicates = self.check_duplicates(embeddings)
        if duplicates:
            formatted = ", ".join([f"{i}-{j}" for i, j in duplicates[:20]])
            errors.append(
                f"Duplicate embeddings detected (same checksum): pairs={formatted}"
                + (" ..." if len(duplicates) > 20 else "")
            )

        return errors

    def _validate_numeric(self, vector: list[float]) -> None:
        if not all(isinstance(v, int | float) for v in vector):
            raise EmbeddingValidationError("Embedding vector must contain only numeric values")

    def _validate_values(self, vector: list[float]) -> None:
        for i, v in enumerate(vector):
            if math.isnan(v):
                if self.allow_nan:
                    continue
                raise EmbeddingValidationError(
                    f"Embedding contains NaN at index {i}"
                )
            if math.isinf(v):
                if self.allow_inf:
                    continue
                raise EmbeddingValidationError(
                    f"Embedding contains Inf at index {i}"
                )

    def _validate_dimension(self, declared_dim: int, actual_dim: int) -> None:
        if declared_dim != actual_dim:
            raise EmbeddingDimensionError(
                f"Dimension mismatch: declared {declared_dim}, actual {actual_dim}",
                {"declared_dimension": declared_dim, "actual_dimension": actual_dim},
            )
        if self.expected_dimension is not None and declared_dim != self.expected_dimension:
            raise EmbeddingDimensionError(
                f"Unexpected dimension: expected {self.expected_dimension}, got {declared_dim}",
                {"expected_dimension": self.expected_dimension, "actual_dimension": declared_dim},
            )

    def is_normalized(self, vector: list[float]) -> bool:
        magnitude = math.sqrt(sum(v * v for v in vector))
        return abs(magnitude - 1.0) < NORMALIZATION_EPSILON

    def normalize(self, vector: list[float]) -> list[float]:
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude == 0:
            return vector
        return [v / magnitude for v in vector]

    def compute_similarity(
        self, embedding1: Embedding, embedding2: Embedding
    ) -> float:
        if len(embedding1.embedding_vector) != len(embedding2.embedding_vector):
            raise EmbeddingDimensionError(
                f"Cannot compute similarity: dimension mismatch {len(embedding1.embedding_vector)} vs {len(embedding2.embedding_vector)}"
            )
        dot_product = sum(
            a * b
            for a, b in zip(embedding1.embedding_vector, embedding2.embedding_vector, strict=True)
        )
        magnitude1 = math.sqrt(sum(v * v for v in embedding1.embedding_vector))
        magnitude2 = math.sqrt(sum(v * v for v in embedding2.embedding_vector))
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

    def check_duplicates(self, embeddings: list[Embedding]) -> list[tuple[int, int]]:
        """Find duplicate embeddings by checksum.

        Note: checksum may be unset; in that case we do not treat embeddings as duplicates.
        """
        duplicates: list[tuple[int, int]] = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                ci = embeddings[i].checksum
                cj = embeddings[j].checksum
                if not ci or not cj:
                    continue
                if ci == cj:
                    duplicates.append((i, j))
        return duplicates
