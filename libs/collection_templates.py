"""
Collection Template Manager

Simple utility for managing pre-baked collection templates.
Templates are stored in blob storage and can be loaded by name.
"""

import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CollectionTemplateManager:
    """Manages pre-baked collection templates stored in blob storage."""

    def __init__(self, blob_client, container_name="collection-templates"):
        self.blob_client = blob_client
        self.container_name = container_name

    async def load_template(self, template_name: str) -> Optional[Dict]:
        """Load a collection template by name."""
        try:
            blob_name = f"{template_name}.json"
            content = await self.blob_client.download_blob(
                container_name=self.container_name, blob_name=blob_name
            )
            template = json.loads(content)

            # Return just the collection_request part
            return template.get("collection_request")

        except Exception as e:
            logger.error(f"Failed to load template '{template_name}': {e}")
            return None

    async def list_templates(self) -> List[Dict]:
        """List all available templates with metadata."""
        try:
            blobs = await self.blob_client.list_blobs(
                container_name=self.container_name
            )

            templates = []
            for blob_name in blobs:
                if blob_name.endswith(".json"):
                    try:
                        content = await self.blob_client.download_blob(
                            container_name=self.container_name, blob_name=blob_name
                        )
                        template = json.loads(content)

                        # Extract metadata
                        metadata = template.get("template_metadata", {})
                        metadata["template_id"] = blob_name.replace(".json", "")
                        templates.append(metadata)

                    except Exception as e:
                        logger.warning(
                            f"Failed to load template metadata from {blob_name}: {e}"
                        )

            return templates

        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []

    async def get_random_template(self, domain: Optional[str] = None) -> Optional[Dict]:
        """Get a random template, optionally filtered by domain."""
        try:
            templates = await self.list_templates()

            if domain:
                templates = [t for t in templates if t.get("domain") == domain]

            if not templates:
                return None

            import random

            selected = random.choice(templates)
            return await self.load_template(selected["template_id"])

        except Exception as e:
            logger.error(f"Failed to get random template: {e}")
            return None


# Example usage patterns:
"""
# Load specific template
template_mgr = CollectionTemplateManager(blob_client)
request = await template_mgr.load_template("technology-comprehensive")

# Get random template
request = await template_mgr.get_random_template()

# Get random AI/ML template
request = await template_mgr.get_random_template(domain="artificial-intelligence")

# List all available templates
templates = await template_mgr.list_templates()
for template in templates:
    print(f"- {template['name']}: {template['description']}")
"""
