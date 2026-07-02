# TODO — Phase 5.2 Semantic Retrieval Engine

## Vector Store contract & persistence
- [x] Extend `backend/vectorstore/base_vector_store.py` with minimal retrieval contract:
  - [x] `search(...)`
  - [x] `batch_search(...)` (if feasible without breaking changes)
- [x] Implement retrieval contract in `backend/vectorstore/faiss_vector_store.py`:
  - [x] Persist chunk text + metadata per vector ID during `add_embeddings()`
  - [x] Implement `search(...)` with:
    - [x] top-k
    - [x] similarity threshold
    - [x] metadata/document/source/language/custom filtering (post-candidate)
    - [x] strongly typed results
  - [x] Implement `batch_search(...)` (falls back to base implementation)
- [x] Update `backend/vectorstore/index_serializer.py` to persist/restore the new metadata repository alongside FAISS index.
- [x] Ensure synchronization for add/remove/update/save/load.

## Retrieval modules (provider-agnostic semantic engine)
- [ ] Create `backend/retrieval/` modules (as specified):
  - [ ] `__init__.py`
  - [ ] `retrieval_engine.py`
  - [ ] `retrieval_pipeline.py`
  - [ ] `retrieval_request.py`
  - [ ] `retrieval_result.py`
  - [ ] `retrieval_metadata.py`
  - [ ] `retrieval_filters.py`
  - [ ] `retrieval_ranker.py`
  - [ ] `exceptions.py`
- [ ] Implement `retrieval_engine.py`:
  - [ ] `retrieve()`
  - [ ] `retrieve_batch()`
  - [ ] `retrieve_by_document()`
  - [ ] `retrieve_by_chunk()`
  - [ ] `retrieve_with_filters()`
  - [ ] initial ranking using vector similarity only (extensible architecture)
- [ ] Implement `retrieval_pipeline.py`:
  - [ ] log latency + retrieval stats using existing logging approach (stdlib `logging` if no internal logger exists)

## Logging & Errors
- [x] Add required logging fields:
  - [x] query latency
  - [x] retrieved documents/chunks
  - [x] similarity scores
  - [x] number of retrieved chunks
  - [x] errors/warnings
- [x] Implement retrieval exceptions in `backend/retrieval/exceptions.py`:
  - [x] `RetrievalError`
  - [x] `RetrievalTimeoutError`
  - [x] `RetrievalConfigurationError`
  - [x] `EmptyRetrievalResultError`

## Tests
- [ ] Add unit tests under `backend/tests/unit/test_retrieval/`:
  - [ ] top-k ordering
  - [ ] similarity threshold filtering
  - [ ] document/source/language/custom filtering
  - [ ] persistence save/load restores metadata

## Validation
- [ ] Run `pytest` (or project test command) to confirm Phase 5.2 passes.
