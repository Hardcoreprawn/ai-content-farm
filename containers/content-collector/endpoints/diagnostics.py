"""
Diagnostics Endpoints - Health, Status, and Troubleshooting

RESTful endpoints for service health checks and diagnostic information.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends
from reddit_client import RedditClient
from source_collectors import SourceCollectorFactory

from config import ENVIRONMENT
from libs.shared_models import StandardResponse, create_service_dependency
from libs.standard_endpoints import (
    create_standard_health_endpoint,
    create_standard_root_endpoint,
    create_standard_status_endpoint,
)

# Create router for diagnostics
router = APIRouter(tags=["diagnostics"])

# Create service metadata dependency
service_metadata = create_service_dependency("content-womble")

# Standard endpoints
router.add_api_route(
    "/",
    create_standard_root_endpoint(
        service_name="Content Womble",
        description="A humble service for collecting and analyzing digital content",
        version="2.0.1",
        available_endpoints=[
            "/health",
            "/status",
            "/collections",
            "/discoveries",
            "/sources",
            "/docs",
        ],
        service_metadata_dep=service_metadata,
    ),
    methods=["GET"],
)
router.add_api_route(
    "/health",
    create_standard_health_endpoint(
        service_name="content-womble",
        version="2.0.1",
        environment="development",
        service_metadata_dep=service_metadata,
    ),
    methods=["GET"],
)
router.add_api_route(
    "/status",
    create_standard_status_endpoint(
        service_name="content-womble",
        version="2.0.1",
        environment="development",
        service_metadata_dep=service_metadata,
    ),
    methods=["GET"],
)


@router.get(
    "/reddit/diagnostics",
    response_model=StandardResponse,
    summary="Reddit API Diagnostics",
    description="Detailed diagnostics for Reddit API connectivity and authentication",
)
async def reddit_diagnostics(
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Perform comprehensive Reddit API diagnostics.

    Tests connectivity, authentication, and provides detailed status information
    for troubleshooting Reddit integration issues.
    """
    try:
        # Get collector information
        collector_info = SourceCollectorFactory.get_reddit_collector_info()

        # Create the recommended collector for testing
        collector = SourceCollectorFactory.create_collector("reddit")

        # Test connectivity and authentication
        connectivity_test = await collector.check_connectivity()
        auth_test = await collector.check_authentication()

        # If it's a PRAW collector, get credential status
        credential_status = {}
        if hasattr(collector, "credential_status"):
            credential_status = getattr(collector, "credential_status", {})

        return StandardResponse(
            status="success",
            message="Reddit diagnostics completed",
            data={
                "collector_info": collector_info,
                "connectivity": {
                    "status": connectivity_test[0],
                    "message": connectivity_test[1],
                },
                "authentication": {
                    "status": auth_test[0],
                    "message": auth_test[1],
                },
                "credential_status": credential_status,
                "environment": ENVIRONMENT,
                "recommendations": _get_reddit_recommendations(
                    collector_info, connectivity_test, auth_test
                ),
            },
            errors=[],
            metadata=metadata,
        )

    except Exception as e:
        return StandardResponse(
            status="error",
            message=f"Reddit diagnostics failed: {str(e)}",
            data={},
            errors=[str(e)],
            metadata=metadata,
        )


def _get_reddit_recommendations(collector_info, connectivity_test, auth_test):
    """Generate recommendations based on diagnostic results."""
    recommendations = []

    if not connectivity_test[0]:
        recommendations.append(
            "Check internet connectivity and Reddit API availability"
        )

    if not auth_test[0]:
        if "credentials" in auth_test[1].lower():
            recommendations.append("Verify Reddit credentials in Azure Key Vault")
            recommendations.append(
                "Ensure reddit-client-id and reddit-client-secret are set"
            )
        elif "rate" in auth_test[1].lower():
            recommendations.append("Reddit API rate limited - wait before retrying")
        else:
            recommendations.append("Check Reddit API authentication configuration")

    if collector_info.get("recommended_collector") == "RedditPublicCollector":
        recommendations.append(
            "Using public API (limited functionality) - add credentials for full access"
        )

    if not recommendations:
        recommendations.append(
            "All Reddit diagnostics passed - API is working correctly"
        )

    return recommendations
