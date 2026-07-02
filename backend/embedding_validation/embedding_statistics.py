"""Statistics generation for embedding analysis.

Generates comprehensive statistics including:
- Norm statistics (mean, std, min, max of vector norms)
- Value statistics (distribution of embedding values)
- Density statistics (sparsity and outlier detection)
- Similarity distribution (pairwise similarity distribution)
- Overall embedding quality metrics
"""

import math
from dataclasses import dataclass, field

import numpy as np

from backend.data.models.embedding import Embedding
from backend.data.models.embedding import Embedding as EmbeddingModel


@dataclass
class EmbeddingStats:
    """Statistics for a single embedding or collection of embeddings."""

    mean: float = 0.0
    std: float = 0.0
    min: float = 0.0
    max: float = 0.0
    count: int = 0


@dataclass
class NormStatistics:
    """Statistics about embedding vector norms."""

    mean_norm: float = 0.0
    std_norm: float = 0.0
    min_norm: float = 0.0
    max_norm: float = 0.0
    norms: list[float] = field(default_factory=list)
    norms_array: np.ndarray | None = None

    @property
    def average_norm(self) -> float:
        """Alias for mean_norm for backward compatibility."""
        return self.mean_norm


@dataclass
class DensityStatistics:
    """Statistics about embedding density in vector space."""

    mean_density: float = 0.0
    sparsity_ratio: float = 0.0
    outlier_count: int = 0
    outlier_ratio: float = 0.0


