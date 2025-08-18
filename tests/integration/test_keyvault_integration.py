#!/usr/bin/env python3
"""
Test Azure Key Vault Integration

Tests the Key Vault client functionality and credential retrieval.
"""

import sys
import os
import json
from typing import Dict, Any

# Add the current directory to Python path for imports
sys.path.insert(0, '/workspaces/ai-content-farm/containers/content-collector')

try:
    from keyvault_client import (
        get_keyvault_client,
        get_reddit_credentials_with_fallback,
        health_check_keyvault
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root")
    sys.exit(1)


def test_keyvault_client():
    """Test basic Key Vault client functionality."""
    print("🔑 Testing Azure Key Vault Client")
    print("=" * 50)

    client = get_keyvault_client()

    print(f"Key Vault URL: {client.vault_url or 'Not configured'}")
    print(f"Client Available: {client.is_available()}")

    if client.is_available():
        print("✅ Key Vault client is available")

        # Test secret retrieval
        print("\n🔍 Testing Secret Retrieval:")
        test_secret = client.get_secret("reddit-client-id")

        if test_secret:
            print(
                f"✅ Successfully retrieved reddit-client-id: {'*' * len(test_secret[:4])}...")
        else:
            print("⚠️  reddit-client-id not found or not accessible")

    else:
        print("⚠️  Key Vault client not available")
        if not client.vault_url:
            print("   💡 Tip: Set AZURE_KEY_VAULT_URL in your .env file")
        else:
            print(
                "   💡 Tip: Check your Azure authentication (az login or service principal)")


def test_reddit_credentials():
    """Test Reddit credential retrieval with fallback."""
    print("\n📱 Testing Reddit Credentials with Fallback")
    print("=" * 50)

    credentials = get_reddit_credentials_with_fallback()

    print("Credential Status:")
    for key, value in credentials.items():
        if value:
            masked_value = f"{'*' * len(value[:4])}..." if len(
                value) > 4 else "***"
            print(f"  ✅ {key}: {masked_value}")
        else:
            print(f"  ❌ {key}: Not found")

    # Check sources
    print("\nCredential Sources:")
    kv_client = get_keyvault_client()

    if kv_client.is_available():
        print("  🔑 Trying Key Vault...")
        kv_creds = kv_client.get_reddit_credentials()
        for key, value in kv_creds.items():
            if value:
                print(f"     ✅ {key}: Found in Key Vault")
            else:
                print(f"     ❌ {key}: Not in Key Vault")

    print("  🌍 Checking Environment Variables...")
    env_vars = {
        "client_id": "REDDIT_CLIENT_ID",
        "client_secret": "REDDIT_CLIENT_SECRET",
        "user_agent": "REDDIT_USER_AGENT"
    }

    for key, env_var in env_vars.items():
        env_value = os.getenv(env_var)
        if env_value:
            print(f"     ✅ {key}: Found in {env_var}")
        else:
            print(f"     ❌ {key}: Not in {env_var}")


def test_health_check():
    """Test the Key Vault health check."""
    print("\n🏥 Testing Key Vault Health Check")
    print("=" * 50)

    health = health_check_keyvault()

    print(f"Status: {health['status']}")
    print(f"Message: {health.get('message', 'N/A')}")
    print(f"Key Vault Configured: {health['key_vault_configured']}")
    print(f"Client Available: {health['client_available']}")

    if 'test_secret_retrieval' in health:
        print(
            f"Secret Retrieval Test: {'✅ Passed' if health['test_secret_retrieval'] else '❌ Failed'}")


def test_service_health():
    """Test the content-collector service health endpoint."""
    print("\n🌐 Testing Content Collector Service Health")
    print("=" * 50)

    try:
        import requests

        response = requests.get("http://localhost:8001/health", timeout=5)

        if response.status_code == 200:
            health_data = response.json()

            print(f"Service Status: {health_data['status']}")

            kv_info = health_data.get(
                'environment_info', {}).get('key_vault', {})
            print(f"Key Vault Status: {kv_info.get('status', 'unknown')}")
            print(f"Key Vault Message: {kv_info.get('message', 'N/A')}")

            config_info = health_data.get(
                'environment_info', {}).get('config_validation', {})
            print(f"Config Valid: {config_info.get('valid', False)}")

            if config_info.get('issues'):
                print("Config Issues:")
                for issue in config_info['issues']:
                    print(f"  ❌ {issue}")
            else:
                print("✅ No config issues")

            print("\n📊 Full Key Vault Info:")
            print(json.dumps(kv_info, indent=2))

        else:
            print(f"❌ Service health check failed: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.RequestException as e:
        print(f"❌ Cannot connect to service: {e}")
        print("💡 Make sure the content-collector is running: docker-compose up -d")
    except ImportError:
        print("❌ requests library not available")
        print("💡 Install with: pip install requests")


def main():
    """Run all tests."""
    print("🧪 Azure Key Vault Integration Test Suite")
    print("=" * 60)

    # Test 1: Key Vault client
    test_keyvault_client()

    # Test 2: Reddit credentials
    test_reddit_credentials()

    # Test 3: Health check
    test_health_check()

    # Test 4: Service integration
    test_service_health()

    print("\n" + "=" * 60)
    print("🎯 Test Summary")
    print("=" * 60)
    print("1. ✅ Key Vault client initialization tested")
    print("2. ✅ Reddit credential fallback tested")
    print("3. ✅ Health check functionality tested")
    print("4. ✅ Service integration tested")
    print()
    print("💡 Next Steps:")
    print("   - If Key Vault is not configured, run: ./setup-local-dev.sh")
    print("   - If credentials are missing, add them to Key Vault or .env")
    print("   - Test the full pipeline with: python test_mock_pipeline.py")


if __name__ == "__main__":
    main()
