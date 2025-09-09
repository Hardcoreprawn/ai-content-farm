"""
Pipeline Orchestrator Azure Functions

Replaces Logic App with cost-effective, Terraform-friendly pipeline automation.
Handles scheduled content collection and blob-triggered pipeline progression.

Functions:
1. ScheduledCollectionTrigger - Timer trigger every 6 hours (replaces Logic App)
2. BlobEventHandler - Blob created events to trigger next pipeline step
3. HealthCheck - Function health monitoring

Cost Benefits:
- Consumption plan: Pay only for execution time
- No Logic App standard pricing (~$200/month)
- More granular control and better Terraform integration
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize function app
app = func.FunctionApp()

# Azure clients (initialized once)
credential = DefaultAzureCredential()
servicebus_namespace = os.environ.get("SERVICE_BUS_NAMESPACE", "")


def create_service_bus_message(
    queue_name: str, payload: Dict[str, Any]
) -> ServiceBusMessage:
    """Create a standardized Service Bus message."""
    message_data = {
        "message_id": func.create_uuid(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "pipeline-orchestrator",
        "queue_name": queue_name,
        "payload": payload,
    }

    message = ServiceBusMessage(
        body=json.dumps(message_data), content_type="application/json"
    )

    message.application_properties = {
        "source": "pipeline-orchestrator",
        "timestamp": message_data["timestamp"],
    }

    return message


def send_service_bus_message(queue_name: str, message: ServiceBusMessage) -> bool:
    """Send message to Service Bus queue."""
    try:
        fully_qualified_namespace = f"{servicebus_namespace}.servicebus.windows.net"

        with ServiceBusClient(
            fully_qualified_namespace=fully_qualified_namespace, credential=credential
        ) as client:
            with client.get_queue_sender(queue_name=queue_name) as sender:
                sender.send_messages(message)

        logger.info(f"Message sent to queue: {queue_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to send message to {queue_name}: {e}")
        return False


@app.timer_trigger(schedule="0 0 */6 * * *", arg_name="timer", run_on_startup=False)
def ScheduledCollectionTrigger(timer: func.TimerRequest) -> None:
    """
    Timer-triggered function for scheduled content collection.

    Runs every 6 hours and sends message to content-collection-requests queue.
    Replaces the Logic App for cost savings and better Terraform integration.
    """
    logger.info("Starting scheduled content collection")

    try:
        # Create collection request payload
        collection_payload = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology", "programming", "science"],
                    "limit": 10,
                }
            ],
            "save_to_storage": True,
            "deduplicate": True,
            "triggered_by": "scheduled_timer",
            "schedule_time": datetime.now(timezone.utc).isoformat(),
        }

        # Create and send Service Bus message
        message = create_service_bus_message(
            queue_name="content-collection-requests", payload=collection_payload
        )

        success = send_service_bus_message("content-collection-requests", message)

        if success:
            logger.info("Scheduled collection request sent successfully")
        else:
            logger.error("Failed to send scheduled collection request")

    except Exception as e:
        logger.error(f"Error in scheduled collection trigger: {e}")


@app.blob_trigger(
    arg_name="blob", path="collected-content/{name}", connection="AzureWebJobsStorage"
)
def BlobEventHandler(blob: func.InputStream) -> None:
    """
    Blob-triggered function for pipeline progression.

    Triggers when blobs are created in storage containers:
    - collected-content/*.json -> triggers content-processing-requests
    - processed-content/*.json -> triggers site-generation-requests
    """
    logger.info(f"Blob trigger fired: {blob.name}")

    try:
        # Parse blob path to determine pipeline step
        container_name = blob.name.split("/")[0] if "/" in blob.name else ""
        file_name = blob.name.split("/")[-1] if "/" in blob.name else blob.name

        # Only process JSON files
        if not file_name.endswith(".json"):
            logger.info(f"Skipping non-JSON file: {file_name}")
            return

        next_queue = None
        payload = {
            "triggered_by": "blob_event",
            "source_blob": blob.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Determine next pipeline step
        if container_name == "collected-content":
            next_queue = "content-processing-requests"
            payload["operation"] = "process_content"
            payload["input_blob"] = blob.name

        elif container_name == "processed-content":
            next_queue = "site-generation-requests"
            payload["operation"] = "generate_site"
            payload["input_blob"] = blob.name

        else:
            logger.info(f"No pipeline step defined for container: {container_name}")
            return

        # Send message to trigger next step
        if next_queue:
            message = create_service_bus_message(queue_name=next_queue, payload=payload)

            success = send_service_bus_message(next_queue, message)

            if success:
                logger.info(f"Pipeline progression: {container_name} -> {next_queue}")
            else:
                logger.error(f"Failed to trigger next step: {next_queue}")

    except Exception as e:
        logger.error(f"Error in blob event handler: {e}")


@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS)
def HealthCheck(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for monitoring."""

    health_data = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "pipeline-orchestrator",
        "version": "1.0.0",
        "environment": {
            "servicebus_namespace": servicebus_namespace,
            "function_app": os.environ.get("WEBSITE_SITE_NAME", "unknown"),
        },
    }

    return func.HttpResponse(
        json.dumps(health_data), status_code=200, mimetype="application/json"
    )
