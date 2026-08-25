# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: builder - resolve and install Python dependencies into a venv.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements-runtime.txt pyproject.toml ./

# torch on PyPI is the CUDA build. Installing it here pulled ~2.5 GB of nvidia_*
# wheels (cublas, cudnn, cufft, nccl, ...) into an image that has no GPU runtime
# and pairs torch with faiss-cpu - gigabytes of dead weight in every push and
# pull. Install the CPU wheel from PyTorch's own index first; the requirements
# install that follows then sees torch already satisfied and does not reach for
# the CUDA variant. Override TORCH_INDEX_URL to build a GPU image.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --upgrade pip \
    && pip install --index-url "${TORCH_INDEX_URL}" "torch>=2.3.0,<3.0.0" \
    && pip install -r requirements-runtime.txt

# ---------------------------------------------------------------------------
# Stage 2: runtime - slim image, non-root, hardened.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    APP_HOME="/app" \
    API_ENVIRONMENT="production" \
    API_HOST="0.0.0.0" \
    API_PORT="8000" \
    API_LOG_FORMAT="json" \
    API_DOCS_ENABLED="false" \
    API_SECURITY_HEADERS_ENABLED="true" \
    API_HSTS_ENABLED="true" \
    API_PROMETHEUS_ENABLED="true"

# Runtime libraries needed by some wheels (e.g. torch, opencv transitive).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Copy application source.
WORKDIR /app
COPY backend ./backend
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Persist the FAISS index and the default SQLite database. Mount a volume
# here; without one, every container restart loses the knowledge base.
ENV VECTOR_STORE_STORAGE_DIR="/app/data/vectorstore" \
    DATABASE_URL="sqlite+aiosqlite:////app/data/rip.db" \
    DB_AUTO_CREATE="false"

# Create a non-root user and grant ownership of the app directory.
RUN mkdir -p /app/data/vectorstore \
    && groupadd --system --gid 1001 rip \
    && useradd --system --uid 1001 --gid rip --home /app rip \
    && chown -R rip:rip /app
USER rip

VOLUME ["/app/data"]

EXPOSE 8000

# Container orchestrator probes.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live').status == 200 else 1)"

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]
CMD ["serve"]
