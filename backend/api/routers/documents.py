"""Document API router.

Two ingestion paths, both namespace-scoped:

* ``POST /documents/upload``      - JSON body with inline text.
* ``POST /documents/upload/file`` - multipart file upload (PDF, DOCX, MD, TXT),
  parsed through the loader registry.

Documents are written to the caller's private knowledge base, or to a workspace
they have permission to write to. The chunk/embed/index sequence is CPU-bound
and synchronous, so it runs in a worker thread under a per-namespace write lock.
"""

import logging
import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies import (
    get_chunker,
    get_current_user,
    get_embedding_provider,
    get_namespace_store,
)
from backend.api.ingestion import IngestionError, ingest_document
from backend.api.namespaces import (
    NamespaceError,
    readable_namespaces,
    writable_namespace,
)
from backend.api.schemas import (
    DocumentSummary,
    DocumentUploadRequest,
    DocumentUploadResponse,
)
from backend.configs.settings import get_settings
from backend.core.exceptions import (
    DocumentLoadError,
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
)
from backend.data.loaders.loader_factory import LoaderFactory
from backend.data.models.document import Document
from backend.enterprise.database import get_db
from backend.enterprise.models import User

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


async def _resolve_namespace(db: AsyncSession, user: User, workspace_id: str | None):
    """Resolve the write namespace, translating domain errors to HTTP errors."""
    try:
        return await writable_namespace(db, user, workspace_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NamespaceError as exc:  # pragma: no cover - ids come from the database
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workspace identifier"
        ) from exc


async def _ingest(
    *,
    document: Document,
    namespace,
    embedding_provider: object,
    chunker: object,
) -> DocumentUploadResponse:
    """Run ingestion for a prepared document and build the API response."""
    try:
        result = await ingest_document(
            document=document,
            chunker=chunker,
            embedding_provider=embedding_provider,
            vector_store=get_namespace_store(namespace.index_id),
            index_id=namespace.index_id,
            auto_save=get_settings().vector_store.auto_save,
        )
    except IngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return DocumentUploadResponse(
        document_id=document.document_id,
        filename=document.filename,
        status="ingested",
        message=(f"Ingested {result.chunks_indexed} chunk(s) into {namespace.label}."),
        namespace=namespace.label,
        chunks_indexed=result.chunks_indexed,
    )


@router.get("/documents")
async def get_documents() -> dict[str, str]:
    """Document API status."""
    return {"message": "Document API is running"}


@router.get("/documents/supported-formats")
async def supported_formats() -> dict[str, object]:
    """Report which file types the upload endpoint accepts."""
    ingestion = get_settings().ingestion
    return {
        "extensions": sorted(ingestion.supported_extensions),
        "max_file_size_mb": ingestion.max_file_size_mb,
    }


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    payload: DocumentUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embedding_provider: object = Depends(get_embedding_provider),
    chunker: object = Depends(get_chunker),
) -> DocumentUploadResponse:
    """Ingest a document supplied as inline text.

    Writes to the caller's private knowledge base unless ``workspace_id`` names a
    workspace they may write to.
    """
    if not payload.content or not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document content must be non-empty",
        )

    namespace = await _resolve_namespace(db, current_user, payload.workspace_id)

    document = Document(
        filename=payload.filename,
        file_extension=Path(payload.filename).suffix or ".txt",
        source_path=payload.filename,
        title=payload.filename,
        language="en",
        content=payload.content,
        file_size=len(payload.content.encode("utf-8")),
    )

    return await _ingest(
        document=document,
        namespace=namespace,
        embedding_provider=embedding_provider,
        chunker=chunker,
    )


def _safe_filename(raw: str | None) -> str:
    """Return a filename stripped of any directory component.

    The uploaded name is attacker-controlled and is used to build a temporary
    path, so only the final component is kept.
    """
    candidate = Path(raw or "upload").name.strip()
    if not candidate or candidate in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid filename",
        )
    return candidate[:255]


