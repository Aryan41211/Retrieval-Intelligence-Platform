# CLAUDE.md - Retrieval Intelligence Platform Development Guide

## Project Objective

Build a production-grade Retrieval-Augmented Generation platform with modular architecture, focusing on:
- Document retrieval with explainable reasoning
- Grounded generation with citation support
- Automated evaluation using industry-standard metrics
- Experiment tracking with full reproducibility
- Clean separation of concerns across all pipeline stages

## Engineering Principles

1. **Never break existing functionality** - All changes must maintain backward compatibility or provide clear migration paths
2. **Keep modules small and cohesive** - Each module should have a single, well-defined responsibility
3. **Prefer composition over duplication** - Reuse existing components through well-defined interfaces
4. **Write readable code** - Code is read more often than written; optimize for clarity
5. **Avoid unnecessary abstractions** - Don't create abstractions until you have at least 3 concrete use cases
6. **Avoid premature optimization** - Profile first, optimize second; clarity over cleverness
7. **Never hardcode secrets** - All configuration must come from environment variables
8. **Configuration over convention** - Explicit configuration is preferred over implicit behavior

## Coding Standards

### Python Style
- Follow PEP 8 with Ruff enforcement (line length: 100)
- Use type hints for all public functions and methods
- Prefer `import` over `from x import y` for clarity
- Use Google-style docstrings for public APIs
- Maximum function length: 50 lines (excluding docstrings)
- Maximum class length: 200 lines

### Type Hints
```python
# Good
def retrieve_documents(query: str, top_k: int = 10) -> list[Document]:
    ...

# Avoid
def retrieve_documents(query, top_k=10):
    ...
```

### Error Handling
- Use custom exceptions for domain-specific errors
- Never catch bare `Exception` - be specific
- Log errors with context before re-raising
- Use `Result` types or `Option` types for expected failures

### Async/Await
- Use `async`/`await` for I/O-bound operations
- Don't mix sync and async code unnecessarily
- Use `asyncio.gather` for concurrent operations

### Testing
- Unit tests for all public functions (>80% coverage target)
- Integration tests for cross-module interactions
- Use fixtures for test data setup
- Mock external dependencies (APIs, databases, file systems)

## Folder Responsibilities

```
backend/
├── api/              # FastAPI routes, schemas, dependencies
├── core/             # Core domain logic, interfaces, base classes
├── configs/          # Configuration management, settings
├── data/             # Data layer (separated by pipeline stage)
│   ├── raw/              # Raw, unprocessed input data
│   ├── processed/        # Cleaned, transformed data
│   ├── loaders/          # Document loading implementations
│   ├── preprocessing/    # Text cleaning, normalization
│   ├── chunking/         # Chunking strategies
│   ├── embeddings/       # Embedding providers and utilities
│   ├── vectorstore/      # Vector store abstractions
│   ├── retrieval/        # Retrieval algorithms
│   ├── generation/       # LLM generation pipelines
│   ├── evaluation/       # Evaluation metrics and runners
│   ├── experiments/      # Experiment tracking utilities
│   ├── prompts/          # Prompt templates and management
│   ├── models/           # Domain models, schemas
│   └── utils/            # Shared utilities
├── tests/            # Test suite (mirrors backend structure)
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Packages/Modules | `snake_case` | `vector_store`, `retrieval_service` |
| Classes | `PascalCase` | `DocumentRetriever`, `EmbeddingProvider` |
| Functions/Methods | `snake_case` | `retrieve_documents`, `compute_embeddings` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_TOP_K`, `MAX_CONTEXT_TOKENS` |
| Type Variables | `PascalCase` with `T` prefix | `TDocument`, `TEmbedding` |
| Private Members | `_leading_underscore` | `_internal_cache` |
| Environment Variables | `UPPER_SNAKE_CASE` | `OPENAI_API_KEY`, `VECTOR_STORE_PATH` |
| Test Files | `test_<module>.py` | `test_retrieval_service.py` |
| Test Functions | `test_<functionality>_<scenario>` | `test_retrieve_documents_returns_top_k` |

