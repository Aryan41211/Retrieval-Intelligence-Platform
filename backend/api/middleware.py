"""
Middleware implementations for the FastAPI application.
"""

from typing import Callable
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import Response
from fastapi.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log incoming request and outgoing response."""
        request_id = "req_" + str(hash(request.url))
        
        # Log request
        print(f"[{request_id}] {request.method} {request.url}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        print(f"[{request_id}] {response.status_code} - Duration: {response.headers.get('X-Process-Time', 'unknown')}")
        
        return response


def add_middleware(app: FastAPI):
    """Add middleware to the FastAPI application."""
    app.add_middleware(LoggingMiddleware)
