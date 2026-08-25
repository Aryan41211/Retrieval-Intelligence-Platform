#!/usr/bin/env python
"""Prepare a host for `docker compose up`.

Two secrets have to exist before the stack will start, and neither has a safe
default:

* ``ENTERPRISE_JWT_SECRET_KEY`` - compose refuses to start without it, and the
  settings layer rejects short or low-entropy values.
* ``API_METRICS_TOKEN`` - Prometheus cannot log in, so it presents a bearer
  token read from ``deploy/metrics_token``. The API must be given the same
  value or every scrape returns 401.

Keeping those two in sync by hand is the most common reason a first deployment
comes up half-working, so this script generates both and writes them to the
right places.

Usage::

    python scripts/bootstrap_deployment.py           # fill in what is missing
    python scripts/bootstrap_deployment.py --force    # regenerate both secrets
    python scripts/bootstrap_deployment.py --check    # verify, change nothing
"""

from __future__ import annotations

import argparse
import pathlib
import re
import secrets
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
METRICS_TOKEN_FILE = REPO_ROOT / "deploy" / "metrics_token"

JWT_KEY = "ENTERPRISE_JWT_SECRET_KEY"
METRICS_KEY = "API_METRICS_TOKEN"

# The following three mirror EnterpriseSettings in backend/enterprise/config.py.
# They are duplicated rather than imported because that module validates its
# settings at import time and raises without a signing secret - the very
# situation this script exists to fix, so importing it here would make the
# bootstrap unusable on a fresh host. A unit test asserts the copies stay in
# sync with the originals.
MIN_JWT_LENGTH = 32
MIN_JWT_VARIETY = 8
PLACEHOLDER_MARKERS = (
    "change-in-production",
    "change-me",
    "change_me",
    "changeme",
    "changein",
    "ci-only",
    "dev-secret",
    "dummy",
    "example",
    "insecure",
    "not-a-real",
    "not-for-prod",
    "placeholder",
    "sample",
    "test-secret",
    "your-secret",
)


def placeholder_marker(value: str) -> str | None:
    """Return the placeholder marker found in ``value``, if any.

    Args:
        value: A candidate signing secret.

    Returns:
        The first matching marker, or ``None`` when the value shows no sign of
        being a copied placeholder.
    """
    lowered = value.strip().lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker in lowered:
            return marker
    return None


def secret_problem(value: str) -> str | None:
    """Return why ``value`` is unfit to sign production tokens, or ``None``.

    Length alone used to be the only gate here, which let
    ``.env.example``'s own placeholder through: it is 48 characters, so the
    bootstrap left it in place and ``--check`` reported success, and then the
    API refused to boot with ``API_ENVIRONMENT=production``. The preflight has
    to reject exactly what production rejects or it is not a preflight.

    Args:
        value: A candidate signing secret.

    Returns:
        A human-readable problem description, or ``None`` when the value is fit.
    """
    if len(value) < MIN_JWT_LENGTH:
        return f"is {len(value)} characters; at least {MIN_JWT_LENGTH} are required"
    marker = placeholder_marker(value)
    if marker is not None:
        return (
            f"looks like a placeholder (contains {marker!r}); the API refuses to "
            "start with API_ENVIRONMENT=production"
        )
    if len(set(value)) < MIN_JWT_VARIETY:
        return "has too little variety to be random"
    return None


def read_env_value(text: str, key: str) -> str | None:
    """Return the value assigned to ``key``, or ``None`` if it is unset.

    Args:
        text: Full contents of a dotenv-style file.
        key: Variable name to look up.

    Returns:
        The assigned value with surrounding quotes stripped, or ``None`` when
        the key is absent or assigned an empty value.
    """
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, flags=re.MULTILINE)
    if match is None:
        return None
    value = match.group(1).strip().strip("'\"")
    return value or None


def set_env_value(text: str, key: str, value: str) -> str:
    """Return ``text`` with ``key`` assigned ``value``.

    The key is rewritten in place when present so generated comments and
    ordering survive; otherwise it is appended.

    Args:
        text: Full contents of a dotenv-style file.
        key: Variable name to assign.
        value: Value to write.

    Returns:
        The updated file contents.
    """
    replacement = f"{key}={value}"
    pattern = rf"^{re.escape(key)}=.*$"
    if re.search(pattern, text, flags=re.MULTILINE):
        return re.sub(pattern, replacement, text, count=1, flags=re.MULTILINE)
    separator = "" if text.endswith("\n") else "\n"
    return f"{text}{separator}{replacement}\n"