## General Development Workflow

### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/descriptive-name

# Develop with tests
# Write implementation
# Write unit tests
# Write integration tests (if needed)

# Run quality checks
ruff check .
black --check .
mypy .
pytest -xvs

# Commit with conventional commits
git commit -m "feat: add hybrid retrieval with BM25 and dense fusion"
```

### 2. Code Review Checklist
- [ ] All public APIs have type hints and docstrings
- [ ] Tests cover happy path and edge cases
- [ ] No hardcoded values (use config)
- [ ] No secrets in code
- [ ] Follows existing patterns in codebase
- [ ] Performance implications considered
- [ ] Documentation updated if needed

### 3. Adding Dependencies
1. Add to `requirements.txt` and `pyproject.toml`
2. Pin versions (avoid `>=` without upper bound)
3. Justify in PR description
4. Run `pip-audit` for security

### 4. Configuration Changes
1. Add to `.env.example` with documentation
2. Update `configs/settings.py` with validation
3. Never commit actual `.env` files

## Important Rules

### Configuration
- **All configuration via environment variables** - Use `pydantic-settings`
- **No defaults for secrets** - Require explicit configuration
- **Validate on startup** - Fail fast if config is invalid
- **Document every setting** - Include in `.env.example` with comments

### Data Flow
```
Input → Loader → Preprocessor → Chunker → Embedder → VectorStore
                                              ↓
Query → Expander → Retriever → Reranker → Generator → Output
                                              ↓
                                    Evaluator → Metrics
                                              ↓
                                    ExperimentTracker → Logs
```

### Interface Design
- Define protocols/abstract base classes in `core/`
- Implementations in respective data subdirectories
- Use dependency injection for swapping implementations
- Never instantiate concrete implementations in core logic

### Logging
- Use structured logging (JSON format)
- Include correlation IDs for request tracing
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Never log PII or secrets

### Security
- Validate all inputs at boundaries
- Sanitize user-provided data
- Use parameterized queries for databases
- Rotate secrets regularly
- Audit dependencies with `pip-audit`

### Performance
- Profile before optimizing
- Use connection pooling for databases
- Cache expensive computations
- Batch operations where possible
- Monitor memory usage with large datasets

## Architecture Decision Records

Major architectural decisions should be documented in `docs/adr/` with format:
- `YYYY-MM-DD-short-description.md`
- Include context, decision, consequences, alternatives considered

## CI/CD Pipeline

```yaml
# .github/workflows/ci.yml (active)
- Lint (ruff, black) — full codebase
- Unit Tests (pytest backend/tests/unit)
- Integration Tests (pytest backend/tests/integration)
- Frontend: lint (eslint) → test (vitest) → build (tsc + vite)
- Security Scan (pip-audit, bandit) — advisory only
- Build & Package (python -m build)
- Docker build verification
```

## Useful Commands

```bash
# Install dev dependencies
pip install -e .[dev]

# Run all checks (full codebase, excludes mypy — heavy on this codebase)
ruff check backend/ && black --check backend/ && pytest

# Format code
ruff check --fix backend/ && black backend/

# Run tests with coverage
pytest --cov=backend --cov-report=html

# Generate requirements from pyproject.toml
pip-compile pyproject.toml -o requirements.txt

# Pre-commit (config at .pre-commit-config.yaml)
pre-commit install
pre-commit run --all-files
```

## Anti-Patterns to Avoid

1. **God Classes** - Classes that do everything
2. **Circular Dependencies** - Use dependency inversion
3. **Global State** - Use dependency injection
4. **Magic Strings** - Use enums or constants
5. **Premature Abstraction** - Wait for 3+ use cases
6. **Leaky Abstractions** - Hide implementation details
7. **Sync over Async** - Don't block event loop
8. **Exception Swallowing** - Log and re-raise

## Documentation Standards

- Update README for user-facing changes
- Update CLAUDE.md for process changes
- Add docstrings for all public APIs
- Keep CHANGELOG.md updated
- Document complex algorithms in `docs/`

---

*This document evolves with the project. Update it when conventions change.*