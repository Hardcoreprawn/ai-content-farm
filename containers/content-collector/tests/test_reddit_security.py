"""
Security-focused tests for Reddit client functionality.

These tests ensure that:
1. Credentials are properly validated and sanitized
2. Error messages don't leak sensitive information
3. Secure logging practices are followed
4. Authentication flows handle edge cases safely
"""

import logging
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from reddit_client import RedditClient

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from reddit_client import RedditClient


class TestRedditClientSecurity:
    """Test security aspects of Reddit client."""

    def test_credential_validation_format(self):
        """Test that credential validation rejects invalid formats."""
        client = RedditClient.__new__(RedditClient)  # Create without calling __init__

        # Test valid credentials
        assert (
            client._validate_credentials(
                "validclientid123", "validclientsecret123456789"
            )
            is True
        )

        # Test invalid formats
        assert client._validate_credentials("", "secret") is False
        assert client._validate_credentials("id", "") is False
        assert client._validate_credentials("short", "short") is False
        assert (
            client._validate_credentials("id-with-special-chars!", "secret@#$") is False
        )

        # Test placeholder detection
        assert client._validate_credentials("placeholder123", "secret123") is False
        assert client._validate_credentials("client123", "placeholder_secret") is False
        assert client._validate_credentials("example_id", "real_secret_123") is False

    def test_credential_sanitization(self):
        """Test that credentials are properly sanitized."""
        client = RedditClient.__new__(RedditClient)  # Create without calling __init__

        # Test whitespace removal
        clean_id, clean_secret = client._sanitize_credentials(
            "  client_id  ", "  secret_key  "
        )
        assert clean_id == "client_id"
        assert clean_secret == "secret_key"  # pragma: allowlist secret

        # Test dangerous character removal
        clean_id, clean_secret = client._sanitize_credentials(
            "client;drop;", "secret'union'"
        )
        assert clean_id == "clientdrop"
        assert clean_secret == "secretunion"  # pragma: allowlist secret

        # Test length limiting
        long_id = "a" * 100
        long_secret = "b" * 200
        clean_id, clean_secret = client._sanitize_credentials(long_id, long_secret)
        assert len(clean_id) <= 50
        assert len(clean_secret) <= 100

    @patch("reddit_client.logger")
    def test_secure_logging_initialization_failure(self, mock_logger):
        """Test that initialization failures don't expose credentials in logs."""
        with patch("reddit_client.config") as mock_config:
            mock_config.reddit_client_id = "test_client_id"
            mock_config.reddit_client_secret = (
                "sensitive_secret_123"  # pragma: allowlist secret
            )
            mock_config.reddit_user_agent = "test_agent"
            mock_config.environment = "test"

            # Mock praw.Reddit to raise an exception
            with patch("reddit_client.praw.Reddit") as mock_reddit:
                mock_reddit.side_effect = Exception(
                    "Authentication failed with secret: sensitive_secret_123"
                )

                with pytest.raises(RuntimeError):
                    client = RedditClient()

                # Verify that the sensitive information is not logged
                logged_messages = [
                    call.args[0] for call in mock_logger.error.call_args_list
                ]
                for message in logged_messages:
                    assert "sensitive_secret_123" not in message
                    assert "test_client_id" not in message
                    # Should contain generic error message
                    assert any(
                        "configuration error" in msg.lower() for msg in logged_messages
                    )

    @patch("reddit_client.logger")
    @patch("reddit_client.SecretClient")
    def test_secure_logging_keyvault_failure(self, mock_secret_client, mock_logger):
        """Test that Key Vault failures don't expose credentials in logs."""
        with patch("reddit_client.config") as mock_config:
            mock_config.azure_key_vault_url = "https://test.vault.azure.net/"
            mock_config.environment = "production"

            # Mock Key Vault to return credentials but praw to fail
            mock_kv_instance = Mock()
            mock_secret_client.return_value = mock_kv_instance

            mock_secret = Mock()
            mock_secret.value = "sensitive_keyvault_secret"
            mock_kv_instance.get_secret.return_value = mock_secret

            with patch("reddit_client.praw.Reddit") as mock_reddit:
                mock_reddit.side_effect = Exception(
                    "PRAW error with secret: sensitive_keyvault_secret"
                )

                with pytest.raises(RuntimeError):
                    client = RedditClient()

                # Verify that the sensitive information is not logged
                logged_messages = [
                    call.args[0] for call in mock_logger.error.call_args_list
                ]
                for message in logged_messages:
                    assert "sensitive_keyvault_secret" not in message
                    # Should contain generic error message
                    assert any(
                        "configuration error" in msg.lower() for msg in logged_messages
                    )

    @patch("reddit_client.logger")
    def test_secure_logging_local_development(self, mock_logger):
        """Test that local development initialization doesn't expose credentials."""
        with patch("reddit_client.config") as mock_config:
            # Use credentials that pass validation but will fail Reddit connection
            mock_config.reddit_client_id = "validclientid123"  # Valid format but fake
            mock_config.reddit_client_secret = (
                "validclientsecret123456789"  # pragma: allowlist secret
            )
            mock_config.reddit_user_agent = "test_agent"
            mock_config.environment = "development"

            with patch("reddit_client.praw.Reddit") as mock_reddit:
                mock_reddit.side_effect = Exception(
                    "Connection failed with credentials: validclientsecret123456789"
                )

                # Should not raise exception in local mode, should fall back to None
                client = RedditClient()
                assert client.reddit is None

                # Verify that the sensitive information is not logged
                logged_messages = []
                for call in (
                    mock_logger.warning.call_args_list
                    + mock_logger.error.call_args_list
                    + mock_logger.info.call_args_list
                ):
                    logged_messages.append(call.args[0])

                for message in logged_messages:
                    assert "validclientsecret123456789" not in message
                    assert "validclientid123" not in message

    def test_anonymous_mode_detection(self):
        """Test that anonymous mode is properly detected."""
        client = RedditClient.__new__(RedditClient)  # Create without calling __init__

        # Test with no Reddit client
        client.reddit = None
        assert client.is_anonymous() is False

        # Test with mock authenticated client
        mock_reddit = Mock()
        mock_reddit.user.me.return_value = {"name": "test_user"}
        client.reddit = mock_reddit
        assert client.is_anonymous() is False

        # Test with mock anonymous client (throws exception on user.me())
        mock_reddit_anon = Mock()
        mock_reddit_anon.user.me.side_effect = Exception("Not authenticated")
        client.reddit = mock_reddit_anon
        assert client.is_anonymous() is True

    @patch("reddit_client.config")
    @patch("reddit_client.praw.Reddit")
    def test_anonymous_access_fallback(self, mock_reddit, mock_config):
        """Test that anonymous access works as fallback."""
        mock_config.reddit_client_id = None
        mock_config.reddit_client_secret = None
        mock_config.reddit_user_agent = "test_agent"
        mock_config.environment = "development"

        mock_reddit_instance = Mock()
        mock_reddit.return_value = mock_reddit_instance

        client = RedditClient()

        # Verify anonymous Reddit client was created
        mock_reddit.assert_called_with(
            client_id=None,
            client_secret=None,
            user_agent="test_agent",
            check_for_async=False,
        )
        assert client.reddit == mock_reddit_instance

    def test_credential_validation_edge_cases(self):
        """Test edge cases in credential validation."""
        client = RedditClient.__new__(RedditClient)  # Create without calling __init__

        # Test None values (type: ignore to suppress mypy warnings)
        assert client._validate_credentials(None, "secret") is False  # type: ignore
        assert client._validate_credentials("client", None) is False  # type: ignore
        assert client._validate_credentials(None, None) is False  # type: ignore

        # Test empty strings
        assert client._validate_credentials("", "secret") is False
        assert client._validate_credentials("client", "") is False
        assert client._validate_credentials("", "") is False

        # Test too short credentials
        assert client._validate_credentials("short", "secret123456789012345") is False
        assert client._validate_credentials("validclientid123", "short") is False

        # Test too long credentials
        assert (
            client._validate_credentials(
                "a" * 25, "validclientsecret123456789"  # Too long client_id
            )
            is False
        )
        assert (
            client._validate_credentials(
                "validclientid123", "a" * 55  # Too long client_secret
            )
            is False
        )

    def test_sanitization_preserves_valid_characters(self):
        """Test that sanitization preserves valid characters."""
        client = RedditClient.__new__(RedditClient)  # Create without calling __init__

        # Test that valid characters are preserved
        valid_id = "client_id-123"
        valid_secret = "secret_key-456"  # pragma: allowlist secret

        clean_id, clean_secret = client._sanitize_credentials(valid_id, valid_secret)
        assert clean_id == valid_id
        assert clean_secret == valid_secret