@dataclass
class EmbeddingQualityReport:
    """Comprehensive embedding quality report.

    Contains all quality metrics including norm statistics, value statistics,
    density statistics, similarity distribution, and actionable warnings
    and recommendations.
    """

    total_embeddings: int = 0
    embedding_dimension: int = 0
    norm_statistics: NormStatistics | None = None
    value_statistics: EmbeddingStats = field(default_factory=EmbeddingStats)
    density_statistics: DensityStatistics | None = None
    similarity_distribution: dict[str, float] = field(default_factory=dict)

    # Extended quality metrics
    average_norm: float = 0.0
    norm_std_dev: float = 0.0
    duplicate_percentage: float = 0.0
    invalid_embedding_percentage: float = 0.0
    validation_pass_rate: float = 0.0

    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class EmbeddingStatistics:
    """Generate statistics for embedding analysis.

    Computes comprehensive statistical measures for embedding quality assessment,
    including norm distributions, value distributions, density metrics,
    and similarity distributions.
    """

    def __init__(self, embeddings: list[Embedding] | None = None):
        self.embeddings = embeddings or []

    def compute_norm_statistics(
        self, embeddings: list[Embedding] | None = None
    ) -> NormStatistics:
        """Compute statistics about vector norms.

        Args:
            embeddings: List of embeddings to analyze. If None, uses stored embeddings.

        Returns:
            NormStatistics with mean, std, min, max norms and raw norm values.
        """
        embeddings = embeddings or self.embeddings
        if not embeddings:
            return NormStatistics()

        norms = [self._compute_norm(e.embedding_vector) for e in embeddings]
        norms_array = np.array(norms, dtype=np.float64)

        return NormStatistics(
            mean_norm=float(np.mean(norms_array)),
            std_norm=float(np.std(norms_array)),
            min_norm=float(np.min(norms_array)),
            max_norm=float(np.max(norms_array)),
            norms=norms,
            norms_array=norms_array,
        )

    def compute_value_statistics(
        self, embeddings: list[Embedding] | None = None
    ) -> EmbeddingStats:
        """Compute statistics about embedding values across all dimensions.

        Args:
            embeddings: List of embeddings to analyze. If None, uses stored embeddings.

        Returns:
            EmbeddingStats with mean, std, min, max values and total count.
        """
        embeddings = embeddings or self.embeddings
        if not embeddings:
            return EmbeddingStats()

        all_values = []
        for e in embeddings:
            all_values.extend(e.embedding_vector)

        values_array = np.array(all_values, dtype=np.float64)

        return EmbeddingStats(
            mean=float(np.mean(values_array)),
            std=float(np.std(values_array)),
            min=float(np.min(values_array)),
            max=float(np.max(values_array)),
            count=len(all_values),
        )

    def compute_density_statistics(
        self,
        embeddings: list[Embedding] | None = None,
        density_threshold: float = 0.1,
    ) -> DensityStatistics:
        """Compute embedding density statistics.

        Measures how many dimensions are non-zero (active) in each embedding,
        detecting sparse or outlier vectors.

        Args:
            embeddings: List of embeddings to analyze.
            density_threshold: Minimum density ratio to consider non-sparse.

        Returns:
            DensityStatistics with mean density, sparsity ratio, and outlier count.
        """
        embeddings = embeddings or self.embeddings
        if not embeddings:
            return DensityStatistics()

        outlier_count = 0
        density_values = []

        for e in embeddings:
            non_zero = sum(1 for v in e.embedding_vector if abs(v) > 1e-10)
            density = non_zero / len(e.embedding_vector) if e.embedding_vector else 0
            density_values.append(density)

            if density < density_threshold:
                outlier_count += 1

        density_array = np.array(density_values, dtype=np.float64) if density_values else np.array([0.0])

        return DensityStatistics(
            mean_density=float(np.mean(density_array)),
            sparsity_ratio=1.0 - (float(np.mean(density_array)) if len(density_array) > 0 else 0),
            outlier_count=outlier_count,
            outlier_ratio=outlier_count / len(embeddings) if embeddings else 0,
        )

    def compute_similarity_distribution(
        self,
        embeddings: list[Embedding] | None = None,
        num_bins: int = 10,
        threshold: float = 0.99,
    ) -> dict[str, float]:
        """Compute distribution of pairwise similarities.

        Computes cosine similarity for all unique embedding pairs and returns
        distribution statistics including histogram bin counts.

        Args:
            embeddings: List of embeddings to analyze.
            num_bins: Number of histogram bins (unused, kept for backward compat).
            threshold: Threshold for high similarity detection.

        Returns:
            Dictionary with mean, std, min, max, median, p95, p99, and
            high_similarity_ratio.
        """
        embeddings = embeddings or self.embeddings
        if len(embeddings) < 2:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                if len(embeddings[i].embedding_vector) == len(embeddings[j].embedding_vector):
                    sim = self._compute_cosine_similarity(embeddings[i], embeddings[j])
                    similarities.append(sim)

        if not similarities:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

        sim_array = np.array(similarities, dtype=np.float64)

        return {
            "mean": float(np.mean(sim_array)),
            "std": float(np.std(sim_array)),
            "min": float(np.min(sim_array)),
            "max": float(np.max(sim_array)),
            "median": float(np.median(sim_array)),
            "p95": float(np.percentile(sim_array, 95)),
            "p99": float(np.percentile(sim_array, 99)),
            "high_similarity_ratio": sum(1 for s in similarities if s >= threshold)
            / len(similarities) if similarities else 0.0,
        }

    def generate_quality_report(
        self,
        embeddings: list[Embedding],
        expected_dimension: int | None = None,
        duplicate_count: int | None = None,
        invalid_count: int | None = None,
        total_validated: int | None = None,
    ) -> EmbeddingQualityReport:
        """Generate comprehensive quality report for embeddings.

        Computes all statistical measures and generates actionable warnings
        and recommendations based on the analysis.

        Args:
            embeddings: List of embeddings to analyze.
            expected_dimension: Expected embedding dimension for validation.
            duplicate_count: Number of duplicate embeddings found (optional).
            invalid_count: Number of invalid embeddings (optional).
            total_validated: Total number of embeddings validated (optional).

        Returns:
            EmbeddingQualityReport with all metrics, warnings, and recommendations.
        """
        if not embeddings:
            return EmbeddingQualityReport(total_embeddings=0)

        dimension = embeddings[0].embedding_dimension
        warnings: list[str] = []
        recommendations: list[str] = []

        norm_stats = self.compute_norm_statistics(embeddings)
        value_stats = self.compute_value_statistics(embeddings)
        density_stats = self.compute_density_statistics(embeddings)
        sim_dist = self.compute_similarity_distribution(embeddings)

        if expected_dimension and dimension != expected_dimension:
            warnings.append(
                f"Dimension mismatch: expected {expected_dimension}, got {dimension}"
            )

        if norm_stats.mean_norm > 0 and norm_stats.mean_norm < 0.9:
            recommendations.append(
                "Consider normalizing embeddings for better similarity search"
            )

        if norm_stats.std_norm > 1.0:
            warnings.append(
                f"High norm variance detected (std={norm_stats.std_norm:.4f}), "
                "embeddings may have inconsistent magnitudes"
            )

        if sim_dist.get("high_similarity_ratio", 0) > 0.3:
            warnings.append(
                f"High similarity ratio detected ({sim_dist['high_similarity_ratio']:.2%}), "
                "possible duplicate content"
            )

        if density_stats.sparsity_ratio > 0.9:
            warnings.append(
                f"High sparsity detected ({density_stats.sparsity_ratio:.2%}), "
                "vectors may have many near-zero values"
            )

        if density_stats.outlier_ratio > 0.05:
            warnings.append(
                f"Outlier embeddings detected ({density_stats.outlier_ratio:.2%}), "
                "may indicate anomalous content"
            )

        # Compute extended quality metrics
        average_norm = float(np.mean(norm_stats.norms)) if norm_stats.norms else 0.0
        norm_std_dev = float(np.std(norm_stats.norms)) if norm_stats.norms else 0.0

        total = total_validated or len(embeddings)
        duplicate_percentage = (duplicate_count or 0) / total * 100.0 if total > 0 else 0.0
        invalid_embedding_percentage = (invalid_count or 0) / total * 100.0 if total > 0 else 0.0
        validation_pass_rate = (
            (total - (invalid_count or 0)) / total * 100.0 if total > 0 else 0.0
        )

        if duplicate_percentage > 10.0:
            warnings.append(
                f"High duplicate rate ({duplicate_percentage:.1f}%), "
                "review deduplication strategy"
            )

        if invalid_embedding_percentage > 5.0:
            recommendations.append(
                f"Invalid embeddings rate is {invalid_embedding_percentage:.1f}%. "
                "Consider pre-validation before indexing."
            )

        return EmbeddingQualityReport(
            total_embeddings=len(embeddings),
            embedding_dimension=dimension,
            norm_statistics=norm_stats,
            value_statistics=value_stats,
            density_statistics=density_stats,
            similarity_distribution=sim_dist,
            average_norm=average_norm,
            norm_std_dev=norm_std_dev,
            duplicate_percentage=duplicate_percentage,
            invalid_embedding_percentage=invalid_embedding_percentage,
            validation_pass_rate=validation_pass_rate,
            warnings=warnings,
            recommendations=recommendations,
        )

    def _compute_norm(self, vector: list[float]) -> float:
        """Compute L2 norm of a vector."""
        return math.sqrt(sum(v * v for v in vector))

    def _compute_cosine_similarity(self, e1: Embedding, e2: Embedding) -> float:
        """Compute cosine similarity between two embeddings."""
        vec1 = e1.embedding_vector
        vec2 = e2.embedding_vector

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = math.sqrt(sum(v * v for v in vec1))
        magnitude2 = math.sqrt(sum(v * v for v in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)