"""
Security tests to verify that our security fixes prevent information exposure.
"""

import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Add containers to path for imports
sys.path.append(
    os.path.join(os.path.dirname(__file__), "..", "containers", "content-ranker")
)


def test_health_endpoint_security():
    """Test that health endpoint doesn't expose sensitive information in error responses."""
    # Import after adding path
    try:
        from main import app

        client = TestClient(app)

        # Mock health_check to raise an exception with sensitive data
        with patch("main.health_check") as mock_health:
            # Simulate an exception with sensitive information
            mock_health.side_effect = Exception(
                "Database password: super_secret_123 | API key: sk-abcd1234"
            )

            # Call the health endpoint
            response = client.get("/health")

            # Verify the response doesn't expose sensitive data
            assert response.status_code == 503
            response_text = response.text.lower()

            # Check that sensitive information is NOT in the response
            assert "password" not in response_text
            assert "super_secret_123" not in response_text
            assert "api key" not in response_text
            assert "sk-abcd1234" not in response_text
            assert "database" not in response_text

            # Verify we get a generic, safe error message
            response_json = response.json()
            assert "error" in response_json
            assert response_json["error"] == "Service temporarily unavailable"
            assert "service" in response_json
            assert response_json["service"] == "content-ranker"

            print("✅ Security test passed - no sensitive information exposed")

    except ImportError as e:
        print(f"⚠️ Could not import content-ranker main module: {e}")
        print("This is expected if the content-ranker dependencies are not available")
        pytest.skip("Content-ranker module not available for testing")


def test_error_message_structure():
    """Test that error messages follow secure structure."""
    # Import after adding path
    try:
        from main import app

        client = TestClient(app)

        with patch("main.health_check") as mock_health:
            mock_health.side_effect = Exception("Any error message")

            response = client.get("/health")

            # Verify response structure
            assert response.status_code == 503
            response_json = response.json()

            # Check required fields are present
            required_fields = ["error", "message", "service"]
            for field in required_fields:
                assert (
                    field in response_json
                ), f"Required field '{field}' missing from error response"

            # Check error message is generic
            assert response_json["error"] == "Service temporarily unavailable"
            assert "try again later" in response_json["message"]

            print("✅ Error structure test passed - secure format maintained")

    except ImportError:
        pytest.skip("Content-ranker module not available for testing")


if __name__ == "__main__":
    """Run security tests directly."""
    print("🔒 Running security tests...")
    test_health_endpoint_security()
    test_error_message_structure()
    print("🎉 All security tests completed!")
