"""Test configuration for integration tests."""
import os

# Configure required settings BEFORE any backend module is imported
os.environ.setdefault("ENTERPRISE_ENVIRONMENT", "development")
os.environ.setdefault("ENTERPRISE_JWT_SECRET_KEY", "test-secret-key-not-for-prod-use-1234567890")
os.environ.setdefault("ENTERPRISE_REGISTRATION_ENABLED", "true")
os.environ.setdefault("ENTERPRISE_EMAIL_VERIFICATION_REQUIRED", "false")
os.environ.setdefault("API_RATE_LIMIT_ENABLED", "false")