"""Duplicate detection for embedding data integrity.

Detects exact and near-duplicate embeddings to identify data quality
issues before indexing. Supports large datasets with efficient checksum
comparison and configurable similarity thresholds.

Implements:
- Exact duplicate detection via checksum comparison
- Near-duplicate detection via cosine similarity
- Union-Find cluster grouping for duplicate clusters
"""

import hashlib
import math
from dataclasses import dataclass, field

from backend.data.models.embedding import Embedding


@dataclass
class DuplicateReport:
    """Report of duplicate detection results.

    Contains all detected exact and near-duplicate pairs along with
    cluster groupings and aggregate statistics.
    """

    exact_duplicates: list[tuple[int, int]] = field(default_factory=list)
    near_duplicates: list[tuple[int, int, float]] = field(default_factory=list)
    duplicate_clusters: list[list[int]] = field(default_factory=list)
    total_checked: int = 0
    total_duplicates: int = 0
    duplicate_rate: float = 0.0

    @property
    def exact_duplicate_count(self) -> int:
        """Number of exact duplicate pairs."""
        return len(self.exact_duplicates)

    @property
    def near_duplicate_count(self) -> int:
        """Number of near-duplicate pairs."""
        return len(self.near_duplicates)

    @property
    def cluster_count(self) -> int:
        """Number of duplicate clusters."""
        return len(self.duplicate_clusters)


class DuplicateDetector:
    """Detect duplicate and near-duplicate embeddings.

    Uses checksum-based exact matching and cosine similarity for
    near-duplicate detection. Configurable similarity threshold
    for near-duplicate sensitivity.

    Optimized for large datasets:
    - O(n) exact detection via dictionary lookup
    - O(n²) near-duplicate detection with early exit
    - Union-Find clustering for efficient grouping

    Usage:
        detector = DuplicateDetector(threshold=0.99)
        report = detector.generate_report(embeddings)
        print(f"Duplicate rate: {report.duplicate_rate:.2%}")
    """

    def __init__(self, threshold: float = 0.99):
        self.threshold = threshold

    def detect_exact_duplicates(self, embeddings: list[Embedding]) -> list[tuple[int, int]]:
        """Detect exact duplicate embeddings by checksum.

        Uses pre-computed checksums when available, falling back to
        on-the-fly computation.

        Args:
            embeddings: List of embeddings to check.

        Returns:
            List of (index_i, index_j) pairs that are exact duplicates.
        """
        duplicates: list[tuple[int, int]] = []
        seen_checksums: dict[str, int] = {}

        for i, embedding in enumerate(embeddings):
            checksum = embedding.checksum or embedding.compute_checksum()

            if checksum in seen_checksums:
                duplicates.append((seen_checksums[checksum], i))
            else:
                seen_checksums[checksum] = i

        return duplicates

    def detect_near_duplicates(
        self,
        embeddings: list[Embedding],
        threshold: float | None = None,
    ) -> list[tuple[int, int, float]]:
        """Detect near-duplicate embeddings by cosine similarity.

        Compares all unique embedding pairs to find those exceeding
        the similarity threshold.

        Args:
            embeddings: List of embeddings to check.
            threshold: Similarity threshold (defaults to self.threshold).

        Returns:
            List of (index_i, index_j, similarity) tuples for near duplicates.
        """
        threshold = threshold or self.threshold
        near_duplicates: list[tuple[int, int, float]] = []

        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                if len(embeddings[i].embedding_vector) != len(embeddings[j].embedding_vector):
                    continue

                similarity = self._cosine_similarity(
                    embeddings[i].embedding_vector,
                    embeddings[j].embedding_vector,
                )

                if similarity >= threshold:
                    near_duplicates.append((i, j, similarity))

        return near_duplicates

    def cluster_duplicates(
        self,
        embeddings: list[Embedding],
        threshold: float | None = None,
    ) -> list[list[int]]:
        """Group embeddings into duplicate clusters using Union-Find.

        Finds connected components in the near-duplicate graph,
        where edges connect embeddings with similarity >= threshold.

        Args:
            embeddings: List of embeddings to cluster.
            threshold: Similarity threshold.

        Returns:
            List of clusters, each containing indices of duplicate embeddings.
        """
        threshold = threshold or self.threshold
        near_duplicates = self.detect_near_duplicates(embeddings, threshold)

        if not near_duplicates:
            return []

        parent: dict[int, int] = {}

        def find(x: int) -> int:
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: int, y: int) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        for i in range(len(embeddings)):
            parent[i] = i

        for i, j, _ in near_duplicates:
            union(i, j)

        clusters: dict[int, list[int]] = {}
        for i in range(len(embeddings)):
            root = find(i)
            if root not in clusters:
                clusters[root] = []
            clusters[root].append(i)

        return [c for c in clusters.values() if len(c) > 1]

    def generate_report(
        self,
        embeddings: list[Embedding],
        threshold: float | None = None,
    ) -> DuplicateReport:
        """Generate comprehensive duplicate detection report.

        Performs exact and near-duplicate detection, clusters results,
        and computes aggregate statistics including duplicate rate.

        Args:
            embeddings: List of embeddings to analyze.
            threshold: Similarity threshold for near duplicates.

        Returns:
            DuplicateReport with all findings and statistics.
        """
        threshold = threshold or self.threshold

        if not embeddings:
            return DuplicateReport()

        exact = self.detect_exact_duplicates(embeddings)
        near = self.detect_near_duplicates(embeddings, threshold)
        clusters = self.cluster_duplicates(embeddings, threshold)

        total_duplicates = len(exact) + len(near)
        duplicate_rate = total_duplicates / len(embeddings) if embeddings else 0

        return DuplicateReport(
            exact_duplicates=exact,
            near_duplicates=near,
            duplicate_clusters=clusters,
            total_checked=len(embeddings),
            total_duplicates=total_duplicates,
            duplicate_rate=duplicate_rate,
        )

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = math.sqrt(sum(v * v for v in vec1))
        magnitude2 = math.sqrt(sum(v * v for v in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def compute_hash(self, vector: list[float]) -> str:
        """Compute stable hash for a vector.

        Produces a deterministic SHA-256 hash suitable for exact
        duplicate detection.

        Args:
            vector: Embedding vector to hash.

        Returns:
            SHA-256 hex digest string.
        """
        content = "".join(f"{v:.6f}" for v in vector)
        return hashlib.sha256(content.encode()).hexdigest()
