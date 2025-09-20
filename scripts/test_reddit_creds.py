#!/usr/bin/env python3
"""
Test Reddit API credentials locally
"""
import os
import subprocess
import sys

import praw


def get_secret_from_keyvault(vault_name, secret_name):
    """Get secret from Azure Key Vault"""
    try:
        result = subprocess.run(
            [
                "az",
                "keyvault",
                "secret",
                "show",
                "--vault-name",
                vault_name,
                "--name",
                secret_name,
                "--query",
                "value",
                "--output",
                "tsv",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Failed to get {secret_name}: {e}")
        return None


def test_reddit_credentials():
    """Test Reddit API authentication"""

    # Get credentials from Key Vault
    print("🔑 Fetching Reddit credentials from Azure Key Vault...")

    client_id = get_secret_from_keyvault("ai-content-farm-core-kv", "reddit-client-id")
    client_secret = get_secret_from_keyvault(
        "ai-content-farm-core-kv", "reddit-client-secret"
    )
    user_agent = get_secret_from_keyvault(
        "ai-content-farm-core-kv", "reddit-user-agent"
    )

    if not all([client_id, client_secret, user_agent]):
        print("❌ Failed to retrieve all Reddit credentials")
        return False

    print(f"✅ Retrieved credentials:")
    print(f"   Client ID: {'*' * 10}... (length: {len(client_id)})")
    print(f"   Client Secret: {'*' * 5}... (length: {len(client_secret)})")
    print(f"   User Agent: {user_agent}")

    # Test Reddit API connection
    print("\n🔗 Testing Reddit API connection...")

    try:
        # Create Reddit instance
        reddit = praw.Reddit(
            client_id=client_id, client_secret=client_secret, user_agent=user_agent
        )

        # Test read-only access
        print("🧪 Testing read-only access...")

        # Try to get a simple subreddit
        subreddit = reddit.subreddit("technology")

        # Try to get just one post
        for submission in subreddit.hot(limit=1):
            print(f"✅ Successfully retrieved post: {submission.title[:50]}...")
            print(f"   Score: {submission.score}")
            print(f"   Comments: {submission.num_comments}")
            print(f"   URL: [REDACTED]")  # Don't log URLs for security
            break

        print("\n🎉 Reddit API authentication SUCCESS!")
        return True

    except Exception as e:
        print(f"❌ Reddit API authentication FAILED: {e}")
        return False


if __name__ == "__main__":
    success = test_reddit_credentials()
    sys.exit(0 if success else 1)
