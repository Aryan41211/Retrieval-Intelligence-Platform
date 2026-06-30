"""Tests for embedding validation configuration."""

from backend.configs.settings import EmbeddingValidationSettings, Settings, get_settings


class TestEmbeddingValidationSettings:
    """Tests for EmbeddingValidationSettings."""

    def test_default_settings(self):
        settings = EmbeddingValidationSettings()
        assert settings.expected_dimension is None
        assert settings.duplicate_tolerance == 0.0
        assert settings.validation_enabled is True
        assert settings.strict_mode is False
        assert settings.warning_mode is False

    def test_custom_expected_dimension(self):
        settings = EmbeddingValidationSettings(expected_dimension=1536)
        assert settings.expected_dimension == 1536

    def test_custom_duplicate_tolerance(self):
        settings = EmbeddingValidationSettings(duplicate_tolerance=0.05)
        assert settings.duplicate_tolerance == 0.05

    def test_strict_mode_enabled(self):
        settings = EmbeddingValidationSettings(strict_mode=True)
        assert settings.strict_mode is True

    def test_warning_mode_enabled(self):
        settings = EmbeddingValidationSettings(warning_mode=True)
        assert settings.warning_mode is True

    def test_validation_disabled(self):
        settings = EmbeddingValidationSettings(validation_enabled=False)
        assert settings.validation_enabled is False

    def test_env_prefix(self):
        settings = EmbeddingValidationSettings()
        assert settings.model_config.get("env_prefix") == "EMBEDDING_VALIDATION_"


class TestSettingsIntegration:
    """Tests for Settings integration."""

    def test_settings_includes_validation_settings(self):
        settings = Settings()
        assert hasattr(settings, "embedding_validation")
        assert isinstance(settings.embedding_validation, EmbeddingValidationSettings)

    def test_get_settings_cached(self):
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
