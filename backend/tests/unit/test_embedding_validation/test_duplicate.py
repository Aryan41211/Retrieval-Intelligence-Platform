"""Tests for duplicate detector."""

import hashlib
from uuid import uuid4

from backend.data.models.embedding import Embedding
from backend.embedding_validation.duplicate_detector import (
    DuplicateDetector,
    DuplicateReport,
)


class TestDuplicateDetector:
    """Tests for DuplicateDetector class."""

    def test_detect_exact_duplicates(self):
        detector = DuplicateDetector()
        vector = [1.0, 0.0, 0.0]

        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=vector,
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=vector,
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.0, 1.0, 0.0],
            ),
        ]

        for e in embeddings[:2]:
            e.checksum = hashlib.sha256(
                "".join(str(v) for v in e.embedding_vector).encode()
            ).hexdigest()

        duplicates = detector.detect_exact_duplicates(embeddings)
        assert len(duplicates) == 1
        assert duplicates[0] == (0, 1)

    def test_detect_exact_duplicates_no_duplicates(self):
        detector = DuplicateDetector()
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[1.0, 0.0, 0.0],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.0, 1.0, 0.0],
            ),
        ]

        duplicates = detector.detect_exact_duplicates(embeddings)
        assert len(duplicates) == 0

    def test_detect_near_duplicates(self):
        detector = DuplicateDetector(threshold=0.95)
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[1.0, 0.0, 0.0],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.99, 0.01, 0.01],
            ),
        ]

        near_dups = detector.detect_near_duplicates(embeddings, threshold=0.95)
        assert len(near_dups) >= 1

    def test_cluster_duplicates(self):
        detector = DuplicateDetector(threshold=0.95)
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[1.0, 0.0, 0.0],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.99, 0.01, 0.01],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.98, 0.02, 0.02],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.0, 0.0, 1.0],
            ),
        ]

        clusters = detector.cluster_duplicates(embeddings)
        assert len(clusters) >= 1
        for cluster in clusters:
            assert len(cluster) >= 2

    def test_generate_report(self):
        detector = DuplicateDetector(threshold=0.95)
        embeddings = [
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[1.0, 0.0, 0.0],
            ),
            Embedding(
                chunk_id=uuid4(),
                document_id=uuid4(),
                model_name="test",
                model_version="1.0",
                embedding_dimension=3,
                embedding_vector=[0.99, 0.01, 0.01],
            ),
        ]

        report = detector.generate_report(embeddings)

        assert isinstance(report, DuplicateReport)
        assert report.total_checked == 2
        assert len(report.near_duplicates) >= 1

    def test_generate_report_empty(self):
        detector = DuplicateDetector()
        report = detector.generate_report([])

        assert isinstance(report, DuplicateReport)
        assert report.total_checked == 0

    def test_compute_hash(self):
        detector = DuplicateDetector()
        vector = [1.0, 0.0, 0.0]
        hash1 = detector.compute_hash(vector)
        hash2 = detector.compute_hash(vector)

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_compute_hash_different_vectors(self):
        detector = DuplicateDetector()
        hash1 = detector.compute_hash([1.0, 0.0, 0.0])
        hash2 = detector.compute_hash([0.0, 1.0, 0.0])

        assert hash1 != hash2
