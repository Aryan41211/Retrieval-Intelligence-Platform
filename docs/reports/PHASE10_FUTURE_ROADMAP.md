# Future Roadmap — Phase 10

**Project:** Retrieval Intelligence Platform (RIP)
**Scope:** Post-v1.0.0 directions for the portfolio and product.

This extends `docs/ROADMAP.md` with a concrete post-release plan. Items are
prioritised; none block the current release.

---

## 1. Near-Term (0–3 months)

| Item | Why | Effort |
|------|-----|--------|
| **Frontend enterprise UI** | Build login/profile/workspace/admin screens on the existing `enterpriseApi`. | M |
| **CI/CD (GitHub Actions)** | Automate `ruff`/`mypy`/`pytest` + image build on PRs. | S |
| **Live screenshots + demo GIF** | Portfolio polish (checklist already provided). | S |
| **Refresh-token denylist** | Server-side revocation for immediate logout. | S |
| **Real SMTP transport** | Wire `_send_email` to SES/SMTP for reset/verify delivery. | S |

## 2. Mid-Term (3–6 months)

| Item | Why | Effort |
|------|-----|--------|
| **GraphRAG / knowledge graphs** | Richer multi-hop retrieval. | L |
| **Streaming responses** | Token-by-token generation (SSE) in chat. | M |
| **Multi-modal ingestion** | Images/tables via vision models + layout-aware chunking. | L |
| **Approximate NN (FAISS IVF/HNSW)** | Scale beyond ~10K vectors. | M |
| **Role-scoped admin dashboards** | Per-workspace analytics. | M |
| **OpenTelemetry traces in UI** | End-to-end latency visibility. | M |

## 3. Long-Term (6–12 months)

| Item | Why |
|------|-----|
| **Multi-model routing & fallbacks** | Resilience across LLM providers. |
| **Self-hosted embedding/LLM options** | Cost + data-sovereignty. |
| **Plugin/connector marketplace** | Notion, Confluence, Jira, Slack ingestion. |
| **Federated workspaces / SSO (SAML/OIDC)** | Enterprise adoption. |
| **Eval-driven auto-optimization** | Tune prompts/retrievers from metric feedback. |

## 4. Technical Debt (tracked)

- Run `mypy` with `--explicit-package-bases` (top-level namespace collisions in
  `backend.generation`, etc.); does not affect runtime.
- Add a server-side refresh-token store (vs. stateless JWT) if revocation SLA
  tightens.
- Expand frontend test coverage (pre-existing type errors in unrelated pages
  should be cleaned before adding new UI).

## 5. Community / Adoption

- Publish a public demo (hosted or local `docker compose`).
- Write a "Building RIP" blog series from the phase reports.
- Add a contributor showcase + example datasets.
- Consider packaging the enterprise layer as an installable FastAPI extension.

---

**Principle:** every roadmap item reuses the existing modular architecture —
no redesigns. Each is a composable stage or a new router behind the same
dependency-injection seams.
