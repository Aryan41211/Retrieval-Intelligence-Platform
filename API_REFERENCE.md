# API Reference

**Base URL:** `http://localhost:8000/api/v1` (local) or your deployment URL.  
**Auth:** Enterprise endpoints require `Authorization: Bearer <access_token>`.  
**Version header:** Every response carries `X-API-Version: v1`.  
**Interactive docs:** `/docs` (Swagger) and `/redoc` when `API_DOCS_ENABLED=true`.

---

## 1. Health & Observability

Unauthenticated endpoints for monitoring and orchestration.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/health/live` | Liveness probe — always returns 200 |
| GET | `/api/v1/health/ready` | Readiness probe — checks dependencies |
| GET | `/api/v1/health` | Service info (env, version, uptime) |
| GET | `/api/v1/metrics` | Prometheus metrics |

## 2. Authentication (`/api/v1/auth`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/register` | — | Self-register; returns tokens |
| POST | `/auth/login` | — | Login by email or username |
| POST | `/auth/refresh` | Refresh token | Rotate access/refresh pair |
| POST | `/auth/logout` | — | Stateless logout |
| POST | `/auth/password-reset/request` | — | Request password reset (idempotent) |
| POST | `/auth/password-reset/confirm` | — | Set new password with reset token |
| POST | `/auth/email/verify` | — | Verify email address |
| GET  | `/auth/oauth/{provider}/login` | — | Begin OAuth flow (501 if unconfigured) |
| GET  | `/auth/oauth/{provider}/callback` | — | Complete OAuth flow |

### Token Response

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

- Access token TTL: configurable via `ENTERPRISE_ACCESS_TOKEN_TTL_SECONDS` (default 900s)
- Refresh token TTL: configurable via `ENTERPRISE_REFRESH_TOKEN_TTL_SECONDS` (default 604800s)

## 3. Users (`/api/v1/users`)

| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET  | `/users/me` | authenticated | Current user profile |
| PATCH| `/users/me` | authenticated | Update `full_name` / `preferences` |
| GET  | `/users` | `manage_users` | List users (paginated) |
| POST | `/users/{id}/deactivate` | `manage_users` | Activate/deactivate a user |

## 4. Workspaces (`/api/v1/workspaces`)

| Method | Path | Purpose |
|--------|------|---------|
| POST   | `/workspaces` | Create workspace (you become owner+member) |
| GET    | `/workspaces` | List workspaces you belong to |
| GET    | `/workspaces/shared` | List shared-knowledge-base workspaces |
| GET    | `/workspaces/{id}` | Get a workspace |
| POST   | `/workspaces/{id}/members` | Add a member (owner/admin) |
| DELETE | `/workspaces/{id}/members/{user_id}` | Remove a member |
| GET    | `/workspaces/{id}/members` | List members |

## 5. Conversations (`/api/v1/conversations`)

| Method | Path | Purpose |
|--------|------|---------|
| POST   | `/conversations` | Create a conversation |
| GET    | `/conversations` | List your conversations (optionally by workspace) |
| GET    | `/conversations/search?q=` | Full-text search by title/content |
| GET    | `/conversations/{id}` | Get conversation + messages |
| POST   | `/conversations/{id}/messages` | Append a message |
| PATCH  | `/conversations/{id}` | Rename conversation |
| DELETE | `/conversations/{id}` | Delete conversation (cascade) |
| GET    | `/conversations/{id}/export?fmt=json\|markdown\|pdf` | Export conversation |

## 6. Administration (`/api/v1/admin`)

| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET | `/admin/dashboard` | `view_analytics` | Dashboard stats (users, workspaces, conversations, audit count) |
| GET | `/admin/audit` | `view_analytics` | Audit log records (activity log) |

## 7. RAG Pipeline (`/api/v1`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/chat` | Run end-to-end RAG pipeline (retrieval → generation) |
| GET  | `/chat` | Conversation history |
| DELETE | `/chat` | Clear a conversation |
| POST | `/documents` | Upload and ingest a document |
| GET  | `/documents` | List ingested documents |
| POST | `/retrieval` | Retrieve relevant chunks for a query |
| POST | `/evaluation` | Run evaluation metrics (Ragas / DeepEval) |
| POST | `/experiments` | Log an experiment run |
| GET  | `/settings` | Read runtime settings |
| PUT  | `/settings` | Update runtime settings |

### Chat Request

```json
{
  "message": "What is the capital of France?",
  "conversation_id": "uuid-optional",
  "workspace_id": "uuid-optional",
  "stream": false
}
```

### Chat Response (non-streaming)

