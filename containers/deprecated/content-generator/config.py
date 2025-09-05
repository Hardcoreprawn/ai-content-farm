import os
from typing import Any, Dict


class Config:
    """Configuration management for content generator service"""

    # Service Configuration
    SERVICE_NAME = "content-generator"
    VERSION = "1.0.0"
    PORT = int(os.getenv("PORT", 8000))

    # Blob Storage Configuration - Using Managed Identity
    STORAGE_ACCOUNT_NAME = os.getenv("STORAGE_ACCOUNT_NAME", "aicontentfarm76ko2h")
    STORAGE_ACCOUNT_URL = os.getenv(
        "STORAGE_ACCOUNT_URL",
        f"https://{os.getenv('STORAGE_ACCOUNT_NAME', 'aicontentfarm76ko2h')}.blob.core.windows.net",
    )
    RANKED_CONTENT_CONTAINER = os.getenv("RANKED_CONTENT_CONTAINER", "ranked-content")
    GENERATED_CONTENT_CONTAINER = os.getenv(
        "GENERATED_CONTENT_CONTAINER", "generated-content"
    )

    # Fallback to connection string for local development
    BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")

    # AI Service Configuration - Azure OpenAI Service
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv(
        "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
    )
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv(
        "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo"
    )

    # Fallback to OpenAI direct API (for development/testing)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    DEFAULT_AI_MODEL = os.getenv("DEFAULT_AI_MODEL", "gpt-3.5-turbo")

    # Content Generation Configuration
    DEFAULT_TLDR_WORDS = int(os.getenv("DEFAULT_TLDR_WORDS", 300))
    DEFAULT_BLOG_WORDS = int(os.getenv("DEFAULT_BLOG_WORDS", 800))
    DEFAULT_DEEPDIVE_WORDS = int(os.getenv("DEFAULT_DEEPDIVE_WORDS", 2000))

    # Writer Personalities
    WRITER_PERSONALITIES = {
        "professional": "Authoritative, balanced, fact-focused business tone",
        "analytical": "Data-driven, technical, research-oriented perspective",
        "casual": "Conversational, accessible, everyday language",
        "expert": "Deep technical knowledge, industry insider perspective",
        "skeptical": "Critical thinking, question assumptions, devil's advocate",
        "enthusiast": "Excited, optimistic, focused on possibilities",
    }

    # Content Verification
    ENABLE_SOURCE_VERIFICATION = (
        os.getenv("ENABLE_SOURCE_VERIFICATION", "true").lower() == "true"
    )
    VERIFICATION_TIMEOUT = int(os.getenv("VERIFICATION_TIMEOUT", 30))  # seconds

    # Generation Limits
    MAX_CONCURRENT_GENERATIONS = int(os.getenv("MAX_CONCURRENT_GENERATIONS", 3))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", 5))

    # Quality Control
    MIN_QUALITY_SCORE = float(os.getenv("MIN_QUALITY_SCORE", 0.7))
    ENABLE_FACT_CHECK = os.getenv("ENABLE_FACT_CHECK", "true").lower() == "true"

    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration and return status"""
        issues = []

        # Check required API keys
        has_azure_ai = bool(cls.AZURE_OPENAI_ENDPOINT and cls.AZURE_OPENAI_API_KEY)
        has_openai_direct = bool(cls.OPENAI_API_KEY)
        has_claude = bool(cls.CLAUDE_API_KEY)

        if not (has_azure_ai or has_openai_direct or has_claude):
            issues.append("No AI services configured (Azure OpenAI, OpenAI, or Claude)")

        # Check blob storage configuration
        has_managed_identity_storage = bool(
            cls.STORAGE_ACCOUNT_NAME or cls.STORAGE_ACCOUNT_URL
        )
        has_connection_string = bool(
            cls.BLOB_CONNECTION_STRING
            and cls.BLOB_CONNECTION_STRING != "UseDevelopmentStorage=true"
        )

        if not (has_managed_identity_storage or has_connection_string):
            issues.append(
                "No blob storage configured (STORAGE_ACCOUNT_NAME/URL or BLOB_CONNECTION_STRING)"
            )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "config": {
                "service_name": cls.SERVICE_NAME,
                "version": cls.VERSION,
                "port": cls.PORT,
                "ai_model": cls.DEFAULT_AI_MODEL,
                "has_azure_openai": has_azure_ai,
                "has_openai": has_openai_direct,
                "has_claude": has_claude,
                "storage_account": cls.STORAGE_ACCOUNT_NAME,
                "blob_storage": (
                    "managed_identity"
                    if has_managed_identity_storage
                    else (
                        "connection_string" if has_connection_string else "development"
                    )
                ),
            },
        }


# Create global config instance
config = Config()
