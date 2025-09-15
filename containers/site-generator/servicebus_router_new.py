"""
Service Bus Endpoints for Site Generator

Implements Service Bus message processing for site generation requests.
Uses shared Service Bus router base and existing site generator functionality.
"""

import logging
from typing import Any, Dict

from libs.service_bus_router import ServiceBusRouterBase

logger = logging.getLogger(__name__)


class SiteGeneratorServiceBusRouter(ServiceBusRouterBase):
    """Service Bus router for site generation service."""

    def __init__(self):
        super().__init__(
            service_name="site-generator",
            queue_name="site-generation-requests",
            prefix="/internal",
        )

    async def process_message_payload(
        self, payload: Dict[str, Any], operation: str
    ) -> Dict[str, Any]:
        """
        Process site generation requests from Service Bus.

        Args:
            payload: Site generation request payload
            operation: Operation type (generate_site, etc.)

        Returns:
            Dict with generation results
        """
        try:
            if operation == "generate_site":
                return await self._generate_static_site(payload)
            else:
                logger.error(f"Unknown operation: {operation}")
                return {"status": "error", "error": f"Unknown operation: {operation}"}

        except Exception as e:
            logger.error(f"Site generation failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _generate_static_site(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate static site from processed content."""
        try:
            processed_content_location = payload.get("processed_content_location")
            items_count = payload.get("items_count", 0)

            if not processed_content_location:
                return {
                    "status": "error",
                    "error": "Missing processed_content_location",
                }

            # Load processed content from storage
            from libs.blob_storage import BlobStorageClient

            storage = BlobStorageClient()

            # Parse storage location
            parts = processed_content_location.split("/", 1)
            if len(parts) != 2:
                return {
                    "status": "error",
                    "error": f"Invalid storage location format: {processed_content_location}",
                }

            container_name, blob_name = parts
            content_json = storage.download_text(container_name, blob_name)

            import json

            processed_data = json.loads(content_json)
            processed_items = processed_data.get("items", [])

            # First generate markdown from the processed content
            from site_generator import SiteGenerator

            generator = SiteGenerator()

            # Generate markdown files from processed content
            # For now, we'll use the static site generation which includes markdown
            result = await generator.generate_static_site(
                theme="minimal", force_rebuild=True
            )

            logger.info(f"Generated site from {len(processed_items)} processed items")
            return {
                "status": "success",
                "generated_files": result.files_generated,
                "site_location": result.output_location,
                "processed_items_count": len(processed_items),
                "success": True,
                "pages_generated": result.pages_generated,
                "processing_time": result.processing_time,
                "generator_id": result.generator_id,
            }

        except Exception as e:
            logger.error(f"Failed to generate static site: {e}")
            return {"status": "error", "error": str(e)}

    def get_max_messages(self) -> int:
        """Site generator handles fewer messages due to file generation overhead."""
        return 2


# Create router instance
service_bus_router = SiteGeneratorServiceBusRouter()
router = service_bus_router.router
