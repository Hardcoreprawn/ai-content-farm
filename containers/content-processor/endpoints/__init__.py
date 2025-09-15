"""
Content Processor Endpoints Package

Contains all FastAPI router endpoints for the content processor service.
"""

# Import Service Bus router
try:
    from .servicebus_router import router as servicebus_router
except ImportError:
    servicebus_router = None
