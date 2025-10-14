"""
Data models and schemas.

Pydantic models for domain objects, API requests/responses, and metadata.
"""

# Import API models and metadata first (wildcard imports)
from .api_models import *  # noqa: F401, F403
from .metadata import *  # noqa: F401, F403

# Import functional models last to ensure they take precedence over any naming conflicts
from .models import ProcessingResult  # Overrides api_models.ProcessingResult
from .models import (
    ProcessBatchRequest,
    ProcessingAttempt,
    ProcessorStatus,
    ProcessTopicRequest,
    TopicMetadata,
    TopicProcessingResult,
    TopicState,
    WakeUpRequest,
    WakeUpResponse,
)

__all__ = [
    "ProcessingResult",  # Functional model (from models.py, not api_models.py)
    "ProcessorStatus",
    "TopicMetadata",
    "WakeUpRequest",
    "WakeUpResponse",
    "ProcessTopicRequest",
    "ProcessBatchRequest",
    "ProcessingAttempt",
    "TopicState",
    "TopicProcessingResult",
]
