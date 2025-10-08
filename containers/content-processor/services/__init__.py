"""
Services module for content processor.

Provides modular services extracted from the main processor:
- ArticleGenerationService: OpenAI integration and article creation
- LeaseCoordinator: Topic locking and coordination for parallel processing
- ProcessorStorageService: Storage operations and article saving
- TopicConversionService: Legacy collection item conversion (for backward compatibility)
- QueueCoordinator: Queue message coordination for pipeline stages
- SessionTracker: Session metrics and statistics tracking

NOTE: TopicDiscoveryService was removed as part of the architecture pivot to
single-topic processing (October 2025). TopicConversionService is kept for
backward compatibility with legacy batch processing.
"""

from .article_generation import ArticleGenerationService
from .lease_coordinator import LeaseCoordinator
from .processor_storage import ProcessorStorageService
from .queue_coordinator import QueueCoordinator
from .session_tracker import SessionTracker
from .topic_conversion import TopicConversionService

__all__ = [
    "ArticleGenerationService",
    "LeaseCoordinator",
    "ProcessorStorageService",
    "QueueCoordinator",
    "SessionTracker",
    "TopicConversionService",
]
