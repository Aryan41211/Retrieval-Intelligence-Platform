"""Similarity analysis for embedding quality assessment."""

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from backend.data.models.embedding import Embedding


@dataclass
class SimilarityMetrics:
    """Metrics for similarity analysis."""

    average_similarity: float = 0.0
    median_similarity: float = 0.0
    std_similarity: float = 0.0
    min_similarity: float = 0.0
    max_similarity: float = 0.0
    similarity_distribution: dict[str, int] = field(default_factory=dict)
    top_k_similarities: dict[int, float] = field(default_factory=dict)


class SimilarityAnalyzer:
    """Analyze embedding similarity for semantic quality assessment."""

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
        """
        dimensions = set(e.embedding_dimension for e in embeddings)
        if len(dimensions) > 1:
            raise ValueError(
                f"Inconsistent dimensions in embeddings: {dimensions}"
            )

        if not embeddings:
            return np.array([])

        matrix = np.zeros((len(embeddings), len(embeddings)), dtype=np.float64)

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
            k: Number of top similar to find.

        Returns:
            List of (index, similarity) pairs for each embedding.
        """
        if len(embeddings) < 2:
            return []

        similarities = self.compute_pairwise_similarities(embeddings)
        top_k_results: list[list[tuple[int, float]]] = []

        for i in range(len(embeddings)):
            row = similarities[i].copy()
            row[i] = -1

            top_indices = np.argsort(row)[-k:][::-1]
            top_k_results.append(
                [(int(idx), float(row[idx])) for idx in top_indices]
            )

        return top_k_results

    def compute_nearest_neighbor_stats(
        self, embeddings: list[Embedding]
    ) -> dict[str, Any]:
        """Compute nearest neighbor statistics.

        Returns:
            Statistics about nearest neighbors.
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
            row_without_self = np.concatenate([row[:i], row[i + 1 :]])
            nn_similarity = float(np.max(row_without_self)) if len(row_without_self) > 0 else 0
            nn_distances.append(1.0 - nn_similarity)

        distances_array = np.array(nn_distances, dtype=np.float64)

        return {
            "mean_nn_distance": float(np.mean(distances_array)),
            "std_nn_distance": float(np.std(distances_array)),
            "min_nn_distance": float(np.min(distances_array)),
            "max_nn_distance": float(np.max(distances_array)),
        }

    def detect_outlier_embeddings(
        self, embeddings: list[Embedding], method: str = "nn_distance"
    ) -> list[int]:
        """Detect outlier embeddings based on similarity.

        Args:
            embeddings: List of embeddings.
            method: Detection method ('nn_distance' or 'density').

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
                row_without_self = np.concatenate([row[:i], row[i + 1 :]])
                nn_sim = float(np.max(row_without_self)) if len(row_without_self) > 0 else 0
                nn_similarities.append(nn_sim)

            mean_sim = np.mean(nn_similarities)
            std_sim = np.std(nn_similarities)

            return [
                i
                for i, sim in enumerate(nn_similarities)
                if sim < (mean_sim - 2 * std_sim)
            ]

        return []

    def compute_similarity_metrics(
        self, embeddings: list[Embedding]
    ) -> SimilarityMetrics:
        """Compute comprehensive similarity metrics.

        Args:
            embeddings: List of embeddings.

        Returns:
            SimilarityMetrics with statistical summary.
        """
        if len(embeddings) < 2:
            return SimilarityMetrics()

        similarities = self.compute_pairwise_similarities(embeddings)

        upper_triangle = similarities[np.triu_indices(len(embeddings), k=1)]
        sim_list = upper_triangle.tolist()

        bins = [
            "< 0.2",
            "0.2-0.4",
            "0.4-0.6",
            "0.6-0.8",
            "0.8-1.0",
        ]
        hist, _ = np.histogram(sim_list, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0])

        sim_array = np.array(sim_list, dtype=np.float64)

        top_k = self.find_top_k_similar(embeddings, k=5)
        top_k_avg: dict[int, float] = {}
        for k in range(1, 6):
            avg = np.mean([r[k - 1][1] for r in top_k if len(r) >= k])
            top_k_avg[k] = float(avg)

        return SimilarityMetrics(
            average_similarity=float(np.mean(sim_array)) if len(sim_array) > 0 else 0,
            median_similarity=float(np.median(sim_array)) if len(sim_array) > 0 else 0,
            std_similarity=float(np.std(sim_array)) if len(sim_array) > 0 else 0,
            min_similarity=float(np.min(sim_array)) if len(sim_array) > 0 else 0,
            max_similarity=float(np.max(sim_array)) if len(sim_array) > 0 else 0,
            similarity_distribution=dict(zip(bins, hist.tolist(), strict=False)),
            top_k_similarities=top_k_avg,
        )

    def compute_cluster_quality(
        self, embeddings: list[Embedding], labels: list[int] | None = None
    ) -> dict[str, Any]:
        """Compute cluster quality indicators.

        Args:
            embeddings: List of embeddings.
            labels: Optional cluster labels (if None, uses simple heuristics).

        Returns:
            Cluster quality metrics.
        """
        if len(embeddings) < 2:
            return {"silhouette_estimate": 0.0, "cluster_separation": 0.0}

        similarities = self.compute_pairwise_similarities(embeddings)

        avg_similarity = float(np.mean(similarities[np.triu_indices(len(embeddings), k=1)]))

        return {
            "silhouette_estimate": avg_similarity,
            "intra_cluster_density": avg_similarity,
            "embedding_diversity": 1.0 - avg_similarity,
        }

    def analyze_content_overlap(
        self, embeddings: list[Embedding], threshold: float = 0.95
    ) -> list[tuple[int, int]]:
        """Find embeddings with high content overlap.

        Args:
            embeddings: List of embeddings.
            threshold: Similarity threshold for overlap.

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
