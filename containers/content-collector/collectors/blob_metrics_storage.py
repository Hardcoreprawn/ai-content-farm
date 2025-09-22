"""
Persistent Metrics Storage for Adaptive Collection Strategies - LEGACY

DEPRECATED: Complex blob storage for adaptive strategy metrics
Status: PENDING REMOVAL - Not needed with simplified collectors

Was used to persist complex adaptive strategy state across restarts.
Simplified collectors don't need persistent state.

Provides Azure Blob Storage integration for persisting collection metrics,
strategy parameters, and learned behaviors across container restarts.
"""

import asyncio
import json
import logging
import os

# Import your existing blob storage client
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from blob_storage import BlobStorageClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))

logger = logging.getLogger(__name__)


class BlobMetricsStorage:
    """Handles persistent storage of collection metrics and strategy data in Azure Blob Storage."""

    def __init__(self, container_name: str = "collection-metrics"):
        """
        Initialize blob metrics storage.

        Args:
            container_name: Azure Blob Storage container for metrics
        """
        self.container_name = container_name
        self.blob_client = BlobStorageClient()
        self._ensure_container()

    def _ensure_container(self) -> None:
        """Ensure the metrics container exists."""
        try:
            self.blob_client.ensure_container(self.container_name)
            logger.info(f"Metrics container '{self.container_name}' ready")
        except Exception as e:
            logger.error(f"Failed to ensure metrics container: {e}")
            raise

    async def save_strategy_metrics(
        self,
        strategy_key: str,
        metrics_data: Dict[str, Any],
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save strategy metrics to blob storage.

        Args:
            strategy_key: Unique identifier for the strategy
            metrics_data: Metrics data to save
            strategy_params: Optional strategy parameters

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create comprehensive data structure
            blob_data = {
                "strategy_key": strategy_key,
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics_data,
                "strategy_params": strategy_params or {},
                "version": "1.0",
            }

            # Use timestamp-based blob naming for history
            blob_name = f"strategies/{strategy_key}/metrics/{datetime.now().strftime('%Y/%m/%d/%H%M%S')}.json"

            # Also save as "latest" for quick access
            latest_blob_name = f"strategies/{strategy_key}/latest.json"

            # Save both timestamped and latest versions
            await self.blob_client.upload_json(
                self.container_name, blob_name, blob_data
            )
            await self.blob_client.upload_json(
                self.container_name, latest_blob_name, blob_data
            )

            logger.debug(f"Saved metrics for strategy {strategy_key} to blob storage")
            return True

        except Exception as e:
            logger.error(f"Failed to save metrics for {strategy_key}: {e}")
            return False

    async def load_strategy_metrics(
        self, strategy_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load latest strategy metrics from blob storage.

        Args:
            strategy_key: Unique identifier for the strategy

        Returns:
            Metrics data if found, None otherwise
        """
        try:
            blob_name = f"strategies/{strategy_key}/latest.json"
            data = await self.blob_client.download_json(self.container_name, blob_name)

            if data:
                logger.debug(
                    f"Loaded metrics for strategy {strategy_key} from blob storage"
                )
                return data

        except Exception as e:
            logger.debug(f"No previous metrics found for {strategy_key}: {e}")

        return None

    async def get_strategy_history(
        self, strategy_key: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get historical metrics for a strategy.

        Args:
            strategy_key: Unique identifier for the strategy
            days: Number of days of history to retrieve

        Returns:
            List of historical metrics
        """
        try:
            prefix = f"strategies/{strategy_key}/metrics/"
            blobs = await self.blob_client.list_blobs(self.container_name, prefix)

            # Filter blobs by date range
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_blobs = []

            for blob in blobs:
                # Extract date from blob name pattern: YYYY/MM/DD/HHMMSS.json
                try:
                    date_part = (
                        blob["name"].split("/metrics/")[1].split("/")[0:3]
                    )  # YYYY, MM, DD
                    blob_date = datetime(
                        int(date_part[0]), int(date_part[1]), int(date_part[2])
                    )

                    if blob_date >= cutoff_date.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ):
                        recent_blobs.append(blob)

                except (IndexError, ValueError):
                    continue  # Skip malformed blob names

            # Load data from recent blobs
            history = []
            # Last 50 entries
            for blob in sorted(recent_blobs, key=lambda x: x["name"], reverse=True)[
                :50
            ]:
                try:
                    data = await self.blob_client.download_json(
                        self.container_name, blob["name"]
                    )
                    if data:
                        history.append(data)
                except Exception as e:
                    logger.warning(
                        f"Failed to load historical metrics from {blob['name']}: {e}"
                    )

            return history

        except Exception as e:
            logger.error(f"Failed to get strategy history for {strategy_key}: {e}")
            return []

    async def save_global_metrics(self, global_data: Dict[str, Any]) -> bool:
        """
        Save global collection metrics.

        Args:
            global_data: Global metrics data

        Returns:
            True if successful, False otherwise
        """
        try:
            blob_data = {
                "timestamp": datetime.now().isoformat(),
                "data": global_data,
                "version": "1.0",
            }

            # Save timestamped version
            blob_name = (
                f"global/metrics/{datetime.now().strftime('%Y/%m/%d/%H%M%S')}.json"
            )
            await self.blob_client.upload_json(
                self.container_name, blob_name, blob_data
            )

            # Save latest version
            latest_blob_name = "global/latest.json"
            await self.blob_client.upload_json(
                self.container_name, latest_blob_name, blob_data
            )

            logger.debug("Saved global metrics to blob storage")
            return True

        except Exception as e:
            logger.error(f"Failed to save global metrics: {e}")
            return False

    async def load_global_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Load latest global metrics.

        Returns:
            Global metrics data if found, None otherwise
        """
        try:
            data = await self.blob_client.download_json(
                self.container_name, "global/latest.json"
            )
            if data:
                logger.debug("Loaded global metrics from blob storage")
                return data

        except Exception as e:
            logger.debug(f"No previous global metrics found: {e}")

        return None

    async def save_performance_report(
        self, report_data: Dict[str, Any], report_type: str = "comprehensive"
    ) -> str:
        """
        Save performance report to blob storage.

        Args:
            report_data: Report data
            report_type: Type of report (comprehensive, daily, etc.)

        Returns:
            Blob name of saved report
        """
        try:
            timestamp = datetime.now()
            blob_name = (
                f"reports/{report_type}/{timestamp.strftime('%Y/%m/%d/%H%M%S')}.json"
            )

            await self.blob_client.upload_json(
                self.container_name, blob_name, report_data
            )
            logger.info(f"Saved {report_type} performance report to {blob_name}")

            return blob_name

        except Exception as e:
            logger.error(f"Failed to save performance report: {e}")
            raise

    async def cleanup_old_metrics(self, retention_days: int = 30) -> int:
        """
        Clean up old metrics data to manage storage costs.

        Args:
            retention_days: Number of days to retain data

        Returns:
            Number of blobs deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            deleted_count = 0

            # Get all metrics blobs
            for prefix in ["strategies/", "global/metrics/"]:
                blobs = await self.blob_client.list_blobs(self.container_name, prefix)

                for blob in blobs:
                    # Skip "latest" files
                    if "latest.json" in blob["name"]:
                        continue

                    # Check blob modification time
                    if "last_modified" in blob and blob["last_modified"] < cutoff_date:
                        try:
                            await self.blob_client.delete_blob(
                                self.container_name, blob["name"]
                            )
                            deleted_count += 1
                            logger.debug(f"Deleted old metrics blob: {blob['name']}")
                        except Exception as e:
                            logger.warning(f"Failed to delete blob {blob['name']}: {e}")

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old metrics blobs")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
            return 0

    async def get_storage_usage(self) -> Dict[str, Any]:
        """
        Get storage usage statistics for the metrics container.

        Returns:
            Storage usage statistics
        """
        try:
            blobs = await self.blob_client.list_blobs(self.container_name)

            total_size = sum(blob.get("size", 0) for blob in blobs)
            blob_count = len(blobs)

            # Categorize by type
            strategy_blobs = len(
                [b for b in blobs if b["name"].startswith("strategies/")]
            )
            global_blobs = len([b for b in blobs if b["name"].startswith("global/")])
            report_blobs = len([b for b in blobs if b["name"].startswith("reports/")])

            return {
                "total_blobs": blob_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "strategy_blobs": strategy_blobs,
                "global_blobs": global_blobs,
                "report_blobs": report_blobs,
                "container_name": self.container_name,
            }

        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return {"error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """
        Check health of blob metrics storage.

        Returns:
            Health check results
        """
        try:
            # Test basic blob connectivity
            blob_health = self.blob_client.health_check()

            if blob_health.get("status") == "healthy":
                return {
                    "status": "healthy",
                    "container": self.container_name,
                    "blob_storage": blob_health,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "unhealthy",
                    "container": self.container_name,
                    "blob_storage": blob_health,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# Global storage instance
_global_metrics_storage: Optional[BlobMetricsStorage] = None


def get_metrics_storage() -> BlobMetricsStorage:
    """Get or create global metrics storage instance."""
    global _global_metrics_storage
    if _global_metrics_storage is None:
        _global_metrics_storage = BlobMetricsStorage()
    return _global_metrics_storage
