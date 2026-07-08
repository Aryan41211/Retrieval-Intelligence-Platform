"""End-to-end API integration tests for the real RAG flow.

These tests verify that the data-plane routers now use the *real* retrieval and generation
pipelines (no mocked context), enforce authentication, and honestly report unavailable
features. Heavy components (sentence-transformers model, real LLM) are replaced with
dependency overrides so the suite runs fully offline.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api.dependencies import (
    DEFAULT_INDEX_ID,
    RetrievalService,
    get_current_user,
    get_embedding_provider,
    get_generation_pipeline,
    get_retrieval_service,
    get_vector_store,
)
from backend.data.models.chunk import Chunk
from backend.data.models.embedding import (
    Embedding,
    EmbeddingBatchResult,
    EmbeddingResult,
)
from backend.enterprise.models import User
from backend.generation.generation_pipeline import GenerationPipeline
from backend.retrieval.retrieval_engine import RetrievalEngine
from backend.retrieval.retrieval_pipeline import RetrievalPipeline
from backend.vectorstore.vector_store_factory import VectorStoreFactory

DIM = 8


class FakeEmbeddingProvider:
    """Offline embedding provider used to avoid loading sentence-transformers."""

    dimension = DIM

    def embed_text(self, text: str) -> Embedding:
        return Embedding(
            chunk_id=UUID(int=0),
            document_id=UUID(int=0),
            model_name="fake",
            model_version="1.0.0",
            embedding_dimension=DIM,
            embedding_vector=[0.1] * DIM,
        )

    def embed_chunks(self, chunks: list[Chunk]) -> EmbeddingBatchResult:
        results = []
        for chunk in chunks:
            emb = Embedding(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                model_name="fake",
                model_version="1.0.0",
                embedding_dimension=DIM,
                embedding_vector=[0.1] * DIM,
            )
            results.append(EmbeddingResult(chunk=chunk, embedding=emb))
        return EmbeddingBatchResult(results=results)


@pytest.fixture
def auth_client(tmp_path):
    store = VectorStoreFactory.create("faiss", str(tmp_path))
    store.create_index(DEFAULT_INDEX_ID, dimension=DIM)
    rng = np.random.RandomState(0)
    vectors = rng.rand(5, DIM).astype("float32")
    ids = [str(uuid4()) for _ in range(5)]
    metadatas = [
        {
            "chunk_id": ids[i],
            "document_id": ids[i],
            "chunk_text": f"RIP chunk {i} about retrieval and semantic search",
            "source_filename": f"doc{i}.txt",
            "embedding_model": "fake",
            "language": "en",
            "metadata": {},
            "custom": {},
        }
        for i in range(5)
    ]
    store.add_embeddings(vectors, ids=ids, metadata=metadatas)
    store.save_index(DEFAULT_INDEX_ID)

    provider = FakeEmbeddingProvider()

    def _provider():
        return provider

    def _store():
        return store

    def _retrieval_service():
        return RetrievalService(
            embedding_provider=provider,
            retrieval_pipeline=RetrievalPipeline(RetrievalEngine(store)),
            top_k=10,
        )

    def _generation():
        return GenerationPipeline.from_config()

    def _user():
        return User(id=str(uuid4()), email="test@example.com", username="tester", role="admin", is_active=True)

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_embedding_provider] = _provider
    app.dependency_overrides[get_vector_store] = _store
    app.dependency_overrides[get_retrieval_service] = _retrieval_service
    app.dependency_overrides[get_generation_pipeline] = _generation

    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


AUTH = {"Authorization": "Bearer test-token"}


def test_chat_uses_real_retrieval_not_mock(auth_client: TestClient):
    resp = auth_client.post("/api/v1/chat", json={"query": "retrieval"}, headers=AUTH)
    assert resp.status_code == 200
    body = resp.text
    # The old hardcoded mock filenames must NOT appear.
    assert "ai_documentation.txt" not in body
    assert "ml_research_paper.md" not in body
    assert "healthcare_ai.txt" not in body
    # Real retrieved chunks (from the populated store) must be present.
    assert "retrieved_chunks" in body
    assert "RIP chunk" in body


def test_retrieval_search_returns_real_chunks(auth_client: TestClient):
    resp = auth_client.post(
        "/api/v1/retrieval/search",
        json={"query": "semantic search", "top_k": 3},
        headers=AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_found"] >= 1
    assert any("RIP chunk" in r["content"] for r in data["results"])


def test_documents_upload_then_retrievable(auth_client: TestClient):
    upload = auth_client.post(
        "/api/v1/documents/upload",
        json={
            "filename": "note.txt",
            "content": "The Retrieval Intelligence Platform indexes documents for semantic search.",
        },
        headers=AUTH,
    )
    assert upload.status_code == 200
    assert upload.json()["status"] == "ingested"

    search = auth_client.post(
        "/api/v1/retrieval/search",
        json={"query": "indexes documents", "top_k": 5},
        headers=AUTH,
    )
    assert search.status_code == 200
    contents = [r["content"] for r in search.json()["results"]]
    assert any("Retrieval Intelligence Platform" in c for c in contents)


def test_evaluation_run_is_unavailable_not_simulated(auth_client: TestClient):
    resp = auth_client.post("/api/v1/evaluation/run", json={}, headers=AUTH)
    assert resp.status_code == 501
    assert "not configured" in resp.json()["detail"].lower()


def test_settings_returns_non_sensitive_summary(auth_client: TestClient):
    resp = auth_client.get("/api/v1/settings", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "environment" in data
    assert "retrieval_top_k" in data


def test_protected_endpoint_requires_auth():
    client = TestClient(app)
    resp = client.post("/api/v1/chat", json={"query": "hi"})
    assert resp.status_code == 401
