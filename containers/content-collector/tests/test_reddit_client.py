"""
Reddit Client Tests for Content Collector

Tests Reddit client functionality, security, and credential handling.
"""

from unittest.mock import Mock, patch

import pytest
from reddit_client import RedditClient


@pytest.mark.unit
class TestRedditClientSecurity:
    """Security tests for Reddit client core functionality."""

    @patch("reddit_client.logger")
    def test_reddit_client_error_logging_security(self, mock_logger):
        """Test that Reddit client errors don't expose sensitive information."""
        # Mock config with sensitive credentials
        with patch("reddit_client.config") as mock_config:
            mock_config.reddit_client_id = "sensitive_client_id"
            mock_config.reddit_client_secret = (
                "super_secret_password_123"  # pragma: allowlist secret
            )
            mock_config.reddit_user_agent = "test_agent"
            mock_config.environment = "test"

            # Mock praw.Reddit to raise an exception with sensitive info
            with patch("reddit_client.praw.Reddit") as mock_reddit:
                mock_reddit.side_effect = Exception(
                    "Authentication failed: invalid client_secret 'super_secret_password_123'"
                )

                # Should raise RuntimeError, not the original exception
                with pytest.raises(RuntimeError):
                    RedditClient()

                # Verify sensitive information is not in logs
                logged_messages = []
                for call in mock_logger.error.call_args_list:
                    logged_messages.append(str(call.args))

                log_content = " ".join(logged_messages)
                assert "super_secret_password_123" not in log_content
                assert "sensitive_client_id" not in log_content

                # Should contain generic error message
                assert any(
                    "configuration error" in str(args).lower()
                    for args in logged_messages
                )

    def test_reddit_credential_validation(self):
        """Test Reddit credential validation prevents malicious inputs."""
        client = RedditClient.__new__(RedditClient)  # Create without __init__

        # Test injection attempts
        malicious_inputs = [
            ("client_id'; DROP TABLE users; --", "normal_secret_123456789"),
            ("normal_client_id", "secret'; DELETE FROM secrets; --"),
            ("client<script>alert('xss')</script>", "normal_secret_123456789"),
            ("../../../etc/passwd", "normal_secret_123456789"),
            ("client\x00null_byte", "normal_secret_123456789"),
        ]

        for client_id, client_secret in malicious_inputs:
            sanitized_id, sanitized_secret = client._sanitize_credentials(
                client_id, client_secret
            )

            # Verify dangerous characters are removed
            assert "'" not in sanitized_id
            assert "'" not in sanitized_secret
            assert "<" not in sanitized_id
            assert ">" not in sanitized_id
            assert ";" not in sanitized_id
            assert "\x00" not in sanitized_id

    @patch("reddit_client.praw.Reddit")
    @patch("reddit_client.config")
    def test_reddit_anonymous_access_security(self, mock_config, mock_reddit):
        """Test that anonymous access doesn't expose sensitive operations."""
        mock_config.reddit_client_id = None
        mock_config.reddit_client_secret = None
        mock_config.reddit_user_agent = "test_agent"
        mock_config.environment = "development"

        mock_reddit_instance = Mock()
        mock_reddit.return_value = mock_reddit_instance

        client = RedditClient()

        # Verify anonymous client was created (no credentials)
        mock_reddit.assert_called_with(
            client_id=None,
            client_secret=None,
            user_agent="test_agent",
            check_for_async=False,
        )

        # Verify client is available but anonymous
        assert client.is_available() is True

    @patch("reddit_client.logger")
    @patch("reddit_client.SecretClient")
    @patch("reddit_client.config")
    def test_reddit_keyvault_error_security(
        self, mock_config, mock_secret_client, mock_logger
    ):
        """Test that Key Vault errors don't expose credentials."""
        mock_config.azure_key_vault_url = "https://test.vault.azure.net/"
        mock_config.reddit_client_id = None
        mock_config.reddit_client_secret = None
        mock_config.environment = "production"

        # Mock Key Vault to return sensitive credentials
        mock_kv = Mock()
        mock_secret = Mock()
        mock_secret.value = "keyvault_secret_password_456"
        mock_kv.get_secret.return_value = mock_secret
        mock_secret_client.return_value = mock_kv

        # Mock praw to fail with sensitive error
        with patch("reddit_client.praw.Reddit") as mock_reddit:
            mock_reddit.side_effect = Exception(
                "API authentication failed with secret: keyvault_secret_password_456"
            )

            with pytest.raises(RuntimeError):
                RedditClient()

            # Verify sensitive information is not logged
            logged_messages = []
            for call in mock_logger.error.call_args_list:
                logged_messages.append(str(call.args))

            log_content = " ".join(logged_messages)
            assert "keyvault_secret_password_456" not in log_content


@pytest.mark.unit
class TestRedditClientFunctionality:
    """Test Reddit client basic functionality."""

    @patch("reddit_client.praw.Reddit")
    @patch("reddit_client.config")
    def test_reddit_client_initialization(self, mock_config, mock_reddit):
        """Test Reddit client initializes properly with valid config."""
        mock_config.reddit_client_id = "valid_client_id"
        mock_config.reddit_client_secret = (
            "valid_secret_123456789"  # pragma: allowlist secret
        )
        mock_config.reddit_user_agent = "test_agent"
        mock_config.environment = "test"

        mock_reddit_instance = Mock()
        mock_reddit.return_value = mock_reddit_instance

        client = RedditClient()

        assert client.is_available() is True
        mock_reddit.assert_called_once()

    @patch("reddit_client.praw.Reddit")
    @patch("reddit_client.config")
    def test_reddit_client_is_anonymous(self, mock_config, mock_reddit):
        """Test anonymous mode detection."""
        mock_config.reddit_client_id = None
        mock_config.reddit_client_secret = None
        mock_config.reddit_user_agent = "test_agent"
        mock_config.environment = "development"

        mock_reddit_instance = Mock()
        mock_reddit_instance.user.me.side_effect = Exception("Anonymous")
        mock_reddit.return_value = mock_reddit_instance

        client = RedditClient()

        assert client.is_anonymous() is True

    @patch("reddit_client.praw.Reddit")
    @patch("reddit_client.config")
    def test_reddit_client_authenticated_mode(self, mock_config, mock_reddit):
        """Test authenticated mode detection."""
        mock_config.reddit_client_id = "valid_client_id"
        mock_config.reddit_client_secret = (
            "valid_secret_123456789"  # pragma: allowlist secret
        )
        mock_config.reddit_user_agent = "test_agent"
        mock_config.environment = "test"

        mock_reddit_instance = Mock()
        mock_reddit_instance.user.me.return_value = Mock(name="test_user")
        mock_reddit.return_value = mock_reddit_instance

        client = RedditClient()

        assert client.is_anonymous() is False
