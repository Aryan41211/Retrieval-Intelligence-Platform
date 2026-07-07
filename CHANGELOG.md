# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 9: Enterprise features — authentication (JWT/OAuth/refresh/password-reset/email-verify), RBAC authorization, user management, multi-user workspaces with shared knowledge bases, persistent collaborative chat (history/search/rename/delete), admin dashboard with analytics and audit/activity logs, and conversation export (JSON/Markdown/PDF)
- Frontend `enterpriseApi` service client and typed enterprise models (`frontend/src/services/enterprise.ts`, `frontend/src/types/api.ts`)
- Comprehensive enterprise test suite (`backend/tests/enterprise/`, 65 tests)
- Config-driven rate-limit toggle (`API_RATE_LIMIT_ENABLED`) for the API middleware

### Changed
- `enterprise.database.get_db` now commits on success and rolls back on error so writes persist (previously flushed but never committed)
- Enterprise settings validated fail-fast; JWT secret is mandatory in production

### Fixed
- Critical data-loss bug: `get_db` discarded all writes on session close

### Added
- Sprint 4: Embedding validation framework with profiling, benchmarking, and duplicate detection
- Sprint 3: Intelligent retrieval pipeline with BM25, RRF fusion, cross-encoder reranking, query expansion, and dynamic top-k selection
- Sprint 2: Embedding pipeline with batch processing, caching, and validation
- Sprint 1: Document loading, preprocessing, chunking, and vector store infrastructure
- End-to-end RAG pipeline orchestrator (`RAGPipeline`) integrating retrieval and generation
- Integration test suite covering 8 validation scenarios for the RAG pipeline
- Missing generation pipeline components: `LLMGateway`, `CitationGenerator`, `ResponseValidator`, `HallucinationGuard`
- Missing LLM provider stubs: `OpenAICompatibleProvider`, `OllamaProvider`, `NIMProvider`
- `GenerationSettings` configuration class and provider factory wiring

### Changed
- Unified exception hierarchy: `VectorStoreError` now inherits from `RipError`
- `ProviderFactory.create()` now reads from unified `GenerationSettings` instead of nested provider config
- Enhanced `GenerationPipeline.from_config()` to build complete pipeline with all components

### Fixed
- Critical import failures in `generation_pipeline.py` caused by missing pipeline component modules
- `ProviderFactory` broken configuration reads for `settings.generation.provider.provider_type`
- Standardized exception base classes across vector store and embedding modules

### Security
- N/A

## [0.1.0] - 2026-06-27

### Added
- Project initialization with clean architecture
- Directory structure following modular design principles
- Core configuration infrastructure
- Development environment setup
- Code quality tooling
- Testing framework configuration

---

## Release Types

- **Major** (`X.0.0`): Incompatible API changes
- **Minor** (`0.X.0`): Backward-compatible functionality additions
- **Patch** (`0.0.X`): Backward-compatible bug fixes

## Change Categories

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

## Versioning

This project uses [Semantic Versioning](https://semver.org/).
Version format: `MAJOR.MINOR.PATCH`

- `MAJOR` version when you make incompatible API changes
- `MINOR` version when you add functionality in a backward compatible manner
- `PATCH` version when you make backward compatible bug fixes

Additional labels for pre-release and build metadata are available as extensions to the MAJOR.MINOR.PATCH format.