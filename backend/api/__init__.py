"""
Retrieval Intelligence Platform API package.

The ASGI application is exposed as ``app`` for uvicorn (``backend.api:app``)
and the factory as ``create_application`` for tests and embedding.
"""

from .app import app, create_application

__all__ = ["app", "create_application"]