def _write_metrics_token(token: str) -> None:
    """Write the Prometheus bearer token file.

    Written without a trailing newline: Prometheus trims surrounding whitespace,
    but an exact match keeps the file readable as the literal token.

    Args:
        token: The bearer token to persist.
    """
    METRICS_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    METRICS_TOKEN_FILE.write_text(token, encoding="utf-8")


def check() -> int:
    """Report whether the host is ready to start the stack.

    Returns:
        ``0`` when both secrets are present and consistent, ``1`` otherwise.
    """
    problems: list[str] = []

    if not ENV_FILE.exists():
        problems.append(f"{ENV_FILE.name} does not exist (run without --check to create it)")
        env_text = ""
    else:
        env_text = ENV_FILE.read_text(encoding="utf-8")

    jwt_secret = read_env_value(env_text, JWT_KEY)
    if jwt_secret is None:
        problems.append(f"{JWT_KEY} is unset; the API will refuse to start")
    else:
        problem = secret_problem(jwt_secret)
        if problem is not None:
            problems.append(f"{JWT_KEY} {problem}")

    metrics_token = read_env_value(env_text, METRICS_KEY)
    if metrics_token is None:
        problems.append(f"{METRICS_KEY} is unset; Prometheus scrapes will return 401")
    elif not METRICS_TOKEN_FILE.exists():
        problems.append(
            f"{METRICS_TOKEN_FILE.relative_to(REPO_ROOT)} is missing; Prometheus has no token to present"
        )
    elif METRICS_TOKEN_FILE.read_text(encoding="utf-8").strip() != metrics_token:
        problems.append(
            f"{METRICS_TOKEN_FILE.relative_to(REPO_ROOT)} does not match {METRICS_KEY} in .env"
        )

    if problems:
        print("Deployment prerequisites are not satisfied:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("Deployment prerequisites satisfied.")
    return 0


def bootstrap(force: bool = False) -> int:
    """Create ``.env`` and the metrics token file, generating missing secrets.

    Args:
        force: Regenerate both secrets even when they already have values.

    Returns:
        ``0`` on success, ``1`` when ``.env.example`` is missing.
    """
    if not ENV_FILE.exists():
        if not ENV_EXAMPLE.exists():
            print(f"error: neither {ENV_FILE.name} nor {ENV_EXAMPLE.name} exists", file=sys.stderr)
            return 1
        ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"created {ENV_FILE.name} from {ENV_EXAMPLE.name}")

    env_text = ENV_FILE.read_text(encoding="utf-8")
    actions: list[str] = []

    jwt_secret = read_env_value(env_text, JWT_KEY)
    if force or jwt_secret is None or secret_problem(jwt_secret) is not None:
        env_text = set_env_value(env_text, JWT_KEY, secrets.token_hex(32))
        actions.append(f"generated {JWT_KEY}")

    metrics_token = read_env_value(env_text, METRICS_KEY)
    if force or metrics_token is None:
        metrics_token = secrets.token_urlsafe(32)
        env_text = set_env_value(env_text, METRICS_KEY, metrics_token)
        actions.append(f"generated {METRICS_KEY}")

    ENV_FILE.write_text(env_text, encoding="utf-8")

    existing = (
        METRICS_TOKEN_FILE.read_text(encoding="utf-8").strip()
        if METRICS_TOKEN_FILE.exists()
        else None
    )
    if existing != metrics_token:
        _write_metrics_token(metrics_token)
        actions.append(f"wrote {METRICS_TOKEN_FILE.relative_to(REPO_ROOT).as_posix()}")

    if actions:
        for action in actions:
            print(action)
    else:
        print("nothing to do; secrets are already in place")

    print()
    print("Ready for: docker compose up --build")
    print("Before serving real traffic set API_ENVIRONMENT=production, which additionally")
    print("requires a real GENERATION_PROVIDER + GENERATION_API_KEY and explicit")
    print("API_CORS_ORIGINS / API_TRUSTED_HOSTS. See DEPLOYMENT.md.")
    return 0


def main() -> int:
    """Parse arguments and run the requested mode.

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n", maxsplit=1)[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify prerequisites without writing anything",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="regenerate secrets even if they already have values",
    )
    args = parser.parse_args()

    if args.check:
        return check()
    return bootstrap(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
