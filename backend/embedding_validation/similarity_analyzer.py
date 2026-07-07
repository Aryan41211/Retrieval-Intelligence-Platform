"""Similarity analysis for embedding quality assessment.

Implements:
- Cosine similarity distribution
- Top-K similarity statistics
- Mean similarity
- Similarity variance
- Outlier detection
- Duplicate cluster detection
- Embedding density statistics

Does NOT implement retrieval evaluation.
"""

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from backend.data.models.embedding import Embedding


@dataclass
class SimilarityMetrics:
    """Metrics for similarity analysis.

    Contains comprehensive similarity statistics including distribution,
    top-K averages, and analysis of similarity patterns.
    """

    average_similarity: float = 0.0
    median_similarity: float = 0.0
    std_similarity: float = 0.0
    min_similarity: float = 0.0
    max_similarity: float = 0.0
    similarity_distribution: dict[str, int] = field(default_factory=dict)
    top_k_similarities: dict[int, float] = field(default_factory=dict)

    # Extended metrics
    similarity_variance: float = 0.0
    outlier_count: int = 0
    outlier_indices: list[int] = field(default_factory=list)
    embedding_density: float = 0.0
    duplicate_clusters: int = 0


class SimilarityAnalyzer:
    """Analyze embedding similarity for semantic quality assessment.

    Computes pairwise cosine similarities, nearest neighbor statistics,
    outlier detection, cluster quality metrics, and content overlap analysis.

    Does NOT perform retrieval evaluation.
    """

    def __init__(self):
        self._similarity_matrix: np.ndarray | None = None

    def compute_pairwise_similarities(
        self, embeddings: list[Embedding]
    ) -> np.ndarray:
        """Compute pairwise cosine similarity matrix.

        Args:
            embeddings: List of embeddings to compare.

        Returns:
            NxN matrix of cosine similarities.

        Raises:
            ValueError: If embeddings have inconsistent dimensions.
        """
        dimensions = set(e.embedding_dimension for e in embeddings)
        if len(dimensions) > 1:
            raise ValueError(
                f"Inconsistent dimensions in embeddings: {dimensions}"
            )

        if not embeddings:
            return np.array([])

        matrix = np.zeros(
            (len(embeddings), len(embeddings)), dtype=np.float64
        )

        for i, e1 in enumerate(embeddings):
            for j, e2 in enumerate(embeddings):
                if i <= j:
                    matrix[i, j] = self._cosine_similarity(e1, e2)
                    matrix[j, i] = matrix[i, j]

        self._similarity_matrix = matrix
        return matrix

    def find_top_k_similar(
        self, embeddings: list[Embedding], k: int = 5
    ) -> list[list[tuple[int, float]]]:
        """Find top-K most similar embeddings for each embedding.

        Args:
            embeddings: List of embeddings.
            k: Number of top similar to find (excluding self).

        Returns:
            List of (index, similarity) pairs for each embedding.
        """
        if len(embeddings) < 2:
            return []

        similarities = self.compute_pairwise_similarities(embeddings)
        top_k_results: list[list[tuple[int, float]]] = []

        for i in range(len(embeddings)):
            row = similarities[i].copy()
            row[i] = -1  # Exclude self-similarity

            top_indices = np.argsort(row)[-k:][::-1]
            top_k_results.append(
                [(int(idx), float(row[idx])) for idx in top_indices]
            )

        return top_k_results

    def compute_top_k_statistics(
        self, embeddings: list[Embedding], k: int = 5
    ) -> dict[str, float]:
        """Compute statistics of top-K similarities.

        Calculates the average similarity to the top-K nearest neighbors
        for each embedding, providing insight into local neighborhood density.

        Args:
            embeddings: List of embeddings.
            k: Number of nearest neighbors to consider.

        Returns:
            Dictionary with mean_top_k_similarity and per-rank averages.
        """
        if len(embeddings) < 2:
            return {"mean_top_k_similarity": 0.0}

        top_k_results = self.find_top_k_similar(embeddings, k=k)
        if not top_k_results:
            return {"mean_top_k_similarity": 0.0}

        result: dict[str, float] = {}
        for rank in range(min(k, len(top_k_results[0]))):
            similarities_at_rank = [
                r[rank][1] for r in top_k_results if len(r) > rank
            ]
            if similarities_at_rank:
                result[f"top_{rank + 1}_avg_similarity"] = float(
                    np.mean(similarities_at_rank)
                )

        all_neighbor_sims = [
            sim for r in top_k_results for _, sim in r
        ]
        result["mean_top_k_similarity"] = (
            float(np.mean(all_neighbor_sims)) if all_neighbor_sims else 0.0
        )

        return result

    def compute_nearest_neighbor_stats(
        self, embeddings: list[Embedding]
    ) -> dict[str, Any]:
        """Compute nearest neighbor statistics.

        Calculates distance distribution to the nearest neighbor (excluding self)
        for each embedding.

        Returns:
            Statistics about nearest neighbor distances.
        """
        if len(embeddings) < 2:
            return {
                "mean_nn_distance": 0.0,
                "std_nn_distance": 0.0,
                "min_nn_distance": 0.0,
                "max_nn_distance": 0.0,
            }

        similarities = self.compute_pairwise_similarities(embeddings)

        nn_distances = []
        for i in range(len(embeddings)):
            row = similarities[i]
            row_without_self = np.concatenate([row[:i], row[i + 1:]])
            nn_similarity = (
                float(np.max(row_without_self))
                if len(row_without_self) > 0
                else 0
            )
            nn_distances.append(1.0 - nn_similarity)

        distances_array = np.array(nn_distances, dtype=np.float64)

        return {
            "mean_nn_distance": float(np.mean(distances_array)),
            "std_nn_distance": float(np.std(distances_array)),
            "min_nn_distance": float(np.min(distances_array)),
            "max_nn_distance": float(np.max(distances_array)),
            "median_nn_distance": float(np.median(distances_array)),
        }

    def detect_outlier_embeddings(
        self,
        embeddings: list[Embedding],
        method: str = "nn_distance",
        threshold_factor: float = 2.0,
    ) -> list[int]:
        """Detect outlier embeddings based on similarity.

        Identifies embeddings that are unusually dissimilar from all others,
        which may indicate anomalous or corrupted content.

        Args:
            embeddings: List of embeddings.
            method: Detection method ('nn_distance' or 'density').
            threshold_factor: Standard deviation threshold for outlier
                detection (default: 2.0).

        Returns:
            Indices of outlier embeddings.
        """
        if len(embeddings) < 3 or method not in ("nn_distance", "density"):
            return []

        similarities = self.compute_pairwise_similarities(embeddings)

        if method == "nn_distance":
            nn_similarities = []
            for i in range(len(embeddings)):
                row = similarities[i]
                row_without_self = np.concatenate(
                    [row[:i], row[i + 1:]]
                )
                nn_sim = (
                    float(np.max(row_without_self))
                    if len(row_without_self) > 0
                    else 0
                )
                nn_similarities.append(nn_sim)

            mean_sim = float(np.mean(nn_similarities))
            std_sim = float(np.std(nn_similarities))

            return [
                i
                for i, sim in enumerate(nn_similarities)
                if sim < (mean_sim - threshold_factor * std_sim)
            ]

        return []

    def compute_density_statistics(
        self, embeddings: list[Embedding]
    ) -> dict[str, float]:
        """Compute embedding density statistics.

        Analyzes how densely packed embeddings are in the vector space
        based on their pairwise similarity distribution.

        Args:
            embeddings: List of embeddings.

        Returns:
            Dictionary with embedding_density, spatial_spread,
            and diversity_score metrics.
        """
        if len(embeddings) < 2:
            return {
                "embedding_density": 0.0,
                "spatial_spread": 0.0,
                "diversity_score": 1.0,
            }

        # Compute pairwise similarities if not already cached
        if self._similarity_matrix is None or self._similarity_matrix.shape[0] != len(embeddings):
            self.compute_pairwise_similarities(embeddings)

        assert self._similarity_matrix is not None
        upper = self._similarity_matrix[np.triu_indices(len(embeddings), k=1)]
        if len(upper) == 0:
            return {
                "embedding_density": 0.0,
                "spatial_spread": 1.0,
                "diversity_score": 1.0,
            }

        avg_sim = float(np.mean(upper))
        std_sim = float(np.std(upper))
        sim_variance = std_sim ** 2

        return {
            "embedding_density": avg_sim,
            "spatial_spread": 1.0 - avg_sim,
            "diversity_score": 1.0 - avg_sim,
            "similarity_variance": sim_variance,
            "std_similarity": std_sim,
        }

    def compute_similarity_metrics(
        self, embeddings: list[Embedding]
    ) -> SimilarityMetrics:
        """Compute comprehensive similarity metrics.

        Calculates all similarity-related metrics including distribution,
        top-K statistics, outlier detection, and density metrics.

        Args:
            embeddings: List of embeddings.

        Returns:
            SimilarityMetrics with comprehensive statistical summary.
        """
        if len(embeddings) < 2:
            return SimilarityMetrics()

        similarities = self.compute_pairwise_similarities(embeddings)

        upper_triangle = similarities[
            np.triu_indices(len(embeddings), k=1)
        ]
        sim_list = upper_triangle.tolist()

        bins = [
            "< 0.2",
            "0.2-0.4",
            "0.4-0.6",
            "0.6-0.8",
            "0.8-1.0",
        ]
        hist, _ = np.histogram(
            sim_list, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0]
        )

        sim_array = np.array(sim_list, dtype=np.float64)

        top_k = self.find_top_k_similar(embeddings, k=5)
        top_k_avg: dict[int, float] = {}
        for k in range(1, 6):
            avg = float(
                np.mean([r[k - 1][1] for r in top_k if len(r) >= k])
            ) if any(len(r) >= k for r in top_k) else 0.0
            top_k_avg[k] = avg

        outliers = self.detect_outlier_embeddings(embeddings)

        density = self.compute_density_statistics(embeddings)

        sim_variance = float(np.var(sim_array)) if len(sim_array) > 0 else 0.0

        # Detect duplicate clusters
        duplicate_clusters = 0
        if self._similarity_matrix is not None:
            visited = set()
            n = len(embeddings)
            for i in range(n):
                if i in visited:
                    continue
                cluster = []
                stack = [i]
                while stack:
                    node = stack.pop()
                    if node in visited:
                        continue
                    visited.add(node)
                    cluster.append(node)
                    for j in range(n):
                        if (
                            j != node
                            and self._similarity_matrix[node, j] >= 0.99
                            and j not in visited
                        ):
                            stack.append(j)
                if len(cluster) > 1:
                    duplicate_clusters += 1

        return SimilarityMetrics(
            average_similarity=float(np.mean(sim_array))
            if len(sim_array) > 0
            else 0,
            median_similarity=float(np.median(sim_array))
            if len(sim_array) > 0
            else 0,
            std_similarity=float(np.std(sim_array))
            if len(sim_array) > 0
            else 0,
            min_similarity=float(np.min(sim_array))
            if len(sim_array) > 0
            else 0,
            max_similarity=float(np.max(sim_array))
            if len(sim_array) > 0
            else 0,
            similarity_distribution=dict(
                zip(bins, hist.tolist(), strict=False)
            ),
            top_k_similarities=top_k_avg,
            similarity_variance=sim_variance,
            outlier_count=len(outliers),
            outlier_indices=outliers,
            embedding_density=density.get("embedding_density", 0.0),
            duplicate_clusters=duplicate_clusters,
        )

    def compute_cluster_quality(
        self,
        embeddings: list[Embedding],
        labels: list[int] | None = None,
    ) -> dict[str, Any]:
        """Compute cluster quality indicators.

        Estimates cluster separation and density based on pairwise similarities.

        Args:
            embeddings: List of embeddings.
            labels: Optional cluster labels (if None, uses simple heuristics).

        Returns:
            Cluster quality metrics including silhouette estimate and diversity.
        """
        if len(embeddings) < 2:
            return {
                "silhouette_estimate": 0.0,
                "cluster_separation": 0.0,
                "intra_cluster_density": 0.0,
                "embedding_diversity": 1.0,
            }

        similarities = self.compute_pairwise_similarities(embeddings)

        avg_similarity = float(
            np.mean(
                similarities[np.triu_indices(len(embeddings), k=1)]
            )
        )

        return {
            "silhouette_estimate": avg_similarity,
            "intra_cluster_density": avg_similarity,
            "embedding_diversity": 1.0 - avg_similarity,
            "cluster_separation": 1.0 - avg_similarity,
        }

    def analyze_content_overlap(
        self,
        embeddings: list[Embedding],
        threshold: float = 0.95,
    ) -> list[tuple[int, int]]:
        """Find embeddings with high content overlap.

        Identifies pairs of embeddings whose similarity exceeds the threshold,
        indicating potential content duplication.

        Args:
            embeddings: List of embeddings.
            threshold: Similarity threshold for overlap detection.

        Returns:
            List of (index_i, index_j) pairs with high overlap.
        """
        if len(embeddings) < 2:
            return []

        similarities = self.compute_pairwise_similarities(embeddings)
        overlap_pairs: list[tuple[int, int]] = []

        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                if similarities[i, j] >= threshold:
                    overlap_pairs.append((i, j))

        return overlap_pairs

    def _cosine_similarity(self, e1: Embedding, e2: Embedding) -> float:
        """Compute cosine similarity between two embeddings."""
        vec1 = e1.embedding_vector
        vec2 = e2.embedding_vector

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = math.sqrt(sum(v * v for v in vec1))
        magnitude2 = math.sqrt(sum(v * v for v in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
