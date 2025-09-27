"""
Diagnostics Endpoints - Health, Status, and Troubleshooting

RESTful endpoints for service health checks and diagnostic information.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from config import ENVIRONMENT, settings
from libs.blob_auth import BlobAuthManager
from libs.data_contracts import ContractValidator, DataContractError
from libs.shared_models import StandardResponse, create_service_dependency
from libs.simplified_blob_client import SimplifiedBlobClient
from libs.standard_endpoints import (
    create_standard_health_endpoint,
    create_standard_root_endpoint,
    create_standard_status_endpoint,
)

# Create router for diagnostics
router = APIRouter(tags=["diagnostics"])

# Create service metadata dependency
service_metadata = create_service_dependency("content-processor")

# Standard endpoints
router.add_api_route(
    "/",
    create_standard_root_endpoint(
        service_name="content-processor",
        description="AI-powered content processing service",
        version=settings.service_version,
        available_endpoints=[
            "/pipeline",
            "/processing/diagnostics",
            "/process",
            "/process/wake-up",
            "/process/types",
            "/process/status",
            "/storage-queue/health",
            "/storage-queue/process",
            "/storage-queue/send-wake-up",
        ],
    ),
    methods=["GET"],
    summary="Service Root",
    description="Get basic information about the content processor service",
)

router.add_api_route(
    "/health",
    create_standard_health_endpoint(
        service_name="content-processor",
        version=settings.service_version,
        environment=ENVIRONMENT,
        service_metadata_dep=service_metadata,
    ),
    methods=["GET"],
    summary="Health Check",
    description="Check service health and dependencies",
)

router.add_api_route(
    "/status",
    create_standard_status_endpoint(
        service_name="content-processor",
        version=settings.service_version,
        environment=ENVIRONMENT,
        service_metadata_dep=service_metadata,
    ),
    methods=["GET"],
    summary="Service Status",
    description="Get detailed service status and configuration",
)


@router.get(
    "/processing/diagnostics",
    response_model=StandardResponse,
    summary="Processing Diagnostics",
    description="Get content processing service diagnostics",
    tags=["diagnostics"],
)
async def get_processing_diagnostics(
    metadata: Dict[str, Any] = Depends(service_metadata),
) -> StandardResponse:
    """Get content processing service diagnostics."""
    try:
        # Basic processing service checks
        diagnostics = {
            "processing_service": "available",
            "ai_models": {
                "openai": "configured" if _check_openai_config() else "not_configured",
                "anthropic": (
                    "configured" if _check_anthropic_config() else "not_configured"
                ),
            },
            "storage": {
                "blob_storage": "available" if _check_blob_storage() else "unavailable",
            },
            "dependencies": {
                "content_generator": (
                    "available" if _check_content_generator() else "unavailable"
                ),
                "processing_service": (
                    "available" if _check_processing_service() else "unavailable"
                ),
            },
            "environment": ENVIRONMENT,
        }

        return StandardResponse(
            status="success",
            message="Content processor diagnostics retrieved successfully",
            data=diagnostics,
            errors=None,
            metadata=metadata,
        )

    except Exception as e:
        return StandardResponse(
            status="error",
            message=f"Failed to get diagnostics: {str(e)}",
            data=None,
            errors=[str(e)],
            metadata=metadata,
        )


def _check_openai_config() -> bool:
    """Check if OpenAI is properly configured."""
    try:
        import os

        return bool(os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_ENDPOINT"))
    except Exception:
        return False


def _check_anthropic_config() -> bool:
    """Check if Anthropic is properly configured."""
    try:
        import os

        return bool(os.getenv("ANTHROPIC_API_KEY"))
    except Exception:
        return False


def _check_blob_storage() -> bool:
    """Check if blob storage is available."""
    try:
        from libs.simplified_blob_client import SimplifiedBlobClient

        storage = SimplifiedBlobClient()
        # Simple check - if we can create client, it's configured
        return True
    except Exception:
        return False


def _check_content_generator() -> bool:
    """Check if content generator is available."""
    try:
        from content_generation import get_content_generator

        generator = get_content_generator()
        return True
    except Exception:
        return False


def _check_processing_service() -> bool:
    """Check if processing service is available."""
    try:
        from processing_service import ContentProcessingService

        from config import settings

        processor = ContentProcessingService(settings)
        return True
    except Exception:
        return False


# Pipeline Diagnostics Models
class DiagnosticTest(BaseModel):
    """Result of a single diagnostic test."""

    name: str = Field(..., description="Test name")
    status: str = Field(..., description="pass, fail, or warning")
    message: str = Field(..., description="Test result message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional test details"
    )
    duration_ms: Optional[float] = Field(
        None, description="Test execution time in milliseconds"
    )


class PipelineDiagnosticsResponse(BaseModel):
    """Complete pipeline diagnostics response."""

    overall_status: str = Field(
        ..., description="Overall pipeline health: healthy, degraded, or failed"
    )
    summary: str = Field(..., description="Summary of diagnostic results")
    tests: List[DiagnosticTest] = Field(..., description="Individual test results")
    recommendations: List[str] = Field(
        ..., description="Recommended actions based on results"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PipelineDiagnostics:
    """In-container pipeline diagnostics."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def run_all_tests(
        self, deep_scan: bool = False
    ) -> PipelineDiagnosticsResponse:
        """Run complete diagnostic suite."""
        tests = []
        recommendations = []

        # Test 1: Environment Variables
        env_test = await self._test_environment_variables()
        tests.append(env_test)

        # Test 2: Blob Authentication
        auth_test = await self._test_blob_authentication()
        tests.append(auth_test)

        # Test 3: Configuration Loading
        config_test = await self._test_configuration_loading()
        tests.append(config_test)

        # Test 4: Blob Connectivity
        conn_test = await self._test_blob_connectivity()
        tests.append(conn_test)

        # Test 5: Container Access
        container_test = await self._test_container_access()
        tests.append(container_test)

        # Test 6: Collection Discovery (if deep scan enabled)
        if deep_scan:
            discovery_test = await self._test_collection_discovery()
            tests.append(discovery_test)

            # Test 7: Data Validation
            validation_test = await self._test_data_validation()
            tests.append(validation_test)

        # Determine overall status
        failed_tests = [t for t in tests if t.status == "fail"]
        warning_tests = [t for t in tests if t.status == "warning"]

        if failed_tests:
            overall_status = "failed"
            summary = f"{len(failed_tests)} tests failed, {len(warning_tests)} warnings"
            recommendations.extend(self._get_failure_recommendations(failed_tests))
        elif warning_tests:
            overall_status = "degraded"
            summary = f"All tests passed with {len(warning_tests)} warnings"
            recommendations.extend(self._get_warning_recommendations(warning_tests))
        else:
            overall_status = "healthy"
            summary = "All pipeline tests passed successfully"
            recommendations.append("Pipeline is healthy - no action required")

        return PipelineDiagnosticsResponse(
            overall_status=overall_status,
            summary=summary,
            tests=tests,
            recommendations=recommendations,
        )

    async def _test_environment_variables(self) -> DiagnosticTest:
        """Test required environment variables."""
        start_time = datetime.now()
        required_vars = [
            "AZURE_STORAGE_ACCOUNT_NAME",
            "AZURE_CLIENT_ID",
            "AZURE_TENANT_ID",
            "AZURE_SUBSCRIPTION_ID",
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        duration = (datetime.now() - start_time).total_seconds() * 1000

        if missing_vars:
            return DiagnosticTest(
                name="Environment Variables",
                status="fail",
                message=f"Missing required environment variables: {', '.join(missing_vars)}",
                details={
                    "missing_variables": missing_vars,
                    "required_variables": required_vars,
                },
                duration_ms=duration,
            )
        else:
            return DiagnosticTest(
                name="Environment Variables",
                status="pass",
                message="All required environment variables are present",
                details={"checked_variables": required_vars},
                duration_ms=duration,
            )

    async def _test_configuration_loading(self) -> DiagnosticTest:
        """Test loading configuration from blob storage."""
        start_time = datetime.now()

        try:
            # Import ProcessingConfigManager
            from libs.processing_config import ProcessingConfigManager
            from libs.simplified_blob_client import SimplifiedBlobClient

            blob_client = SimplifiedBlobClient()
            config_manager = ProcessingConfigManager(blob_client)

            # Try to load container configuration
            container_config = await config_manager.get_container_config(
                "content-processor"
            )

            # Try to load processing configuration
            processing_config = await config_manager.get_processing_config(
                "content-processor"
            )

            duration = (datetime.now() - start_time).total_seconds() * 1000

            config_details = {
                "container_config": {
                    "input_container": container_config.get(
                        "input_container", "default"
                    ),
                    "output_container": container_config.get(
                        "output_container", "default"
                    ),
                    "collections_prefix": container_config.get(
                        "collections_prefix", "default"
                    ),
                },
                "processing_config": {
                    "default_batch_size": processing_config.get(
                        "default_batch_size", "default"
                    ),
                    "max_batch_size": processing_config.get(
                        "max_batch_size", "default"
                    ),
                    "default_priority_threshold": processing_config.get(
                        "default_priority_threshold", "default"
                    ),
                },
                "config_source": (
                    "blob_storage"
                    if "input_container" in container_config
                    else "defaults"
                ),
            }

            return DiagnosticTest(
                name="Configuration Loading",
                status="pass",
                message=f"Configuration loaded successfully from {config_details['config_source']}",
                details=config_details,
                duration_ms=duration,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return DiagnosticTest(
                name="Configuration Loading",
                status="fail",
                message=f"Failed to load configuration: {str(e)}",
                details={"error": str(e), "config_source": "unknown"},
                duration_ms=duration,
            )

    async def _test_blob_authentication(self) -> DiagnosticTest:
        """Test Azure blob authentication."""
        start_time = datetime.now()

        try:
            auth_manager = BlobAuthManager()
            connection_result = auth_manager.test_connection()

            duration = (datetime.now() - start_time).total_seconds() * 1000

            if connection_result:
                return DiagnosticTest(
                    name="Blob Authentication",
                    status="pass",
                    message="Successfully authenticated to blob storage",
                    details={"connection_test": "passed"},
                    duration_ms=duration,
                )
            else:
                return DiagnosticTest(
                    name="Blob Authentication",
                    status="fail",
                    message="Blob authentication test failed",
                    details={"connection_test": "failed"},
                    duration_ms=duration,
                )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return DiagnosticTest(
                name="Blob Authentication",
                status="fail",
                message=f"Authentication failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                duration_ms=duration,
            )

    async def _test_blob_connectivity(self) -> DiagnosticTest:
        """Test basic blob storage connectivity."""
        start_time = datetime.now()

        try:
            blob_client = SimplifiedBlobClient()
            connectivity = blob_client.test_connection()

            duration = (datetime.now() - start_time).total_seconds() * 1000

            if connectivity.get("status") == "connected":
                return DiagnosticTest(
                    name="Blob Connectivity",
                    status="pass",
                    message="Successfully connected to blob storage",
                    details=connectivity,
                    duration_ms=duration,
                )
            else:
                return DiagnosticTest(
                    name="Blob Connectivity",
                    status="fail",
                    message="Failed to connect to blob storage",
                    details=connectivity,
                    duration_ms=duration,
                )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return DiagnosticTest(
                name="Blob Connectivity",
                status="fail",
                message=f"Connectivity test failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                duration_ms=duration,
            )

    async def _test_container_access(self) -> DiagnosticTest:
        """Test access to collected-content container."""
        start_time = datetime.now()

        try:
            blob_client = SimplifiedBlobClient()
            blobs = await blob_client.list_blobs("collected-content")

            duration = (datetime.now() - start_time).total_seconds() * 1000

            return DiagnosticTest(
                name="Container Access",
                status="pass",
                message=f"Successfully listed {len(blobs)} blobs in collected-content container",
                details={
                    "blob_count": len(blobs),
                    "recent_blobs": [b.get("name", "unknown") for b in blobs[-3:]],
                },
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return DiagnosticTest(
                name="Container Access",
                status="fail",
                message=f"Failed to access collected-content container: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                duration_ms=duration,
            )

    async def _test_collection_discovery(self) -> DiagnosticTest:
        """Test collection discovery and parsing."""
        start_time = datetime.now()

        try:
            blob_client = SimplifiedBlobClient()
            blobs = await blob_client.list_blobs("collected-content")

            if not blobs:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                return DiagnosticTest(
                    name="Collection Discovery",
                    status="warning",
                    message="No collections found - nothing to process",
                    details={"blob_count": 0},
                    duration_ms=duration,
                )

            # Test downloading the most recent blob
            recent_blob = blobs[-1]
            collection_data = await blob_client.download_json(
                "collected-content", recent_blob["name"]
            )

            items = collection_data.get("items", [])
            duration = (datetime.now() - start_time).total_seconds() * 1000

            return DiagnosticTest(
                name="Collection Discovery",
                status="pass",
                message=f"Successfully discovered and parsed collection with {len(items)} items",
                details={
                    "recent_collection": recent_blob["name"],
                    "item_count": len(items),
                    "collection_keys": list(collection_data.keys()),
                    "sample_items": len(items[:3]),
                },
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return DiagnosticTest(
                name="Collection Discovery",
                status="fail",
                message=f"Failed to discover/parse collections: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                duration_ms=duration,
            )

    async def _test_data_validation(self) -> DiagnosticTest:
        """Test data contract validation."""
        start_time = datetime.now()

        try:
            blob_client = SimplifiedBlobClient()
            blobs = await blob_client.list_blobs("collected-content")

            if not blobs:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                return DiagnosticTest(
                    name="Data Validation",
                    status="warning",
                    message="No collections to validate",
                    details={},
                    duration_ms=duration,
                )

            # Test validation on most recent collection
            recent_blob = blobs[-1]
            collection_data = await blob_client.download_json(
                "collected-content", recent_blob["name"]
            )

            # Try to validate with contracts
            validated_collection = ContractValidator.validate_collection_data(
                collection_data
            )

            duration = (datetime.now() - start_time).total_seconds() * 1000

            return DiagnosticTest(
                name="Data Validation",
                status="pass",
                message=f"Successfully validated collection with {len(validated_collection.items)} items",
                details={
                    "validated_collection": recent_blob["name"],
                    "validated_items": len(validated_collection.items),
                    "schema_version": getattr(
                        validated_collection, "schema_version", "unknown"
                    ),
                },
                duration_ms=duration,
            )
        except DataContractError as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return DiagnosticTest(
                name="Data Validation",
                status="fail",
                message=f"Data contract validation failed: {str(e)}",
                details={"error": str(e), "error_type": "DataContractError"},
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return DiagnosticTest(
                name="Data Validation",
                status="fail",
                message=f"Validation test failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                duration_ms=duration,
            )

    def _get_failure_recommendations(
        self, failed_tests: List[DiagnosticTest]
    ) -> List[str]:
        """Get recommendations for failed tests."""
        recommendations = []

        for test in failed_tests:
            if test.name == "Environment Variables":
                recommendations.append(
                    "Set missing environment variables in container configuration"
                )
            elif test.name == "Blob Authentication":
                recommendations.append(
                    "Check Azure managed identity configuration and permissions"
                )
            elif test.name == "Blob Connectivity":
                recommendations.append(
                    "Verify network connectivity and storage account access"
                )
            elif test.name == "Container Access":
                recommendations.append(
                    "Verify 'collected-content' container exists and has read permissions"
                )
            elif test.name == "Collection Discovery":
                recommendations.append(
                    "Check if collector is running and generating content"
                )
            elif test.name == "Data Validation":
                recommendations.append(
                    "Use debug_bypass=true to skip validation, or fix collection format"
                )

        return recommendations

    def _get_warning_recommendations(
        self, warning_tests: List[DiagnosticTest]
    ) -> List[str]:
        """Get recommendations for warning tests."""
        recommendations = []

        for test in warning_tests:
            if test.name == "Collection Discovery":
                recommendations.append("Run collector to generate content")
            elif test.name == "Data Validation":
                recommendations.append("Check collection format compliance")

        return recommendations


@router.get("/pipeline", response_model=StandardResponse[PipelineDiagnosticsResponse])
async def pipeline_diagnostics(
    deep_scan: bool = Query(
        False, description="Run deep diagnostics including collection parsing"
    ),
    metadata: Dict[str, Any] = Depends(service_metadata),
) -> StandardResponse[PipelineDiagnosticsResponse]:
    """
    Comprehensive pipeline diagnostics endpoint.

    Tests the entire content processor pipeline from blob authentication
    to data validation. Use deep_scan=true for thorough testing including
    collection parsing and validation.

    Perfect for diagnosing why the processor isn't finding or processing content.
    """
    try:
        diagnostics = PipelineDiagnostics()
        result = await diagnostics.run_all_tests(deep_scan=deep_scan)

        return StandardResponse(
            status="success",
            message=f"Pipeline diagnostics completed: {result.overall_status}",
            data=result,
            metadata=metadata,
        )

    except Exception as e:
        return StandardResponse(
            status="error",
            message=f"Diagnostics failed: {str(e)}",
            data=None,
            errors=[str(e)],
            metadata=metadata,
        )
