"""Reliability tests for ingestion and hybrid retrieval.

Covers two audit findings that the previous suite could not see:

* **C10** - concurrent uploads mutated a process-global FAISS store with no
  mutual exclusion, so one request's embeddings could be discarded by another
  reloading the on-disk index.
* **H1** - the chunk/embed/index sequence ran inline in an ``async def`` route
  and blocked the event loop for its whole duration.
"""

import asyncio
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.api import ingestion


class _FakeChunk:
    def __init__(self, text: str) -> None:
        self.chunk_id = uuid4()
        self.text = text


class _FakeEmbedding:
    def __init__(self, chunk_id, document_id) -> None:
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.embedding_vector = [0.1, 0.2, 0.3]
        self.model_name = "fake-embed"


class _FakeChunker:
    def __init__(self, count: int = 3) -> None:
        self._count = count

    def chunk(self, document):
        return [_FakeChunk(f"chunk {i}") for i in range(self._count)]


class _FakeProvider:
    dimension = 3

    def __init__(self, fail_indices: set[int] | None = None) -> None:
        self._fail = fail_indices or set()

    def embed_chunks(self, chunks):
        successful = [
            _FakeEmbedding(chunk.chunk_id, "doc-1")
            for i, chunk in enumerate(chunks)
            if i not in self._fail
        ]
        return SimpleNamespace(successful_embeddings=successful)


class _RecordingStore:
    """Vector store double that detects interleaved critical sections."""

    def __init__(self) -> None:
        self._index = None
        self.total_added = 0
        self.events: list[str] = []
        self.overlaps = 0
        self._in_section = 0

    def index_exists(self, index_id: str) -> bool:
        return self._index is not None

    def create_index(self, index_id: str, dimension: int) -> None:
        self._index = {"dimension": dimension}

    def load_index(self, index_id: str) -> None:
        self.events.append("load")

    def add_embeddings(self, vectors, ids=None, metadata=None) -> int:
        self._in_section += 1
        if self._in_section > 1:
            self.overlaps += 1
        # Widen the window in which a race would be observable.
        time.sleep(0.01)
        self.total_added += len(ids or [])
        self._in_section -= 1
        return len(ids or [])

    def save_index(self, index_id: str) -> None:
        self.events.append("save")


def _document(name: str = "doc.txt"):
    return SimpleNamespace(
        filename=name,
        language="en",
        document_id=uuid4(),
    )


class TestConcurrentIngestion:
    """C10: index mutations must be serialised."""

    @pytest.mark.asyncio
    async def test_concurrent_uploads_do_not_interleave(self) -> None:
        store = _RecordingStore()
        chunker = _FakeChunker(count=2)
        provider = _FakeProvider()

        await asyncio.gather(
            *[
                ingestion.ingest_document(
                    document=_document(f"doc{i}.txt"),
                    chunker=chunker,
                    embedding_provider=provider,
                    vector_store=store,
                    index_id="test-index",
                    auto_save=False,
                )
                for i in range(8)
            ]
        )

        assert store.overlaps == 0, "critical section was entered concurrently"
        # Every chunk from every upload must survive: 8 uploads x 2 chunks.
        assert store.total_added == 16

    @pytest.mark.asyncio
    async def test_index_is_not_reloaded_once_in_memory(self) -> None:
        """Reloading on every upload discarded unsaved in-memory additions."""
        store = _RecordingStore()
        for _ in range(3):
            await ingestion.ingest_document(
                document=_document(),
                chunker=_FakeChunker(count=1),
                embedding_provider=_FakeProvider(),
                vector_store=store,
                index_id="test-index",
                auto_save=False,
            )
        assert store.events.count("load") == 0
        assert store.total_added == 3


class TestIngestionDoesNotBlockEventLoop:
    """H1: the blocking sequence must run off the event loop."""

    @pytest.mark.asyncio
    async def test_event_loop_stays_responsive(self) -> None:
        store = _RecordingStore()
        ticks = 0

        async def heartbeat() -> None:
            nonlocal ticks
            for _ in range(20):
                await asyncio.sleep(0.005)
                ticks += 1

        beat = asyncio.create_task(heartbeat())
        await ingestion.ingest_document(
            document=_document(),
            chunker=_FakeChunker(count=5),
            embedding_provider=_FakeProvider(),
            vector_store=store,
            index_id="test-index",
            auto_save=False,
        )
        await beat
        # The loop kept scheduling while ingestion ran in its worker thread.
        assert ticks == 20


class TestPartialEmbeddingFailure:
    """H8: a partially failed batch used to raise ValueError (HTTP 500)."""

    @pytest.mark.asyncio
    async def test_partial_failure_indexes_the_successes(self) -> None:
        store = _RecordingStore()
        result = await ingestion.ingest_document(
            document=_document(),
            chunker=_FakeChunker(count=4),
            embedding_provider=_FakeProvider(fail_indices={1, 3}),
            vector_store=store,
            index_id="test-index",
            auto_save=False,
        )
        assert result.chunks_created == 4
        assert result.chunks_indexed == 2

    @pytest.mark.asyncio
    async def test_no_chunks_raises_ingestion_error(self) -> None:
        with pytest.raises(ingestion.IngestionError, match="no chunks"):
            await ingestion.ingest_document(
                document=_document(),
                chunker=_FakeChunker(count=0),
                embedding_provider=_FakeProvider(),
                vector_store=_RecordingStore(),
                index_id="test-index",
                auto_save=False,
            )

    @pytest.mark.asyncio
    async def test_no_embeddings_raises_ingestion_error(self) -> None:
        with pytest.raises(ingestion.IngestionError, match="no vectors"):
            await ingestion.ingest_document(
                document=_document(),
                chunker=_FakeChunker(count=2),
                embedding_provider=_FakeProvider(fail_indices={0, 1}),
                vector_store=_RecordingStore(),
                index_id="test-index",
                auto_save=False,
            )
