"""Tests for logging configuration.

Pins the rule that SQL statements and their bind parameters never reach the
application log: at API_LOG_LEVEL=DEBUG the SQLAlchemy and aiosqlite loggers
previously dumped every statement, including user ids and token lookups.
"""

import logging

import pytest

from backend.api.config import APISettings
from backend.api.observability import (
    _SQL_LOGGERS,
    CorrelationFilter,
    JsonFormatter,
    configure_logging,
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)


@pytest.fixture(autouse=True)
def _restore_logging():
    """Restore root logging state after each test."""
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.setLevel(original_level)


class TestSqlLoggerSuppression:
    """H11: statement-level logging must never be enabled."""

    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING"])
    def test_sql_loggers_never_below_warning(self, level: str) -> None:
        configure_logging(APISettings(log_level=level, log_format="json"))
        for name in _SQL_LOGGERS:
            assert logging.getLogger(name).level >= logging.WARNING, name

    def test_debug_does_not_enable_sql_statement_logging(self) -> None:
        configure_logging(APISettings(log_level="DEBUG", log_format="json"))
        engine_logger = logging.getLogger("sqlalchemy.engine.Engine")
        # A SELECT logged at INFO by SQLAlchemy must be filtered out.
        assert not engine_logger.isEnabledFor(logging.INFO)

    def test_application_loggers_still_honour_debug(self) -> None:
        configure_logging(APISettings(log_level="DEBUG", log_format="json"))
        assert logging.getLogger("backend.api.middleware").isEnabledFor(logging.DEBUG)


class TestJsonFormatter:
    """Structured logs must stay parseable and carry the correlation id."""

    def test_renders_single_line_json(self) -> None:
        import json

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        CorrelationFilter().filter(record)
        rendered = JsonFormatter().format(record)
        assert "\n" not in rendered
        payload = json.loads(rendered)
        assert payload["message"] == "hello world"
        assert payload["level"] == "INFO"
        assert "correlation_id" in payload

    def test_includes_extra_fields(self) -> None:
        import json

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="request",
            args=(),
            exc_info=None,
        )
        record.status = 200
        CorrelationFilter().filter(record)
        payload = json.loads(JsonFormatter().format(record))
        assert payload["status"] == 200


class TestCorrelationId:
    """Correlation ids propagate through the context."""

    def test_set_and_get(self) -> None:
        value = new_correlation_id()
        set_correlation_id(value)
        assert get_correlation_id() == value

    def test_ids_are_unique(self) -> None:
        assert new_correlation_id() != new_correlation_id()