```json
{
  "message": "The capital of France is Paris.",
  "conversation_id": "uuid",
  "citations": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "text": "Paris is the capital and most populous city of France.",
      "relevance_score": 0.95
    }
  ],
  "latency_ms": 2340
}
```

### Chat Response (streaming)

When `stream: true`, the endpoint returns a Server-Sent Events (SSE) stream:

```
data: {"type": "token", "content": "The"}
data: {"type": "token", "content": " capital"}
data: {"type": "token", "content": " of"}
...
data: {"type": "citations", "content": [...]}
data: {"type": "done", "content": null}
```

### Document Upload

```http
POST /api/v1/documents
Content-Type: multipart/form-data

file: @document.pdf
```

Response:

```json
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "status": "ingested",
  "chunks_count": 42,
  "checksum": "sha256-hash"
}
```

### Retrieval Request

```json
{
  "query": "What is the capital of France?",
  "top_k": 10,
  "filters": {
    "document_id": "uuid-optional",
    "metadata": {}
  }
}
```

### Retrieval Response

```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "text": "Paris is the capital and most populous city of France.",
      "score": 0.95,
      "metadata": {
        "title": "France Overview",
        "page": 3
      }
    }
  ],
  "latency_ms": 120,
  "total_results": 10
}
```

## 8. Error Responses

Errors follow a standard JSON format:

```json
{ "detail": "Error description" }
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (validation error, invalid token) |
| 401 | Missing, invalid, or expired credentials |
| 403 | Authenticated but lacking required permission |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate user) |
| 422 | Request body validation error (Pydantic) |
| 429 | Rate limited (see `Retry-After` header) |
| 500 | Unhandled server error (logged with correlation ID) |

## 9. Rate Limiting

Rate limiting is in-memory per-process. Configured via:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_RATE_LIMIT_PER_MINUTE` | 120 | Sustained requests per minute per client IP |
| `API_RATE_LIMIT_BURST` | 20 | Extra burst capacity above sustained rate |

When rate-limited, the API returns `429 Too Many Requests` with a
`Retry-After` header indicating seconds until the limit resets.

## 10. Configuration Variables

### API Core

| Variable | Default | Description |
|----------|---------|-------------|
| `API_ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `API_HOST` | `0.0.0.0` | Bind host |
| `API_PORT` | `8000` | Bind port (overridden by `$PORT` on PaaS) |
| `API_DOCS_ENABLED` | `true` | Expose `/docs`, `/redoc`. Auto-disabled in production |
| `API_LOG_FORMAT` | `json` | `json` or `text` |

### API Security

| Variable | Default | Description |
|----------|---------|-------------|
| `API_CORS_ORIGINS` | `["*"]` | Allowed origins. Must be explicit in production |
| `API_CORS_CREDENTIALS` | `false` | Allow credentialed requests |
| `API_SECURITY_HEADERS_ENABLED` | `true` | Emit security headers |
| `API_HSTS_ENABLED` | `false` | Emit Strict-Transport-Security (enable only behind TLS) |

### Enterprise

| Variable | Default | Description |
|----------|---------|-------------|
| `ENTERPRISE_JWT_SECRET_KEY` | _(required)_ | **Must be set.** Generate with `openssl rand -hex 32` |
| `ENTERPRISE_ACCESS_TOKEN_TTL_SECONDS` | `900` | Access token lifetime |
| `ENTERPRISE_REFRESH_TOKEN_TTL_SECONDS` | `604800` | Refresh token lifetime (7 days) |
| `ENTERPRISE_REGISTRATION_ENABLED` | `true` | Allow self-registration |
| `ENTERPRISE_OAUTH_ENABLED` | `false` | Enable Google OAuth |

### LLM Providers

| Variable | Default | Provider |
|----------|---------|----------|
| `OPENAI_API_KEY` | — | OpenAI |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI |
| `ANTHROPIC_API_KEY` | — | Anthropic |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | Anthropic |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama |
| `OLLAMA_MODEL` | `llama3` | Ollama |
| `NIM_API_KEY` | — | NVIDIA NIM |
| `NIM_MODEL` | `meta/llama3-8b-instruct` | NVIDIA NIM |

### Embeddings

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-Transformers model name |
| `EMBEDDING_BATCH_SIZE` | `32` | Batch size for embedding generation |
| `EMBEDDING_CACHE_ENABLED` | `true` | Enable embedding cache |

### Database & Cache

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./rip.db` | SQLAlchemy connection string |
| `REDIS_URL` | — | Redis connection string (optional, for caching) |

See [CONFIGURATION.md](docs/CONFIGURATION.md) for the full reference.
