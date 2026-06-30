"""Visualization for embedding quality analysis."""

import math
from typing import Any

import numpy as np

from backend.data.models.embedding import Embedding


class EmbeddingVisualizer:
    """Generate visualizations for embedding analysis."""

    def __init__(self, output_dir: str | None = None):
        self.output_dir = output_dir

    def compute_norm_distribution(
        self, embeddings: list[Embedding]
    ) -> dict[str, Any]:
        """Compute embedding norm distribution data.

        Returns:
            Dictionary with histogram data for norms.
        """
        norms = [self._compute_norm(e.embedding_vector) for e in embeddings]

        if not norms:
            return {"histogram": [], "bins": [], "mean": 0, "std": 0}

        hist, bin_edges = np.histogram(norms, bins=20)

        return {
            "histogram": hist.tolist(),
            "bins": bin_edges.tolist(),
            "mean": float(np.mean(norms)),
            "std": float(np.std(norms)),
            "min": float(np.min(norms)),
            "max": float(np.max(norms)),
            "median": float(np.median(norms)),
        }

    def compute_similarity_histogram(
        self, embeddings: list[Embedding], num_bins: int = 20
    ) -> dict[str, Any]:
        """Compute cosine similarity histogram data.

        Returns:
            Dictionary with histogram data for similarities.
        """
        if len(embeddings) < 2:
            return {"histogram": [], "bins": [], "mean": 0, "std": 0}

        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = self._cosine_similarity(
                    embeddings[i].embedding_vector, embeddings[j].embedding_vector
                )
                similarities.append(sim)

        if not similarities:
            return {"histogram": [], "bins": [], "mean": 0, "std": 0}

        hist, bin_edges = np.histogram(similarities, bins=num_bins, range=(0, 1))

        return {
            "histogram": hist.tolist(),
            "bins": bin_edges.tolist(),
            "mean": float(np.mean(similarities)),
            "std": float(np.std(similarities)),
            "min": float(np.min(similarities)),
            "max": float(np.max(similarities)),
        }

    def compute_latency_histogram(
        self, latencies_ms: list[float], num_bins: int = 20
    ) -> dict[str, Any]:
        """Compute latency histogram data.

        Returns:
            Dictionary with histogram data for latencies.
        """
        if not latencies_ms:
            return {"histogram": [], "bins": [], "mean": 0, "std": 0}

        hist, bin_edges = np.histogram(latencies_ms, bins=num_bins)

        return {
            "histogram": hist.tolist(),
            "bins": bin_edges.tolist(),
            "mean": float(np.mean(latencies_ms)),
            "median": float(np.median(latencies_ms)),
            "std": float(np.std(latencies_ms)),
            "min": float(np.min(latencies_ms)),
            "max": float(np.max(latencies_ms)),
            "p95": float(np.percentile(latencies_ms, 95)),
            "p99": float(np.percentile(latencies_ms, 99)),
        }

    def compute_duplicate_clusters(
        self, embeddings: list[Embedding], threshold: float = 0.99
    ) -> dict[str, Any]:
        """Find and analyze duplicate clusters for visualization.

        Returns:
            Dictionary with cluster information.
        """
        clusters: list[list[int]] = []
        visited: set[int] = set()

        for i in range(len(embeddings)):
            if i in visited:
                continue

            cluster = [i]
            visited.add(i)

            for j in range(i + 1, len(embeddings)):
                if j in visited:
                    continue

                sim = self._cosine_similarity(
                    embeddings[i].embedding_vector, embeddings[j].embedding_vector
                )

                if sim >= threshold:
                    cluster.append(j)
                    visited.add(j)

            if len(cluster) > 1:
                clusters.append(cluster)

        cluster_sizes = [len(c) for c in clusters]

        return {
            "cluster_count": len(clusters),
            "cluster_sizes": cluster_sizes,
            "total_clustered": sum(cluster_sizes),
            "max_cluster_size": max(cluster_sizes) if cluster_sizes else 0,
            "avg_cluster_size": float(np.mean(cluster_sizes)) if cluster_sizes else 0,
        }

    def generate_quality_summary(
        self, embeddings: list[Embedding]
    ) -> dict[str, Any]:
        """Generate overall embedding quality visualization data.

        Returns:
            Dictionary with comprehensive quality metrics.
        """
        norm_data = self.compute_norm_distribution(embeddings)
        sim_data = self.compute_similarity_histogram(embeddings)

        zero_vectors = sum(
            1 for e in embeddings if all(abs(v) < 1e-10 for v in e.embedding_vector)
        )
        normalized_count = sum(
            1 for e in embeddings if abs(self._compute_norm(e.embedding_vector) - 1.0) < 1e-6
        )

        return {
            "total_embeddings": len(embeddings),
            "embedding_dimension": embeddings[0].embedding_dimension if embeddings else 0,
            "norm_distribution": norm_data,
            "similarity_distribution": sim_data,
            "zero_vector_count": zero_vectors,
            "normalized_count": normalized_count,
            "zero_vector_rate": zero_vectors / len(embeddings) if embeddings else 0,
            "normalization_rate": normalized_count / len(embeddings) if embeddings else 0,
        }

    def _compute_norm(self, vector: list[float]) -> float:
        """Compute L2 norm of a vector."""
        return math.sqrt(sum(v * v for v in vector))

    def _cosine_similarity(
        self, vec1: list[float], vec2: list[float]
    ) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = math.sqrt(sum(v * v for v in vec1))
        magnitude2 = math.sqrt(sum(v * v for v in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