class TestRedditClientSecurityIntegration:
    """Integration tests for Reddit client security."""

    @patch("reddit_client.logger")
    def test_full_initialization_security(self, mock_logger):
        """Test complete initialization flow for security."""
        with patch("reddit_client.config") as mock_config:
            # Use credentials that will fail validation (contain 'placeholder')
            mock_config.reddit_client_id = (
                "placeholderid123"  # Invalid - contains placeholder
            )
            mock_config.reddit_client_secret = (
                "placeholdersecret123456"  # pragma: allowlist secret
            )
            mock_config.reddit_user_agent = "test_agent"
            mock_config.environment = "test"

            with pytest.raises(RuntimeError):
                client = RedditClient()

            # Verify validation caught the placeholder - but only warning about format
            warning_messages = [
                call.args[0] for call in mock_logger.warning.call_args_list
            ]
            # The warning should be about placeholder values being detected
            assert any("placeholder" in msg.lower() for msg in warning_messages)

    def test_user_agent_handling(self):
        """Test that user agent is handled securely."""
        client = RedditClient.__new__(RedditClient)  # Create without calling __init__

        # User agent should not be validated the same way as credentials
        # This ensures we don't accidentally validate user agent as a credential
        with patch.object(client, "_validate_credentials") as mock_validate:
            mock_validate.return_value = True

            with patch("reddit_client.praw.Reddit"):
                client._init_reddit_with_creds(
                    "valid_id_123", "valid_secret_123456", "My User Agent/1.0"
                )

                # Should only be called once with the credentials, not user agent
                mock_validate.assert_called_once_with(
                    "valid_id_123", "valid_secret_123456"
                )


if __name__ == "__main__":
    pytest.main([__file__])
