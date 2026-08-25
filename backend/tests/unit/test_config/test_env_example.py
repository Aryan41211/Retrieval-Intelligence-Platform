"""Guards on the generated ``.env.example``.

``cp .env.example .env`` is the documented first step in both the README and
DEPLOYMENT.md, so the file has to describe a configuration the application can
actually load. It previously did not: the generator rendered every ``None``
default as ``KEY=``, and pydantic-settings reads that as the empty string rather
than as "absent". For ``EMBEDDING_VALIDATION_EXPECTED_DIMENSION: int | None``
that meant a fresh checkout died at import with::

    ValidationError: expected_dimension
      Input should be a valid integer, unable to parse string as an integer

These tests pin the fix: optional settings are emitted commented out, and the
whole file round-trips through the settings models cleanly.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import textwrap

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# env_prefix values across the settings models, plus the unprefixed DATABASE_URL.
SETTINGS_ENV_PREFIXES = (
    "API_",
    "ENTERPRISE_",
    "GENERATION_",
    "EMBEDDING_",
    "VECTOR_STORE_",
    "RETRIEVAL_",
    "INTELLIGENT_RETRIEVAL_",
    "BM25_",
    "RRF_",
    "CROSS_ENCODER_",
    "QUERY_EXPANSION_",
    "DYNAMIC_TOPK_",
    "INGESTION_",
    "PREPROCESSING_",
    "DATABASE_",
    "DB_",
)


def _assignments(text: str) -> dict[str, str]:
    """Return the active (uncommented) ``KEY=value`` pairs in a dotenv file.

    Args:
        text: Contents of a dotenv-style file.

    Returns:
        Mapping of variable name to assigned value.
    """
    pairs: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", line)
        if match is not None:
            pairs[match.group(1)] = match.group(2).strip()
    return pairs


@pytest.fixture(scope="module")
def env_example_text() -> str:
    """Contents of the committed ``.env.example``."""
    assert ENV_EXAMPLE.exists(), f"{ENV_EXAMPLE} is missing"
    return ENV_EXAMPLE.read_text(encoding="utf-8")


def test_env_example_has_no_empty_assignments_except_secrets(env_example_text: str) -> None:
    """Only the secrets a user must fill in may be assigned an empty value.

    Every other optional setting has to be commented out, because ``KEY=`` is
    an empty string to pydantic-settings, not an absent value.
    """
    fill_in_yourself = {
        "ENTERPRISE_JWT_SECRET_KEY",
        "ENTERPRISE_OAUTH_GOOGLE_CLIENT_SECRET",
        "GENERATION_API_KEY",
        "API_METRICS_TOKEN",
    }

    empty = {key for key, value in _assignments(env_example_text).items() if value == ""}
    unexpected = empty - fill_in_yourself

    assert not unexpected, (
        "these keys are assigned an empty value; optional settings must be "
        f"commented out instead: {sorted(unexpected)}"
    )


def test_optional_numeric_settings_are_commented_out(env_example_text: str) -> None:
    """The two settings that made a fresh checkout unbootable stay commented."""
    for key in ("EMBEDDING_VALIDATION_EXPECTED_DIMENSION", "RETRIEVAL_SIMILARITY_THRESHOLD"):
        assert f"# {key}=" in env_example_text, f"{key} should be documented but commented out"
        assert not re.search(
            rf"^{key}=", env_example_text, flags=re.MULTILINE
        ), f"{key} must not be assigned a value; it is optional and numeric"


def test_env_example_loads_into_the_settings_models(tmp_path: pathlib.Path) -> None:
    """A `.env` copied verbatim from `.env.example` boots the application.

    Runs in a subprocess with ``tmp_path`` as the working directory: the
    settings models read ``.env`` relative to the process CWD, and the modules
    cache their settings at import time.
    """
    env_file = tmp_path / ".env"
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    # The one value a user is required to supply.
    text = re.sub(
        r"^ENTERPRISE_JWT_SECRET_KEY=.*$",
        "ENTERPRISE_JWT_SECRET_KEY=" + "9f2c41ab7d05e6389c1a4be27f0d8635a91c47e0bd23c8f7a",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    env_file.write_text(text, encoding="utf-8")

    program = textwrap.dedent(
        """
        from backend.api.config import get_settings as api_settings
        from backend.configs.settings import get_settings as app_settings
        import backend.enterprise.config  # noqa: F401

        settings = api_settings()
        settings.validate_for_environment()
        app_settings().generation.validate_for_environment(settings.environment)
        print("ok")
        """
    )

    # Inherit the real environment - a stripped one breaks interpreter startup
    # on Windows - but drop every variable the settings models read, so the
    # subprocess is exercising the .env file and not the developer's shell.
    child_env = {
        key: value for key, value in os.environ.items() if not key.startswith(SETTINGS_ENV_PREFIXES)
    }
    child_env["PYTHONPATH"] = str(REPO_ROOT)

    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=child_env,
        check=False,
    )

    assert result.returncode == 0, (
        "a .env copied from .env.example does not load:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_env_example_is_in_sync_with_the_settings_classes() -> None:
    """``.env.example`` matches what the generator produces right now."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "generate_env_example.py"), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "`.env.example` is stale; run python scripts/generate_env_example.py\n"
        f"{result.stdout}{result.stderr}"
    )
