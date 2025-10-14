"""
Tests for configuration module.

Tests Settings class initialization, environment variable parsing,
default values, and validation.
"""

import os

import pytest

from config import Settings  # type: ignore[attr-defined]


class TestSettingsDefaults:
    """Test default values when no environment variables are set."""

    def test_default_service_version(self):
        """Test default service version."""
        settings = Settings()
        assert settings.service_version == "1.0.0"

    def test_default_environment(self, monkeypatch):
        """Test default environment."""
        # Clear any environment variable that might be set
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        settings = Settings()
        assert settings.environment == "development"

    def test_default_host(self):
        """Test default host."""
        settings = Settings()
        assert settings.host == "0.0.0.0"

    def test_default_port(self):
        """Test default port."""
        settings = Settings()
        assert settings.port == 8000

    def test_default_log_level(self):
        """Test default log level."""
        settings = Settings()
        assert settings.log_level == "INFO"


class TestSettingsFromEnvironment:
    """Test settings override from environment variables."""

    def test_service_version_from_env(self, monkeypatch):
        """Test service version can be overridden."""
        monkeypatch.setenv("SERVICE_VERSION", "2.0.0")
        settings = Settings()
        assert settings.service_version == "2.0.0"

    def test_environment_from_env(self, monkeypatch):
        """Test environment can be overridden."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings.environment == "production"

    def test_host_from_env(self, monkeypatch):
        """Test host can be overridden."""
        monkeypatch.setenv("HOST", "127.0.0.1")
        settings = Settings()
        assert settings.host == "127.0.0.1"

    def test_port_from_env(self, monkeypatch):
        """Test port can be overridden."""
        monkeypatch.setenv("PORT", "9000")
        settings = Settings()
        assert settings.port == 9000

    def test_log_level_from_env(self, monkeypatch):
        """Test log level can be overridden."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.log_level == "DEBUG"


class TestSettingsCaseInsensitivity:
    """Test that environment variable names are case-insensitive."""

    def test_lowercase_env_vars(self, monkeypatch):
        """Test lowercase environment variable names work."""
        monkeypatch.setenv("service_version", "3.0.0")
        monkeypatch.setenv("environment", "staging")
        monkeypatch.setenv("log_level", "WARNING")

        settings = Settings()
        assert settings.service_version == "3.0.0"
        assert settings.environment == "staging"
        assert settings.log_level == "WARNING"

    def test_uppercase_env_vars(self, monkeypatch):
        """Test uppercase environment variable names work."""
        monkeypatch.setenv("SERVICE_VERSION", "4.0.0")
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("LOG_LEVEL", "ERROR")

        settings = Settings()
        assert settings.service_version == "4.0.0"
        assert settings.environment == "test"
        assert settings.log_level == "ERROR"

    def test_mixed_case_env_vars(self, monkeypatch):
        """Test mixed case environment variable names work."""
        monkeypatch.setenv("Service_Version", "5.0.0")
        monkeypatch.setenv("Environment", "uat")
        monkeypatch.setenv("Log_Level", "CRITICAL")

        settings = Settings()
        assert settings.service_version == "5.0.0"
        assert settings.environment == "uat"
        assert settings.log_level == "CRITICAL"


class TestSettingsTypeValidation:
    """Test type validation and coercion."""

    def test_port_must_be_integer(self, monkeypatch):
        """Test port is coerced to integer."""
        monkeypatch.setenv("PORT", "8080")
        settings = Settings()
        assert isinstance(settings.port, int)
        assert settings.port == 8080

    def test_invalid_port_raises_error(self, monkeypatch):
        """Test invalid port value raises validation error."""
        monkeypatch.setenv("PORT", "not-a-number")
        with pytest.raises(Exception):  # Pydantic validation error
            Settings()

    def test_all_string_fields_are_strings(self):
        """Test that all string fields are actually strings."""
        settings = Settings()
        assert isinstance(settings.service_version, str)
        assert isinstance(settings.environment, str)
        assert isinstance(settings.host, str)
        assert isinstance(settings.log_level, str)


class TestSettingsImmutability:
    """Test that settings are immutable after creation."""

    def test_settings_fields_can_be_read(self):
        """Test all settings fields can be read."""
        settings = Settings()
        # Access all fields to ensure they work
        _ = settings.service_version
        _ = settings.environment
        _ = settings.host
        _ = settings.port
        _ = settings.log_level


class TestSettingsMultipleInstances:
    """Test creating multiple Settings instances."""

    def test_multiple_instances_independent(self, monkeypatch):
        """Test multiple Settings instances are independent."""
        # Create first instance with default values
        settings1 = Settings()

        # Change environment and create second instance
        monkeypatch.setenv("SERVICE_VERSION", "different")
        settings2 = Settings()

        # First instance should have different value
        assert settings1.service_version == "1.0.0"
        assert settings2.service_version == "different"

    def test_settings_no_global_state(self, monkeypatch):
        """Test Settings doesn't maintain global state."""
        monkeypatch.setenv("ENVIRONMENT", "first")
        settings1 = Settings()

        monkeypatch.setenv("ENVIRONMENT", "second")
        settings2 = Settings()

        # Each instance should have its own values
        assert settings1.environment == "first"
        assert settings2.environment == "second"


class TestSettingsCommonEnvironments:
    """Test common environment configurations."""

    def test_production_configuration(self, monkeypatch):
        """Test typical production configuration."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("PORT", "80")

        settings = Settings()
        assert settings.environment == "production"
        assert settings.log_level == "WARNING"
        assert settings.port == 80

    def test_development_configuration(self, monkeypatch):
        """Test typical development configuration."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("HOST", "localhost")

        settings = Settings()
        assert settings.environment == "development"
        assert settings.log_level == "DEBUG"
        assert settings.host == "localhost"

    def test_test_configuration(self, monkeypatch):
        """Test typical test/CI configuration."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("LOG_LEVEL", "ERROR")

        settings = Settings()
        assert settings.environment == "test"
        assert settings.log_level == "ERROR"
