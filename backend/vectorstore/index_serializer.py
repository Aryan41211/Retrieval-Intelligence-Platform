"""Index serialization and persistence for vector stores."""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

from backend.vectorstore.exceptions import IndexCorruptionError, IndexLoadError, IndexSaveError
from backend.vectorstore.index_metadata import IndexMetadata


class IndexSerializer:
    """Handles serialization and deserialization of vector indexes.

    Provides persistent storage for FAISS indexes with metadata tracking,
    integrity verification, and version compatibility checks.
    """

    def __init__(self, storage_dir: str | Path):
        """Initialize serializer with storage directory.

        Args:
            storage_dir: Directory for storing index files.
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_index(
        self,
        index: Any,
        metadata: IndexMetadata,
        index_data: dict[str, Any] | None = None,
    ) -> Path:
        """Save index and metadata to disk.

        Args:
            index: FAISS index object.
            metadata: Index metadata.
            index_data: Additional data to save (e.g., ID mappings).

        Returns:
            Path to the saved index file.

        Raises:
            IndexSaveError: If saving fails.
        """
        try:
            # Update metadata
            metadata.update_timestamp()
            metadata.num_embeddings = index.ntotal if hasattr(index, "ntotal") else 0

            # Save FAISS index
            index_path = self.storage_dir / f"{metadata.index_id}.index"
            import faiss

            faiss.write_index(index, str(index_path))

            # Compute checksum
            metadata.checksum = self._compute_file_checksum(index_path)

            # Save metadata
            metadata_path = self.storage_dir / f"{metadata.index_id}.meta.json"
            metadata_dict = metadata.to_dict()
            metadata_path.write_text(json.dumps(metadata_dict, indent=2), encoding="utf-8")

            # Save additional data if provided
            if index_data:
                data_path = self.storage_dir / f"{metadata.index_id}.data.pkl"
                with open(data_path, "wb") as f:
                    pickle.dump(index_data, f)

            return index_path

        except Exception as e:
            raise IndexSaveError(f"Failed to save index: {e}") from e

    def load_index(self, metadata: IndexMetadata) -> tuple[Any, dict[str, Any] | None]:
        """Load index and metadata from disk.

        Args:
            metadata: Index metadata with storage path.

        Returns:
            Tuple of (FAISS index, additional data).

        Raises:
            IndexLoadError: If loading fails.
            IndexCorruptionError: If index is corrupted.
        """
        try:
            import faiss

            index_path = self.storage_dir / f"{metadata.index_id}.index"

            if not index_path.exists():
                raise IndexLoadError(f"Index file not found: {index_path}")

            # Verify checksum
            current_checksum = self._compute_file_checksum(index_path)
            if metadata.checksum and current_checksum != metadata.checksum:
                raise IndexCorruptionError(
                    f"Index checksum mismatch: expected {metadata.checksum}, got {current_checksum}"
                )

            # Load index
            index = faiss.read_index(str(index_path))

            # Load additional data if exists
            data_path = self.storage_dir / f"{metadata.index_id}.data.pkl"
            index_data = None
            if data_path.exists():
                with open(data_path, "rb") as f:
                    index_data = pickle.load(f)  # nosec B301: trusted local FAISS index files only; never untrusted input

            return index, index_data

        except IndexCorruptionError:
            raise
        except Exception as e:
            raise IndexLoadError(f"Failed to load index: {e}") from e

    def delete_index(self, index_id: str) -> None:
        """Delete index files from disk.

        Args:
            index_id: Unique identifier for the index.
        """
        base_path = self.storage_dir / index_id
        for ext in [".index", ".meta.json", ".data.pkl"]:
            file_path = base_path.with_suffix(ext)
            if file_path.exists():
                file_path.unlink()

    def index_exists(self, index_id: str) -> bool:
        """Check if index exists on disk.

        Args:
            index_id: Unique identifier for the index.

        Returns:
            True if index exists, False otherwise.
        """
        index_path = self.storage_dir / f"{index_id}.index"
        return index_path.exists()

    def load_metadata(self, index_id: str) -> IndexMetadata | None:
        """Load metadata from disk.

        Args:
            index_id: Unique identifier for the index.

        Returns:
            IndexMetadata if found, None otherwise.
        """
        metadata_path = self.storage_dir / f"{index_id}.meta.json"
        if not metadata_path.exists():
            return None

        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            return IndexMetadata.from_dict(data)
        except Exception:
            return None

    def _compute_file_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of a file.

        Args:
            file_path: Path to the file.

        Returns:
            Hexadecimal checksum string.
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def verify_integrity(self, metadata: IndexMetadata) -> bool:
        """Verify index file integrity.

        Args:
            metadata: Index metadata to verify.

        Returns:
            True if index is valid, False otherwise.
        """
        try:
            index_path = self.storage_dir / f"{metadata.index_id}.index"
            if not index_path.exists():
                return False

            # Verify checksum
            current_checksum = self._compute_file_checksum(index_path)
            if metadata.checksum and current_checksum != metadata.checksum:
                return False

            # Verify index can be loaded
            import faiss

            index = faiss.read_index(str(index_path))
            return index.ntotal >= 0

        except Exception:
            return False
