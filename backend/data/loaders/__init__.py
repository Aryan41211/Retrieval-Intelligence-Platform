"""Document loaders package."""

from backend.data.loaders.base_loader import BaseLoader
from backend.data.loaders.pdf_loader import PDFLoader
from backend.data.loaders.docx_loader import DOCXLoader
from backend.data.loaders.txt_loader import TXTLoader
from backend.data.loaders.markdown_loader import MarkdownLoader
from backend.data.loaders.loader_factory import LoaderFactory

__all__ = [
    "BaseLoader",
    "PDFLoader",
    "DOCXLoader",
    "TXTLoader",
    "MarkdownLoader",
    "LoaderFactory",
]