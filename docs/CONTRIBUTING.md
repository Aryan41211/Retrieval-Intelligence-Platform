# Contribution Guide — Retrieval Intelligence Platform (RIP)

Thanks for contributing! This document explains how to propose changes so they
flow through review cleanly.

---

## 1. Before You Start

- Open an issue describing the change (bug, feature, docs).
- Check [`docs/ROADMAP.md`](../docs/ROADMAP.md) and
  [`TODO.md`](../TODO.md) to avoid duplicate work.
- For large changes, sketch the design in [`docs/architecture/`](../docs/architecture/)
  or an ADR under `docs/architecture/` first.

## 2. Branching

```bash
git checkout -b feat/short-descriptive-name   # features
git checkout -b fix/short-descriptive-name     # fixes
git checkout -b docs/short-descriptive-name    # documentation
```

Base branches off `main`. Keep PRs focused — one logical change per PR.

## 3. Development Workflow

```bash
# 1. Make changes with tests
# 2. Run the quality gates locally
ruff check backend
black backend
mypy backend --explicit-package-bases
pytest

# 3. Commit using Conventional Commits
git commit -m "feat(enterprise): add workspace soft-delete"
```

### Commit Message Format

```
<type>(<scope>): <subject>

<body>            # optional, why & what
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`,
`perf`, `release`. Scopes mirror packages (`enterprise`, `api`, `retrieval`,
`generation`, `docs`, …).

## 4. Coding Standards

- **Type hints** on all public functions; **Google-style docstrings**.
- **No hardcoded secrets** — every config value comes from environment
  variables via `pydantic-settings` and is validated on startup.
- **Tests required** for public APIs (>80% coverage target). Use the existing
  `pytest` + `pytest-asyncio` setup; follow the `backend/tests/` mirror layout.
- **No dead code / TODOs** in shipped code. `print()` is for the benchmark CLI
  only.
- Keep modules small and single-responsibility; prefer composition and
  dependency injection over duplication.

## 5. Pull Request Checklist

- [ ] Tests added/updated and passing (`pytest`)
- [ ] `ruff`, `black`, `mypy` clean
- [ ] Docs updated if behaviour changed (README, `docs/API.md`, architecture)
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] No secrets committed (`.env` is gitignored)
- [ ] PR description explains the *why*

## 6. Review Process

- At least one maintainer approval is required.
- CI must be green (lint, type-check, tests).
- Address review comments with fixups; rebase on `main` before merge when clean.

## 7. Reporting Security Issues

Do **not** open public issues for vulnerabilities. Report privately to the
maintainers so fixes can land before disclosure.

## 8. Code of Conduct

Be respectful, assume good intent, and keep discussions focused on the code
and the user's problem.
