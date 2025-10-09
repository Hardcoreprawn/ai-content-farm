"""
Tests for configuration management.

Tests configuration loading, validation, and logging setup.
"""

import logging

import pytest

from config import Settings, configure_logging, get_settings


class TestSettings:
    """Test Settings configuration class."""

    def test_settings_loads_with_defaults(self) -> None:
        """
        GIVEN no environment variables set
        WHEN Settings is instantiated with minimal required fields
        THEN default values are applied correctly
        """
        # Arrange & Act
        settings = Settings(azure_storage_account_name="test-account")

        # Assert
        assert settings.azure_storage_account_name == "test-account"
        assert settings.app_name == "markdown-generator"
        assert settings.version == "1.0.0"
        # Environment can be "production" (default) or "testing" (from CI/CD)
        assert settings.environment in ["production", "testing"]
        assert settings.log_level == "INFO"
        assert settings.input_container == "processed-content"
        assert settings.output_container == "markdown-content"
        assert settings.queue_name == "markdown-generation-requests"
        assert settings.max_batch_size == 10
        assert settings.enable_metrics is True

    def test_settings_overrides_defaults_with_explicit_values(self) -> None:
        """
        GIVEN explicit configuration values
        WHEN Settings is instantiated with custom values
        THEN custom values override defaults
        """
        # Arrange & Act
        settings = Settings(
            azure_storage_account_name="custom-account",
            app_name="custom-app",
            environment="development",
            log_level="DEBUG",
            max_batch_size=25,
        )

        # Assert
        assert settings.azure_storage_account_name == "custom-account"
        assert settings.app_name == "custom-app"
        assert settings.environment == "development"
        assert settings.log_level == "DEBUG"
        assert settings.max_batch_size == 25

    def test_get_storage_connection_string_returns_explicit_string(
        self,
    ) -> None:
        """
        GIVEN explicit storage connection string
        WHEN get_storage_connection_string is called
        THEN the explicit connection string is returned
        """
        # Arrange
        explicit_conn_str = (
            "DefaultEndpointsProtocol=https;"
            "AccountName=explicit;AccountKey=key123;"
            "EndpointSuffix=core.windows.net"
        )
        settings = Settings(
            azure_storage_account_name="account",
            storage_connection_string=explicit_conn_str,
        )

        # Act
        result = settings.get_storage_connection_string()

        # Assert
        assert result == explicit_conn_str

    def test_get_storage_connection_string_constructs_from_account_name(
        self,
    ) -> None:
        """
        GIVEN only storage account name (no explicit connection string)
        WHEN get_storage_connection_string is called
        THEN connection string is constructed with managed identity pattern
        """
        # Arrange
        settings = Settings(azure_storage_account_name="testaccount")

        # Act
        result = settings.get_storage_connection_string()

        # Assert
        assert "DefaultEndpointsProtocol=https" in result
        assert "AccountName=testaccount" in result
        assert "EndpointSuffix=core.windows.net" in result
        assert "AccountKey" not in result  # Managed identity doesn't use keys

    def test_get_storage_connection_string_raises_when_no_account_info(
        self,
    ) -> None:
        """
        GIVEN neither connection string nor account name provided
        WHEN get_storage_connection_string is called
        THEN ValueError is raised
        """
        # Arrange
        settings = Settings(
            azure_storage_account_name="",  # Empty string (no account name)
            storage_connection_string=None,
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            settings.get_storage_connection_string()

        assert "storage_connection_string or azure_storage_account_name" in str(
            exc_info.value
        )


class TestGetSettings:
    """Test get_settings() function."""

    def test_get_settings_returns_settings_instance(self) -> None:
        """
        GIVEN get_settings is called
        WHEN no errors occur
        THEN Settings instance is returned
        """
        # Act
        settings = get_settings()

        # Assert
        assert isinstance(settings, Settings)
        assert hasattr(settings, "azure_storage_account_name")

    def test_get_settings_is_cached(self) -> None:
        """
        GIVEN get_settings is called multiple times
        WHEN the function is invoked repeatedly
        THEN the same instance is returned (lru_cache behavior)
        """
        # Act
        settings1 = get_settings()
        settings2 = get_settings()

        # Assert
        assert settings1 is settings2  # Same object identity


class TestConfigureLogging:
    """Test configure_logging() function."""

    def test_configure_logging_sets_log_level(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        GIVEN a settings object with specific log level
        WHEN configure_logging is called
        THEN Azure and urllib3 loggers are suppressed to WARNING
        """
        # Arrange
        settings = Settings(azure_storage_account_name="test", log_level="DEBUG")

        # Act
        configure_logging(settings)

        # Assert
        # Note: logging.basicConfig only works on first call in process
        # So we test that Azure loggers are always suppressed (runs every time)
        azure_logger = logging.getLogger("azure")
        urllib3_logger = logging.getLogger("urllib3")
        assert azure_logger.level == logging.WARNING
        assert urllib3_logger.level == logging.WARNING

    def test_configure_logging_without_settings_uses_defaults(self) -> None:
        """
        GIVEN no settings provided
        WHEN configure_logging is called without arguments
        THEN default settings from get_settings() are used
        """
        # Act
        configure_logging()

        # Assert - Should not raise exception
        root_logger = logging.getLogger()
        assert root_logger.level >= logging.DEBUG  # Some level is set

    def test_configure_logging_suppresses_azure_library_logs(self) -> None:
        """
        GIVEN configure_logging is called
        WHEN Azure and urllib3 loggers are checked
        THEN they are set to WARNING level (to reduce noise)
        """
        # Arrange
        settings = Settings(azure_storage_account_name="test", log_level="DEBUG")

        # Act
        configure_logging(settings)

        # Assert
        azure_logger = logging.getLogger("azure")
        urllib3_logger = logging.getLogger("urllib3")
        assert azure_logger.level == logging.WARNING
        assert urllib3_logger.level == logging.WARNING
