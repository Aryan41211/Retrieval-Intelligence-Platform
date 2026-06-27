# Retrieval Intelligence Platform

A production-grade Retrieval-Augmented Generation platform focused on document retrieval, grounded generation, automated evaluation, explainable retrieval, and experiment tracking.

## Project Overview

The Retrieval Intelligence Platform (RIP) is an enterprise-ready system designed to build, evaluate, and deploy retrieval-augmented generation pipelines at scale. It provides a modular architecture that separates concerns across data ingestion, preprocessing, embedding, retrieval, generation, evaluation, and experimentation — enabling teams to iterate rapidly while maintaining production quality.

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
```

### Error Handling

| Error Type | Description |
|------------|-------------|
| `EmptyDocumentError` | File is empty or contains only whitespace |
| `UnsupportedDocumentTypeError` | File extension not supported |
| `DocumentLoadError` | Could not read/parse the document |
| `ValidationError` | File validation failed |

## Folder Responsibilities

| Folder | Purpose |
|--------|---------|
| `backend/loaders/` | Document loading implementations (PDF, DOCX, TXT, MD) |
| `backend/preprocessing/` | Text cleaning and normalization |
| `backend/models/` | Domain models (Document, DocumentMetadata, etc.) |
| `backend/tests/` | Test suite |
| `docs/architecture/` | System architecture documentation |

## Roadmap

| Phase | Focus Area | Status |
|-------|------------|--------|
| 1 | Document Ingestion Engine | ✅ Complete |
| 2 | Chunking Strategies | ⏳ Planned |
| 3 | Embedding Integration | ⏳ Planned |
| 4 | Vector Store & Retrieval | ⏳ Planned |
| 5 | Grounded Generation | ⏳ Planned |
| 6 | Evaluation Framework | ⏳ Planned |
| 7 | Experiment Tracking | ⏳ Planned |

## License

This project is licensed under the MIT License.