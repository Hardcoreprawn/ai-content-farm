"""
Utility to configure Application Insights in Hugo config before building.

This script injects Application Insights credentials from environment variables
into the Hugo config.toml file, enabling client-side telemetry collection.

Usage:
    python configure_telemetry.py
"""

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def configure_hugo_telemetry(config_path: str) -> bool:
    """
    Update Hugo config.toml with Application Insights credentials.

    Reads Application Insights keys from environment variables and injects them
    into the Hugo configuration for client-side telemetry.

    Args:
        config_path: Path to config.toml file

    Returns:
        True if configuration was updated, False otherwise
    """
    config_file = Path(config_path)

    if not config_file.exists():
        logger.warning(f"Config file not found: {config_path}")
        return False

    # Get credentials from environment
    instrumentation_key = os.getenv("APPINSIGHTS_INSTRUMENTATION_KEY", "")
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")

    if not instrumentation_key and not connection_string:
        logger.info("No Application Insights credentials found - telemetry disabled")
        return False

    try:
        # Read current config
        config_content = config_file.read_text()

        # Escape special characters for regex
        escaped_key = re.escape(instrumentation_key) if instrumentation_key else ""
        escaped_conn = re.escape(connection_string) if connection_string else ""

        # Update instrumentation key
        if instrumentation_key:
            config_content = re.sub(
                r'instrumentationKey = ""',
                f'instrumentationKey = "{instrumentation_key}"',
                config_content,
            )
            logger.info(
                "Updated Hugo config with Application Insights instrumentation key"
            )

        # Update connection string
        if connection_string:
            config_content = re.sub(
                r'connectionString = ""',
                f'connectionString = "{connection_string}"',
                config_content,
            )
            logger.info(
                "Updated Hugo config with Application Insights connection string"
            )

        # Write back to file
        config_file.write_text(config_content)
        logger.info(f"Hugo telemetry configuration updated: {config_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to configure Hugo telemetry: {e}", exc_info=True)
        return False


def main():
    """Main entry point."""
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else "hugo-config/config.toml"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    success = configure_hugo_telemetry(config_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
