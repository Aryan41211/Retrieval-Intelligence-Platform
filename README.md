# Retrieval Intelligence Platform

A production-grade Retrieval-Augmented Generation platform focused on document retrieval, grounded generation, automated evaluation, explainable retrieval, and experiment tracking.

## Project Overview

The Retrieval Intelligence Platform (RIP) is an enterprise-ready system designed to build, evaluate, and deploy retrieval-augmented generation pipelines at scale. It provides a modular architecture that separates concerns across data ingestion, preprocessing, embedding, retrieval, generation, evaluation, and experimentation — enabling teams to iterate rapidly while maintaining production quality.

## Enterprise Features

The platform ships a full enterprise layer (`backend/enterprise/`) wired into the
API under `/api/v1`:

- **Authentication** — JWT access/refresh tokens (HS256), optional Google OAuth,
  password reset, and email verification. Passwords are bcrypt-hashed.
- **Authorization** — Role-Based Access Control (`admin` / `member` / `viewer`)
  with an explicit permission matrix and FastAPI dependency guards.
- **User management** — profiles, preferences, and admin user administration.
- **Workspaces** — multi-user workspaces with shared knowledge bases and team
  membership/roles.
- **Persistent chat** — conversation history, full-text search, rename, delete,
  and export to JSON / Markdown / PDF.
- **Administration** — dashboard analytics, usage statistics, system health, and
  append-only audit/activity logs.
- **API** — versioned responses (`X-API-Version`), structured audit logging, and
  config-driven, fail-fast settings.

Configuration is environment-driven (`ENTERPRISE_*` variables); the JWT secret is
mandatory and rejected in production if left at the dev default. See
`docs/reports/PHASE9_*.md` for the detailed reports.

## Document Ingestion

The ingestion engine accepts multiple document formats and converts them into a standardized internal Document model for downstream processing.

### Supported Formats

| Format | Extension | Loader |
|--------|-----------|--------|
| Plain Text | `.txt` | TXTLoader |
| Markdown | `.md`, `.markdown` | MarkdownLoader |
| PDF | `.pdf` | PDFLoader |
| Word | `.docx` | DOCXLoader |

Additional formats (PPTX, HTML, CSV) and OCR support are planned.

### Architecture

```
Document File
     │
     ▼
┌─────────────────┐
│  LoaderFactory  │  Select appropriate loader by extension
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Format Loader  │  Extract text + metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Text Cleaning  │  Normalize unicode, whitespace
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Document Model │  Standardized output
└─────────────────┘
```

### How Ingestion Works

1. **Loader Selection**: `LoaderFactory` inspects file extension and returns the appropriate loader
2. **Document Loading**: Each loader extracts text content and extracts format-specific metadata (title, author, page count)
3. **Validation**: Files are validated for existence, size limits, and content
4. **Checksum**: SHA256 checksum is computed for deduplication and integrity
5. **Preprocessing**: `TextCleaner` normalizes whitespace, unicode characters, and removes excessive blank lines
6. **Output**: All loaders produce a standardized `Document` model instance

### Usage

```python
from backend.data.loaders.loader_factory import LoaderFactory

# Load a document
doc = LoaderFactory.load_document("/path/to/document.pdf")

# Access content
print(doc.content)  # Extracted text

# Access metadata
print(doc.metadata.title)
print(doc.metadata.language)
print(doc.checksum)

# Clean the document
from backend.data.preprocessing.text_cleaner import clean_document
cleaned = clean_document(doc)
```

### Configuration

All settings are configurable via environment variables (using pydantic-settings):

```bash
# Maximum file size in MB
INGESTION_MAX_FILE_SIZE_MB=100

# Default encoding for text files
INGESTION_DEFAULT_ENCODING=utf-8

# Default language for documents
INGESTION_DEFAULT_LANGUAGE=en
```

### Error Handling

| Error Type | Description |
|------------|-------------|
| `EmptyDocumentError` | File is empty or contains only whitespace |
| `UnsupportedDocumentTypeError` | File extension not supported |
| `DocumentLoadError` | Could not read/parse the document |
| `FileSizeError` | File exceeds maximum allowed size |
| `ValidationError` | File validation failed |

## Folder Responsibilities

| Folder | Purpose |
|--------|---------|
| `backend/data/loaders/` | Document loading implementations (PDF, DOCX, TXT, MD) |
| `backend/data/preprocessing/` | Text cleaning and normalization |
| `backend/data/models/` | Domain models (Document, DocumentMetadata, etc.) |
| `backend/core/exceptions.py` | Custom exception hierarchy |
| `backend/configs/settings.py` | Configuration management via pydantic-settings |
| `backend/tests/unit/test_loaders/` | Unit tests for loaders |

## Documentation

| Guide | Purpose |
|-------|---------|
| [Architecture](docs/ARCHITECTURE.md) | System overview, data/request flows, auth, module map (with diagrams) |
| [API](docs/API.md) | Full endpoint contract (health, auth, users, workspaces, conversations, admin, RAG) |
| [Developer](docs/DEVELOPER.md) | Local setup, run, test, conventions |
| [Contributing](docs/CONTRIBUTING.md) | Branching, commit format, PR checklist |
| [Benchmarks](docs/BENCHMARKS.md) | Latency, memory, evaluation metrics + methodology |
| [Deployment](DEPLOYMENT.md) | Docker, Railway/Render/AWS/Azure |
| [Architecture deep-dive](docs/architecture/) | 19-part component reference |
| [Release notes v1.0.0](docs/RELEASE_NOTES_v1.0.0.md) | What's in the release |

Phase reports (including enterprise and release) live in
[`docs/reports/`](docs/reports/).

## Roadmap

**Status:** All planned phases are complete. The platform is released as
**v1.0.0** (production-ready + enterprise-grade). See
[`docs/RELEASE_NOTES_v1.0.0.md`](docs/RELEASE_NOTES_v1.0.0.md).

| Phase | Focus Area | Status |
|-------|------------|--------|
| 1 | Document Ingestion Engine | ✅ Complete |
| 2 | Chunking Strategies | ✅ Complete |
| 3 | Embedding Integration | ✅ Complete |
| 4 | Vector Store & Retrieval | ✅ Complete |
| 4.1–4.3 | Embedding Validation & Benchmarking | ✅ Complete |
| 4.5 | Experiment Tracking (foundation) | ✅ Complete |
| 5 | Grounded Generation | ✅ Complete |
| 6 | Evaluation Framework | ✅ Complete |
| 7 | Experiment Tracking (MLflow / WandB) | ✅ Complete |
| 8 | Production Engineering | ✅ Complete |
| 9 | Enterprise Features | ✅ Complete |
| 10 | Final Release & Portfolio | ✅ Complete |

## License

This project is licensed under the MIT License.