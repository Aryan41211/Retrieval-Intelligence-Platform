# TODO — Phase 5.2 Semantic Retrieval Engine

## Vector Store contract & persistence
- [ ] Extend `backend/vectorstore/base_vector_store.py` with minimal retrieval contract:
  - [ ] `search(...)`
  - [ ] `batch_search(...)` (if feasible without breaking changes)
- [ ] Implement retrieval contract in `backend/vectorstore/faiss_vector_store.py`:
  - [ ] Persist chunk text + metadata per vector ID during `add_embeddings()`
  - [ ] Implement `search(...)` with:
    - [ ] top-k
    - [ ] similarity threshold
    - [ ] metadata/document/source/language/custom filtering (post-candidate)
    - [ ] strongly typed results
  - [ ] Implement `batch_search(...)` (if required by interface)
- [ ] Update `backend/vectorstore/index_serializer.py` to persist/restore the new metadata repository alongside FAISS index.
- [ ] Ensure synchronization for add/remove/update/save/load.

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
- [ ] Add required logging fields:
  - [ ] query latency
  - [ ] retrieved documents/chunks
  - [ ] similarity scores
  - [ ] number of retrieved chunks
  - [ ] errors/warnings
- [ ] Implement retrieval exceptions in `backend/retrieval/exceptions.py`:
  - [ ] `RetrievalError`
  - [ ] `RetrievalTimeoutError`
  - [ ] `RetrievalConfigurationError`
  - [ ] `EmptyRetrievalResultError`

## Tests
- [ ] Add unit tests under `backend/tests/unit/test_retrieval/`:
  - [ ] top-k ordering
  - [ ] similarity threshold filtering
  - [ ] document/source/language/custom filtering
  - [ ] persistence save/load restores metadata

## Validation
- [ ] Run `pytest` (or project test command) to confirm Phase 5.2 passes.
