# API Documentation — Retrieval Intelligence Platform (RIP)

All endpoints are served under the `/api/v1` prefix and return JSON unless
stated otherwise. Every response carries an `X-API-Version: v1` header, and
`GET /api/version` reports the current version. Interactive docs are available
at `/docs` (Swagger) and `/redoc` when `API_DOCS_ENABLED=true`.

> **Base URL:** `http://localhost:8000/api/v1` (local) or your deployment URL.
> **Auth:** enterprise endpoints require `Authorization: Bearer <access_token>`.

---

## 1. Health & Observability

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health/live` | — | Liveness probe. |
| GET | `/health/ready` | — | Readiness (dependency checks). |
| GET | `/health` | — | Service info (env, version, uptime). |
| GET | `/metrics` | — | Prometheus metrics. |

## 2. Authentication (`/auth`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/register` | — | Self-register; returns tokens. |
| POST | `/auth/login` | — | Login by email or username. |
| POST | `/auth/refresh` | Refresh token | Rotate access/refresh pair. |
| POST | `/auth/logout` | — | Stateless logout. |
| POST | `/auth/password-reset/request` | — | Request reset (idempotent). |
| POST | `/auth/password-reset/confirm` | — | Set new password. |
| POST | `/auth/email/verify` | — | Verify email. |
| GET  | `/auth/oauth/{provider}/login` | — | Begin OAuth (501 if unconfigured). |
| GET  | `/auth/oauth/{provider}/callback` | — | Complete OAuth. |

**Token response**
```json
{ "access_token": "eyJ…", "refresh_token": "eyJ…", "token_type": "bearer", "expires_in": 900 }
```

## 3. Users (`/users`)

| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET  | `/users/me` | authenticated | Current user profile. |
| PATCH| `/users/me` | authenticated | Update `full_name` / `preferences`. |
| GET  | `/users` | `manage_users` | List users (paginated). |
| POST | `/users/{id}/deactivate` | `manage_users` | Activate/deactivate a user. |

## 4. Workspaces (`/workspaces`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/workspaces` | Create workspace (you become owner+member). |
| GET  | `/workspaces` | List workspaces you belong to. |
| GET  | `/workspaces/shared` | List shared-knowledge-base workspaces. |
| GET  | `/workspaces/{id}` | Get a workspace. |
| POST | `/workspaces/{id}/members` | Add a member (owner/admin). |
| DELETE | `/workspaces/{id}/members/{user_id}` | Remove a member. |
| GET  | `/workspaces/{id}/members` | List members. |

## 5. Conversations (`/conversations`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/conversations` | Create a conversation. |
| GET  | `/conversations` | List your conversations (optionally by workspace). |
| GET  | `/conversations/search?q=` | Full-text search by title/content. |
| GET  | `/conversations/{id}` | Get conversation + messages. |
| POST | `/conversations/{id}/messages` | Append a message. |
| PATCH| `/conversations/{id}` | Rename. |
| DELETE | `/conversations/{id}` | Delete (cascade). |
| GET  | `/conversations/{id}/export?fmt=json\|markdown\|pdf` | Export. |

## 6. Administration (`/admin`)

| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET  | `/admin/dashboard` | `view_analytics` | `AdminStats` (users, workspaces, conversations, messages, audit count). |
| GET  | `/admin/audit` | `view_analytics` | `AuditLog` records (activity log). |

## 7. RAG Pipeline

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/chat` | Run the end-to-end RAG pipeline (retrieval → generation). |
| GET  | `/chat` | Conversation history. |
| DELETE | `/chat` | Clear a conversation. |
| POST | `/documents` | Upload/ingest a document. |
| GET  | `/documents` | List ingested documents. |
| POST | `/retrieval` | Retrieve relevant chunks for a query. |
| POST | `/evaluation` | Run evaluation metrics (Ragas / DeepEval). |
| POST | `/experiments` | Log an experiment run. |
| GET  | `/settings` | Read runtime settings. |
| PUT  | `/settings` | Update settings. |

> The RAG endpoints integrate the document pipeline, hybrid retrieval
> (dense + BM25 + RRF fusion), cross-encoder reranking, and grounded
> generation with citations. See [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## 8. Errors

Errors follow RFC 7807-style JSON:

```json
{ "detail": "Invalid credentials" }
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (validation / invalid token). |
| 401 | Missing/invalid/expired credentials. |
| 403 | Authenticated but lacking role/permission. |
| 404 | Resource not found (or not allowed). |
| 409 | Conflict (e.g., duplicate user). |
| 422 | Request body validation error (Pydantic). |
| 429 | Rate limited. |
| 500 | Unhandled server error (logged with correlation ID). |

## 9. Configuration

| Variable | Scope | Notes |
|----------|-------|-------|
| `API_ENVIRONMENT` | API | `development` / `staging` / `production`. |
| `API_DOCS_ENABLED`, `API_RATE_LIMIT_ENABLED` | API | Feature toggles. |
| `DATABASE_URL` | API + Enterprise | SQLAlchemy URL (SQLite/Postgres). |
| `ENTERPRISE_JWT_SECRET_KEY` | Enterprise | **Required**; rejected in production if default. |
| `ENTERPRISE_ACCESS_TOKEN_TTL_SECONDS` | Enterprise | Default 900. |
| `ENTERPRISE_OAUTH_ENABLED` + `OAUTH_GOOGLE_*` | Enterprise | Google login. |
| `OPENAI_API_KEY` (etc.) | Generation | LLM provider keys. |

See [`docs/CONFIGURATION.md`](../docs/CONFIGURATION.md) and
[`DEPLOYMENT.md`](../DEPLOYMENT.md) for the full list.
