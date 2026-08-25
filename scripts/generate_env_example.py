#!/usr/bin/env python
"""Generate .env.example from the pydantic settings classes.

The previous .env.example was maintained by hand and had drifted badly: it
documented ~60 variables no code reads (PINECONE_*, QDRANT_*, CHUNKING_*, ...),
used names the code does not accept (VECTOR_STORE_DIR instead of
VECTOR_STORE_STORAGE_DIR), and omitted ENTERPRISE_JWT_SECRET_KEY, the one
variable without which the application will not import.

Deriving the file from the settings classes keeps documentation and code in
lockstep. Run after changing any settings model::

    python scripts/generate_env_example.py

Verify in CI with ``--check``, which fails when the committed file is stale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, get_args, get_origin

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pydantic_settings import BaseSettings  # noqa: E402

from backend.api.config import APISettings  # noqa: E402
from backend.configs.settings import (  # noqa: E402
    BM25Settings,
    CrossEncoderRerankSettings,
    DynamicTopKSettings,
    EmbeddingSettings,
    EmbeddingValidationSettings,
    GenerationSettings,
    IngestionSettings,
    IntelligentRetrievalSettings,
    PreprocessingSettings,
    QueryExpansionSettings,
    RetrievalSettings,
    RRFSettings,
    VectorStoreSettings,
)
from backend.enterprise.config import EnterpriseSettings  # noqa: E402

HEADER = """# ==============================================================================
# Retrieval Intelligence Platform - environment configuration
#
# GENERATED FILE - do not edit by hand.
#   Regenerate with: python scripts/generate_env_example.py
#
# Copy to .env and fill in the values marked REQUIRED.
#   cp .env.example .env
#
# Commented-out keys are optional: leaving them commented means "unset", which
# is what the code expects. Assigning them an empty value is NOT the same thing
# and will fail validation for numeric settings.
# ==============================================================================
"""

# Values that must never be given a working default in the example file.
SECRET_FIELDS = {
    "ENTERPRISE_JWT_SECRET_KEY",
    "ENTERPRISE_OAUTH_GOOGLE_CLIENT_SECRET",
    "GENERATION_API_KEY",
    "API_METRICS_TOKEN",
}

REQUIRED_FIELDS = {"ENTERPRISE_JWT_SECRET_KEY"}

SECTIONS: list[tuple[str, type[BaseSettings], str]] = [
    (
        "API / server",
        APISettings,
        "Server binding, CORS, rate limiting, logging, security headers.",
    ),
    (
        "Enterprise / authentication",
        EnterpriseSettings,
        "JWT signing, token lifetimes, OAuth, registration.",
    ),
    (
        "Generation (LLM)",
        GenerationSettings,
        "Provider selection and credentials for answer generation.",
    ),
    ("Embeddings", EmbeddingSettings, "Embedding model used for indexing and query encoding."),
    ("Vector store", VectorStoreSettings, "Index persistence and defaults."),
    ("Retrieval", RetrievalSettings, "Top-k, thresholds and filters for dense retrieval."),
    ("Hybrid retrieval", IntelligentRetrievalSettings, "Enable the BM25 + RRF + rerank pipeline."),
    ("Hybrid: BM25", BM25Settings, "Sparse retrieval parameters."),
    ("Hybrid: RRF fusion", RRFSettings, "Reciprocal rank fusion parameters."),
    ("Hybrid: cross-encoder rerank", CrossEncoderRerankSettings, "Optional reranking stage."),
    ("Hybrid: query expansion", QueryExpansionSettings, "Lightweight query expansion."),
    ("Hybrid: dynamic top-k", DynamicTopKSettings, "Adaptive result-count selection."),
    ("Ingestion", IngestionSettings, "Document loading limits and supported formats."),
    ("Preprocessing", PreprocessingSettings, "Text normalisation."),
    ("Embedding validation", EmbeddingValidationSettings, "Optional embedding quality checks."),
]

EXTRA_SECTION = """
# ------------------------------------------------------------------------------
# Database
# ------------------------------------------------------------------------------
# SQLAlchemy async URL. A synchronous driver is upgraded automatically, but
# prefer the explicit async form.
#   sqlite+aiosqlite:///./rip.db
#   postgresql+asyncpg://user:password@host:5432/dbname
DATABASE_URL=sqlite+aiosqlite:///./rip.db
"""


def _render_default(value: Any) -> str:
    """Render a field default as an environment-variable value.

    ``None`` is never rendered here - callers comment the assignment out
    instead. See :func:`_render_assignment`.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list | dict):
        import json

        return json.dumps(value)
    return str(value)


def _type_hint(annotation: Any) -> str:
    """Describe a field's accepted values for the comment line."""
    origin = get_origin(annotation)
    if origin is not None:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _type_hint(args[0])
        literals = [repr(a) for a in args if not isinstance(a, type)]
        if literals:
            return " | ".join(literals)
    return getattr(annotation, "__name__", str(annotation))


def _render_assignment(env_name: str, default: Any) -> str:
    """Render one ``KEY=value`` line, commenting out optional-and-unset fields.

    pydantic-settings does not treat ``KEY=`` as "absent" - it reads the empty
    string and feeds it to the field validator. For a ``str | None`` field that
    is merely imprecise, but for ``int | None`` or ``float | None`` it is fatal:
    copying .env.example to .env made the application fail at import with
    "unable to parse string as an integer". Emitting the key commented out
    keeps it documented and discoverable while leaving it genuinely unset.

    Args:
        env_name: The environment variable name.
        default: The field's resolved default value.

    Returns:
        The rendered line.
    """
    if default is None:
        return f"# {env_name}="
    return f"{env_name}={_render_default(default)}"


def render() -> str:
    """Build the full .env.example content."""
    lines: list[str] = [HEADER]

    for title, model, blurb in SECTIONS:
        prefix = model.model_config.get("env_prefix", "")
        lines.append("# " + "-" * 78)
        lines.append(f"# {title}")
        lines.append(f"# {blurb}")
        lines.append("# " + "-" * 78)

        for name, field in model.model_fields.items():
            # Nested settings models carry their own prefix and get their own
            # section; emitting them here would produce unreadable names.
            annotation = field.annotation
            if isinstance(annotation, type) and issubclass(annotation, BaseSettings):
                continue

            env_name = f"{prefix}{name}".upper()
            description = field.description or ""
            if description:
                lines.append(f"# {description}")
            hint = _type_hint(field.annotation)
            if hint and hint not in {"str", "NoneType"}:
                lines.append(f"# Type: {hint}")

            if env_name in SECRET_FIELDS:
                marker = "REQUIRED - " if env_name in REQUIRED_FIELDS else "SECRET - "
                lines.append(f"# {marker}never commit a real value.")
                lines.append(f"{env_name}=")
            else:
                default = field.default
                factory = getattr(field, "default_factory", None)
                if factory is not None:
                    try:
                        default = factory()
                    except TypeError:  # pragma: no cover - defensive
                        default = None
                lines.append(_render_assignment(env_name, default))
            lines.append("")
        lines.append("")

    lines.append(EXTRA_SECTION.strip())
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed .env.example is out of date.",
    )
    args = parser.parse_args()

    target = REPO_ROOT / ".env.example"
    content = render()

    if args.check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != content:
            print(
                ".env.example is out of date. Run: python scripts/generate_env_example.py",
                file=sys.stderr,
            )
            return 1
        print(".env.example is up to date.")
        return 0

    target.write_text(content, encoding="utf-8")
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
