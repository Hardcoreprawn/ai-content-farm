#!/usr/bin/env python3
"""
Configuration module for Content Ranker service.

Handles environment variables, Azure connectivity, and health checks.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def get_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables.

    Returns:
        Configuration dictionary with service settings
    """
    config = {
        "environment": os.getenv("ENVIRONMENT", "production"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "service_name": "content-ranker",
        "service_version": "1.0.0",

        # API Configuration
        "api_host": os.getenv("API_HOST", "0.0.0.0"),
        "api_port": int(os.getenv("API_PORT", "8000")),

        # Ranking Configuration
        "default_weights": {
            "engagement": float(os.getenv("WEIGHT_ENGAGEMENT", "0.4")),
            "recency": float(os.getenv("WEIGHT_RECENCY", "0.35")),
            "topic_relevance": float(os.getenv("WEIGHT_TOPIC_RELEVANCE", "0.25"))
        },
        "recency_half_life_hours": float(os.getenv("RECENCY_HALF_LIFE_HOURS", "24")),
        "max_ranking_items": int(os.getenv("MAX_RANKING_ITEMS", "1000")),

        # Azure Configuration
        "azure_storage_account": os.getenv("AZURE_STORAGE_ACCOUNT"),
        "azure_key_vault_url": os.getenv("AZURE_KEY_VAULT_URL"),
        "azure_resource_group": os.getenv("AZURE_RESOURCE_GROUP"),

        # Performance Configuration
        "request_timeout": int(os.getenv("REQUEST_TIMEOUT", "30")),
        # 1MB
        "max_content_length": int(os.getenv("MAX_CONTENT_LENGTH", "1048576")),

        # Feature Flags
        "enable_caching": os.getenv("ENABLE_CACHING", "false").lower() == "true",
        "enable_metrics": os.getenv("ENABLE_METRICS", "true").lower() == "true",
        "enable_azure_logging": os.getenv("ENABLE_AZURE_LOGGING", "false").lower() == "true",
    }

    return config


def health_check() -> Dict[str, Any]:
    """
    Perform comprehensive health check.

    Returns:
        Health status dictionary
    """
    health_status = {
        "status": "healthy",
        "service": "content-ranker",
        "timestamp": None,
        "checks": {}
    }

    try:
        import datetime
        health_status["timestamp"] = datetime.datetime.utcnow().isoformat()

        # Check basic service functionality
        health_status["checks"]["basic_functionality"] = check_basic_functionality()

        # Check Azure connectivity (if configured)
        azure_status = check_azure_connectivity()
        if azure_status is not None:
            health_status["checks"]["azure_connectivity"] = azure_status
            health_status["azure_connectivity"] = azure_status["status"] == "healthy"

        # Check configuration
        health_status["checks"]["configuration"] = check_configuration()

        # Determine overall status
        failed_checks = [
            name for name, check in health_status["checks"].items()
            if check["status"] != "healthy"
        ]

        if failed_checks:
            health_status["status"] = "degraded" if len(
                failed_checks) == 1 else "unhealthy"
            health_status["failed_checks"] = failed_checks

    except Exception as e:
        logger.error(f"Health check error: {e}")
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)

    return health_status


def check_basic_functionality() -> Dict[str, Any]:
    """
    Check basic service functionality.

    Returns:
        Basic functionality check results
    """
    try:
        # Test ranking algorithms import
        from ranker import calculate_engagement_score, calculate_recency_score

        # Test basic calculations with proper data structures
        test_item = {
            "id": "test",
            "title": "Test",
            "engagement_score": 0.5,
            "published_at": "2024-01-01T00:00:00Z"
        }
        test_score = calculate_engagement_score(test_item)
        test_recency = calculate_recency_score(test_item)

        if isinstance(test_score, (int, float)) and isinstance(test_recency, (int, float)):
            return {
                "status": "healthy",
                "message": "Basic functionality operational"
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Ranking algorithms returning invalid types"
            }

    except ImportError as e:
        return {
            "status": "unhealthy",
            "message": f"Failed to import ranking modules: {e}"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Basic functionality test failed: {e}"
        }


def check_azure_connectivity() -> Optional[Dict[str, Any]]:
    """
    Check Azure service connectivity.

    Returns:
        Azure connectivity check results, or None if not configured
    """
    config = get_config()

    # Skip if Azure not configured
    if not any([
        config.get("azure_storage_account"),
        config.get("azure_key_vault_url"),
        config.get("azure_resource_group")
    ]):
        return None

    try:
        # Basic connectivity check
        # In a real implementation, this would test actual Azure services
        # For now, just check if credentials/config are available

        checks = {}

        if config.get("azure_storage_account"):
            checks["storage_account"] = "configured"

        if config.get("azure_key_vault_url"):
            checks["key_vault"] = "configured"

        if config.get("azure_resource_group"):
            checks["resource_group"] = "configured"

        return {
            "status": "healthy",
            "message": "Azure configuration available",
            "checks": checks
        }

    except Exception as e:
        logger.error(f"Azure connectivity check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Azure connectivity failed: {e}"
        }


def check_configuration() -> Dict[str, Any]:
    """
    Check service configuration validity.

    Returns:
        Configuration check results
    """
    try:
        config = get_config()

        # Validate critical configuration
        issues = []

        # Check weights sum to reasonable value
        weights = config["default_weights"]
        weights_sum = sum(weights.values())
        if not (0.8 <= weights_sum <= 1.2):
            issues.append(
                f"Weights sum ({weights_sum}) should be close to 1.0")

        # Check positive values
        if config["recency_half_life_hours"] <= 0:
            issues.append("Recency half-life must be positive")

        if config["max_ranking_items"] <= 0:
            issues.append("Max ranking items must be positive")

        # Check port range
        if not (1 <= config["api_port"] <= 65535):
            issues.append(f"Invalid API port: {config['api_port']}")

        if issues:
            return {
                "status": "unhealthy",
                "message": "Configuration validation failed",
                "issues": issues
            }
        else:
            return {
                "status": "healthy",
                "message": "Configuration valid"
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Configuration check failed: {e}"
        }


def get_ranking_defaults() -> Dict[str, Any]:
    """
    Get default ranking configuration.

    Returns:
        Default ranking parameters
    """
    config = get_config()

    return {
        "weights": config["default_weights"],
        "recency_half_life_hours": config["recency_half_life_hours"],
        "max_items": config["max_ranking_items"]
    }
