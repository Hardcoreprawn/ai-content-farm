"""
Azure OpenAI Pricing Service

Cost-effective pricing cache using blob storage with smart fallback.
Updates pricing data weekly via Azure automation for accurate cost tracking.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import httpx

from libs import BlobStorageClient

logger = logging.getLogger(__name__)


class PricingService:
    """
    Cost-effective pricing service with blob cache and smart fallback.

    Features:
    - Weekly pricing updates via blob storage cache
    - Smart fallback to hardcoded prices
    - Minimal API calls for cost efficiency
    - Regional pricing awareness
    """

    def __init__(self):
        self.blob_client = BlobStorageClient()
        self.pricing_container = "pricing-cache"
        self.pricing_blob = "azure-openai-pricing.json"
        self.cache_duration_days = 7  # Weekly updates

        # Fallback pricing (UK South region, updated Sept 2025)
        self.fallback_pricing = {
            "gpt-35-turbo": {
                "input_per_1k": 0.0005,  # $0.50 per 1M tokens
                "output_per_1k": 0.0015,  # $1.50 per 1M tokens
            },
            "gpt-4": {
                "input_per_1k": 0.01,  # $10 per 1M tokens
                "output_per_1k": 0.03,  # $30 per 1M tokens
            },
            "gpt-4o": {
                "input_per_1k": 0.0025,  # $2.50 per 1M tokens
                "output_per_1k": 0.01,  # $10 per 1M tokens
            },
            "text-embedding-ada-002": {
                "input_per_1k": 0.0001,  # $0.10 per 1M tokens
                "output_per_1k": 0.0,  # No output cost for embeddings
            },
        }

    async def get_model_pricing(self, model_name: str) -> Dict[str, float]:
        """
        Get current pricing for a model with smart caching.

        Returns:
            Dict with input_per_1k and output_per_1k pricing
        """
        try:
            # Try to get cached pricing first
            cached_pricing = await self._get_cached_pricing()

            if cached_pricing and model_name in cached_pricing.get("models", {}):
                logger.info(f"Using cached pricing for {model_name}")
                return cached_pricing["models"][model_name]

        except Exception as e:
            logger.warning(f"Failed to retrieve cached pricing: {e}")

        # Fall back to hardcoded pricing
        if model_name in self.fallback_pricing:
            logger.info(f"Using fallback pricing for {model_name}")
            return self.fallback_pricing[model_name]

        # Unknown model - use gpt-35-turbo as default
        logger.warning(f"Unknown model {model_name}, using gpt-35-turbo pricing")
        return self.fallback_pricing["gpt-35-turbo"]

    async def _get_cached_pricing(self) -> Optional[Dict]:
        """
        Retrieve pricing from blob cache if not expired.
        """
        try:
            # Check if cached pricing exists and is recent
            pricing_data = await self.blob_client.download_json(
                container_name=self.pricing_container, blob_name=self.pricing_blob
            )

            if not pricing_data:
                logger.info("No cached pricing data found")
                return None

            # Check cache age
            cached_at = datetime.fromisoformat(pricing_data.get("cached_at", ""))
            age_days = (datetime.now(timezone.utc) - cached_at).days

            if age_days > self.cache_duration_days:
                logger.info(f"Cached pricing is {age_days} days old, needs refresh")
                return None

            logger.info(f"Using cached pricing from {age_days} days ago")
            return pricing_data

        except Exception as e:
            logger.error(f"Error retrieving cached pricing: {e}")
            return None

    async def calculate_cost(
        self, model_name: str, input_tokens: int, output_tokens: int
    ) -> float:
        """
        Calculate cost for token usage with current pricing.

        Returns:
            Cost in USD
        """
        try:
            pricing = await self.get_model_pricing(model_name)

            input_cost = (input_tokens / 1000) * pricing["input_per_1k"]
            output_cost = (output_tokens / 1000) * pricing["output_per_1k"]
            total_cost = input_cost + output_cost

            logger.debug(
                f"Cost calculation for {model_name}: "
                f"{input_tokens} input + {output_tokens} output = ${total_cost:.6f}"
            )

            return total_cost

        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            # Emergency fallback - use approximate cost
            return (input_tokens + output_tokens) / 1000 * 0.002

    async def update_pricing_cache(self) -> bool:
        """
        Update pricing cache from Azure API.

        This method is designed to be called by Azure Logic App
        or similar automation service weekly.
        """
        try:
            # Fetch current Azure OpenAI pricing
            pricing_data = await self._fetch_azure_pricing()

            if pricing_data:
                # Add cache metadata
                cache_data = {
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                    "source": "azure-api",
                    "region": "uksouth",
                    "models": pricing_data,
                }

                # Save to blob storage
                success = await self.blob_client.upload_json(
                    container_name=self.pricing_container,
                    blob_name=self.pricing_blob,
                    data=cache_data,
                )

                if success:
                    logger.info("Successfully updated pricing cache")
                    return True

        except Exception as e:
            logger.error(f"Failed to update pricing cache: {e}")

        return False

    async def _fetch_azure_pricing(self) -> Optional[Dict]:
        """
        Fetch current Azure OpenAI pricing from Azure API.

        Note: This is designed to be called infrequently (weekly)
        by automation, not by the main application.
        """
        try:
            # Azure Retail Prices API for UK South region
            # This is a free API that provides current Azure pricing
            pricing_url = (
                "https://prices.azure.com/api/retail/prices"
                "?api-version=2023-01-01-preview"
                "&$filter=serviceName eq 'Azure OpenAI' "
                "and armRegionName eq 'uksouth'"
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(pricing_url)
                response.raise_for_status()

                pricing_response = response.json()

                # Parse the pricing data into our format
                parsed_pricing = self._parse_azure_pricing_response(pricing_response)

                logger.info(
                    f"Successfully fetched pricing for {len(parsed_pricing)} models"
                )
                return parsed_pricing

        except Exception as e:
            logger.error(f"Failed to fetch Azure pricing: {e}")
            return None

    def _parse_azure_pricing_response(self, response: Dict) -> Dict:
        """
        Parse Azure pricing API response into our pricing format.
        """
        models = {}

        for item in response.get("Items", []):
            try:
                # Extract model information from the pricing item
                product_name = item.get("productName", "")
                meter_name = item.get("meterName", "")
                unit_price = float(item.get("unitPrice", 0))

                # Map Azure pricing to our model names
                model_mapping = {
                    "gpt-35-turbo": ["GPT-35-Turbo", "gpt-35-turbo"],
                    "gpt-4": ["GPT-4", "gpt-4"],
                    "gpt-4o": ["GPT-4o", "gpt-4o"],
                    "text-embedding-ada-002": ["Ada", "text-embedding-ada-002"],
                }

                for model_name, azure_names in model_mapping.items():
                    if any(
                        name in product_name or name in meter_name
                        for name in azure_names
                    ):
                        if model_name not in models:
                            models[model_name] = {"input_per_1k": 0, "output_per_1k": 0}

                        # Determine if this is input or output pricing
                        if (
                            "input" in meter_name.lower()
                            or "prompt" in meter_name.lower()
                        ):
                            models[model_name]["input_per_1k"] = unit_price
                        elif (
                            "output" in meter_name.lower()
                            or "completion" in meter_name.lower()
                        ):
                            models[model_name]["output_per_1k"] = unit_price
                        else:
                            # For embeddings or models with single pricing
                            models[model_name]["input_per_1k"] = unit_price

            except Exception as e:
                logger.warning(f"Failed to parse pricing item: {e}")
                continue

        return models

    async def get_pricing_status(self) -> Dict:
        """
        Get current pricing cache status for monitoring.
        """
        try:
            cached_pricing = await self._get_cached_pricing()

            if cached_pricing:
                cached_at = datetime.fromisoformat(cached_pricing["cached_at"])
                age_days = (datetime.now(timezone.utc) - cached_at).days

                return {
                    "cache_status": "active",
                    "cached_at": cached_pricing["cached_at"],
                    "age_days": age_days,
                    "models_cached": len(cached_pricing.get("models", {})),
                    "needs_refresh": age_days > self.cache_duration_days,
                }
            else:
                return {
                    "cache_status": "empty",
                    "cached_at": None,
                    "age_days": None,
                    "models_cached": 0,
                    "needs_refresh": True,
                }

        except Exception as e:
            return {"cache_status": "error", "error": str(e), "needs_refresh": True}
