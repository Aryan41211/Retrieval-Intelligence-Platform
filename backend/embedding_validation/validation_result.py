"""Structured validation results for embedding validation framework."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationStatus(str, Enum):
    """Status of a validation check."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class ValidationSeverity(str, Enum):
    """Severity level of a validation issue."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationCheckResult:
    """Result of a single validation check.

    Each validation result includes:
    - Validation Name: The name of the validation check performed
    - Status: Whether the validation passed, failed, or produced a warning
    - Severity: The severity level of the issue
    - Message: Human-readable description of the check result
    - Recommendation: Suggested corrective action if applicable
    """

    validation_name: str
    status: ValidationStatus
    severity: ValidationSeverity
    message: str
    recommendation: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class ValidationResult:
    """Aggregated result of embedding validation.

    Contains all individual check results and summary metrics.
    """

    is_valid: bool = True
    total_embeddings: int = 0
    valid_embeddings: int = 0
    invalid_embeddings: int = 0
    checks: list[ValidationCheckResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dimensions: set[int] = field(default_factory=set)
    duplicate_count: int = 0
    near_duplicate_count: int = 0
    zero_vector_count: int = 0
    nan_count: int = 0
    inf_count: int = 0
    normalized_count: int = 0

    @property
    def check_results(self) -> list[ValidationCheckResult]:
        """Return all check results."""
        return self.checks

    @property
    def validation_rate(self) -> float:
        """Return the validation pass rate."""
        if self.total_embeddings == 0:
            return 0.0
        return self.valid_embeddings / self.total_embeddings

    @property
    def failed_checks(self) -> list[ValidationCheckResult]:
        """Return all failed checks."""
        return [c for c in self.checks if c.status == ValidationStatus.FAILED]

    @property
    def warning_checks(self) -> list[ValidationCheckResult]:
        """Return all warning and info checks."""
        return [c for c in self.checks if c.status == ValidationStatus.WARNING]

    def add_check(self, check: ValidationCheckResult) -> None:
        """Add a check result and update validity."""
        self.checks.append(check)
        if check.status == ValidationStatus.FAILED:
            self.is_valid = False
            if check.message:
                self.errors.append(check.message)
        elif check.status == ValidationStatus.WARNING:
            if check.message:
                self.warnings.append(check.message)

    def set_validity(self, valid: bool) -> None:
        """Set overall validity flag."""
        self.is_valid = valid
