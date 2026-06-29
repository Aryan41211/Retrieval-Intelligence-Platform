"""Sentence Transformers embedding provider implementation."""

import time
import uuid
from typing import Any

from sentence_transformers import SentenceTransformer

from backend.data.embeddings.base_embedding_provider import BaseEmbeddingProvider
from backend.data.models.chunk import Chunk
from backend.data.models.embedding import (
    Embedding,
    EmbeddingBatchResult,
    EmbeddingModelInfo,
    EmbeddingResult,
)


class SentenceTransformerProvider(BaseEmbeddingProvider):
    """Embedding provider using Sentence Transformers models."""

    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    MODEL_DIMENSIONS = {
        "all-MiniLM-L6-v2": 384,
        "all-MiniLM-L12-v2": 384,
        "all-mpnet-base-v2": 768,
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
        "intfloat/e5-small-v2": 384,
        "intfloat/e5-base-v2": 768,
        "intfloat/e5-large-v2": 1024,
    }

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        config: dict[str, Any] | None = None,
    ):
        super().__init__(config)
        self._model_name = model_name
        self._model: SentenceTransformer | None = None
        self._model_info = EmbeddingModelInfo(
            name=model_name,
            version="1.0.0",
            dimension=self.MODEL_DIMENSIONS.get(model_name, 384),
            max_sequence_length=512,
            provider="sentence_transformers",
        )

    @property
    def model_info(self) -> EmbeddingModelInfo:
        return self._model_info

    @property
    def name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._model_info.dimension

    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            device = self.get_device()
            try:
                self._model = SentenceTransformer(
                    self._model_name,
                    device=device,
                    cache_folder=self.config.get("model_cache_folder"),
                )
            except Exception:
                if device != "cpu":
                    self._model = SentenceTransformer(
                        self._model_name,
                        device="cpu",
                    )
                    self.config["device"] = "cpu"
                else:
                    raise
        return self._model

    def embed_text(self, text: str) -> Embedding:
        start_time = time.perf_counter()
        model = self._load_model()
        vector = model.encode([text], convert_to_numpy=True)[0]
        processing_time_ms = (time.perf_counter() - start_time) * 1000
        self.validate_embedding_vector(vector.tolist())
        embedding = Embedding(
            chunk_id=uuid.UUID(int=0),
            document_id=uuid.UUID(int=0),
            model_name=self._model_name,
            model_version=self._model_info.version,
            embedding_dimension=len(vector),
            embedding_vector=vector.tolist(),
            processing_time_ms=processing_time_ms,
        )
        embedding.checksum = embedding.compute_checksum()
        return embedding

    def embed_texts(self, texts: list[str]) -> list[Embedding]:
        if not texts:
            return []
        model = self._load_model()
        vectors = model.encode(
            texts,
            batch_size=self.get_batch_size(),
            convert_to_numpy=True,
            show_progress_bar=self.config.get("show_progress", False),
        )
        embeddings = []
        for i, vector in enumerate(vectors):
            self.validate_embedding_vector(vector.tolist())
            embedding = Embedding(
                chunk_id=uuid.UUID(int=i),
                document_id=uuid.UUID(int=i),
                model_name=self._model_name,
                model_version=self._model_info.version,
                embedding_dimension=len(vector),
                embedding_vector=vector.tolist(),
                processing_time_ms=0.0,
            )
            embedding.checksum = embedding.compute_checksum()
            embeddings.append(embedding)
        return embeddings

    def embed_chunks(
        self, chunks: list[Chunk]
    ) -> EmbeddingBatchResult:
        if not chunks:
            return EmbeddingBatchResult(results=[])
        model = self._load_model()
        texts = [chunk.text for chunk in chunks]
        start_time = time.perf_counter()
        vectors = model.encode(
            texts,
            batch_size=self.get_batch_size(),
            convert_to_numpy=True,
            show_progress_bar=self.config.get("show_progress", False),
        )
        total_processing_time_ms = (time.perf_counter() - start_time) * 1000
        results = []
        for _i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            self.validate_embedding_vector(vector.tolist())
            processing_time_ms = total_processing_time_ms / len(chunks)
            embedding = self._create_embedding(chunk, vector.tolist(), processing_time_ms)
            results.append(EmbeddingResult(chunk=chunk, embedding=embedding, cache_hit=False))
        return EmbeddingBatchResult(
            results=results,
            total_processing_time_ms=total_processing_time_ms,
            cache_hits=0,
            cache_misses=len(chunks),
        )