def _load_document(path: Path, filename: str) -> Document:
    """Parse a file from disk into a Document. Blocking; run in a thread.

    Args:
        path: Staged temporary file to read.
        filename: The user-supplied name to record on the document.

    Returns:
        The loaded document, re-labelled with the original filename.
    """
    loader = LoaderFactory.get_loader(Path(filename).suffix.lower())
    document = loader.load(str(path))
    # The loader records the temporary path; restore the user-facing name so
    # citations and filters show what the user actually uploaded.
    return document.model_copy(
        update={
            "filename": filename,
            "source_path": filename,
            "title": document.title or filename,
        }
    )


@router.post(
    "/documents/upload/file",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_file(
    file: UploadFile = File(..., description="PDF, DOCX, Markdown or plain-text file"),
    workspace_id: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embedding_provider: object = Depends(get_embedding_provider),
    chunker: object = Depends(get_chunker),
) -> DocumentUploadResponse:
    """Ingest an uploaded file.

    The file is parsed by the loader registered for its extension, so PDF, DOCX,
    Markdown and plain-text documents are all supported. Previously the API
    accepted inline text only and the loader package was unreachable.
    """
    settings = get_settings().ingestion
    filename = _safe_filename(file.filename)
    extension = Path(filename).suffix.lower()

    if extension not in {ext.lower() for ext in settings.supported_extensions}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{extension or "(none)"}'. "
                f"Supported: {', '.join(sorted(settings.supported_extensions))}"
            ),
        )

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    contents = await file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum size of {settings.max_file_size_mb} MB",
        )
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uploaded file is empty"
        )

    namespace = await _resolve_namespace(db, current_user, workspace_id)

    # Loaders read from a path, so the upload is staged in a temporary file that
    # is always removed, including on parse failure.
    with tempfile.TemporaryDirectory() as tmp_dir:
        staged = Path(tmp_dir) / filename
        staged.write_bytes(contents)
        try:
            document = await run_in_threadpool(_load_document, staged, filename)
        except EmptyDocumentError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{filename} contains no extractable text",
            ) from exc
        except DocumentLoadError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not read {filename}: {exc}",
            ) from exc
        except UnsupportedDocumentTypeError as exc:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
            ) from exc

    return await _ingest(
        document=document,
        namespace=namespace,
        embedding_provider=embedding_provider,
        chunker=chunker,
    )


@router.get("/documents/list", response_model=list[DocumentSummary])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentSummary]:
    """List the documents indexed in every knowledge base the caller can read.

    Derived from the vector store's own records rather than a separate registry
    table, so the listing can never disagree with what retrieval will actually
    find.
    """
    namespaces = await readable_namespaces(db, current_user)
    summaries: dict[str, DocumentSummary] = {}

    for namespace in namespaces:
        store = get_namespace_store(namespace.index_id)
        records = getattr(store, "_vector_records", {}) or {}
        for record in records.values():
            document_id = str(record.get("document_id") or "")
            if not document_id:
                continue
            key = f"{namespace.index_id}:{document_id}"
            existing = summaries.get(key)
            if existing is None:
                summaries[key] = DocumentSummary(
                    document_id=document_id,
                    filename=record.get("source_filename") or "(unknown)",
                    namespace=namespace.label,
                    chunk_count=1,
                    status="indexed",
                )
            else:
                summaries[key] = existing.model_copy(
                    update={"chunk_count": existing.chunk_count + 1}
                )

    return sorted(summaries.values(), key=lambda d: d.filename.lower())


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    workspace_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Remove a document's chunks from a knowledge base the caller may write to.

    Args:
        document_id: Document whose chunks should be removed.
        workspace_id: Workspace to delete from; omit for the private namespace.
    """
    namespace = await _resolve_namespace(db, current_user, workspace_id)
    store = get_namespace_store(namespace.index_id)

    records = getattr(store, "_vector_records", {}) or {}
    doomed = [
        embedding_id
        for embedding_id, record in records.items()
        if str(record.get("document_id") or "") == document_id
    ]
    if not doomed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found in this knowledge base",
        )

    removed = await run_in_threadpool(store.remove_embeddings, doomed)
    if get_settings().vector_store.auto_save:
        await run_in_threadpool(store.save_index, namespace.index_id)

    return {"document_id": document_id, "chunks_removed": removed, "namespace": namespace.label}
