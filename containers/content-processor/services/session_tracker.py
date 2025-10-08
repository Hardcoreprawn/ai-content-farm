"""
Session Tracker Service

Tracks processing session metrics and statistics:
- Topics processed
- Articles generated
- Cost tracking
- Processing time
- Success/failure rates
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class SessionTracker:
    """
    Tracks metrics for a content processing session.

    Immutable append-only tracking for thread safety.
    """

    def __init__(self, processor_id: Optional[str] = None):
        """
        Initialize session tracker.

        Args:
            processor_id: Optional processor identifier
        """
        self.processor_id = processor_id or str(uuid4())[:8]
        self.session_id = str(uuid4())
        self.session_start = datetime.now(timezone.utc)

        # Metrics (append-only for thread safety)
        self.topics_processed = 0
        self.topics_failed = 0
        self.articles_generated = 0
        self.total_cost = 0.0
        self.total_processing_time = 0.0
        self.total_word_count = 0

        # Quality tracking
        self.topic_costs: list[float] = []
        self.topic_processing_times: list[float] = []
        self.topic_word_counts: list[int] = []
        self.quality_scores: list[float] = []
        self.failed_topic_errors: list[str] = []

        logger.info(
            f"📊 SESSION: Started session {self.session_id[:8]} on processor {self.processor_id}"
        )

    def record_topic_success(
        self,
        cost: float = 0.0,
        processing_time: float = 0.0,
        word_count: int = 0,
        quality_score: Optional[float] = None,
    ) -> None:
        """
        Record successful topic processing.

        Args:
            cost: OpenAI API cost for this topic
            processing_time: Processing time in seconds
            word_count: Word count of generated article
            quality_score: Quality assessment score (0-1)
        """
        self.topics_processed += 1
        self.articles_generated += 1
        self.total_cost += cost
        self.total_processing_time += processing_time
        self.total_word_count += word_count

        if quality_score is not None:
            self.quality_scores.append(quality_score)

        logger.debug(
            f"📈 SESSION: Topic success - total: {self.topics_processed}, "
            f"cost: ${self.total_cost:.4f}, words: {self.total_word_count}"
        )

    def record_topic_failure(self, error: Optional[str] = None) -> None:
        """
        Record failed topic processing.

        Args:
            error: Optional error message
        """
        self.topics_failed += 1

        if error:
            logger.debug(f"📉 SESSION: Topic failure - {error}")
        else:
            logger.debug(
                f"📉 SESSION: Topic failure - total failed: {self.topics_failed}"
            )

    def get_session_duration(self) -> float:
        """Get session duration in seconds."""
        return (datetime.now(timezone.utc) - self.session_start).total_seconds()

    def get_average_quality(self) -> Optional[float]:
        """Get average quality score."""
        if not self.quality_scores:
            return None
        return sum(self.quality_scores) / len(self.quality_scores)

    def get_success_rate(self) -> float:
        """Get success rate as a percentage."""
        total_attempts = self.topics_processed + self.topics_failed
        if total_attempts == 0:
            return 0.0
        return (self.topics_processed / total_attempts) * 100

    def get_stats(self) -> Dict:
        """
        Get comprehensive session statistics.

        Returns:
            Dict with session metrics
        """
        session_duration = self.get_session_duration()
        avg_quality = self.get_average_quality()
        success_rate = self.get_success_rate()

        return {
            "session_id": self.session_id,
            "processor_id": self.processor_id,
            "session_start": self.session_start.isoformat(),
            "session_duration_seconds": round(session_duration, 2),
            "topics_processed": self.topics_processed,
            "topics_failed": self.topics_failed,
            "articles_generated": self.articles_generated,
            "total_cost": round(self.total_cost, 6),
            "total_word_count": self.total_word_count,
            "average_quality_score": round(avg_quality, 3) if avg_quality else None,
            "success_rate_percent": round(success_rate, 1),
            "average_processing_time_seconds": (
                round(self.total_processing_time / self.topics_processed, 2)
                if self.topics_processed > 0
                else 0
            ),
            "cost_per_article": (
                round(self.total_cost / self.articles_generated, 6)
                if self.articles_generated > 0
                else 0
            ),
            "words_per_article": (
                round(self.total_word_count / self.articles_generated, 0)
                if self.articles_generated > 0
                else 0
            ),
        }

    def log_summary(self) -> None:
        """Log session summary."""
        stats = self.get_stats()

        logger.info("=" * 60)
        logger.info(f"📊 SESSION SUMMARY - {self.session_id[:8]}")
        logger.info("=" * 60)
        logger.info(f"Duration: {stats['session_duration_seconds']}s")
        logger.info(f"Topics Processed: {stats['topics_processed']}")
        logger.info(f"Topics Failed: {stats['topics_failed']}")
        logger.info(f"Success Rate: {stats['success_rate_percent']}%")
        logger.info(f"Articles Generated: {stats['articles_generated']}")
        logger.info(f"Total Cost: ${stats['total_cost']:.4f}")
        logger.info(f"Cost per Article: ${stats['cost_per_article']:.4f}")
        logger.info(f"Total Words: {stats['total_word_count']}")
        logger.info(f"Words per Article: {stats['words_per_article']}")

        if stats["average_quality_score"]:
            logger.info(f"Average Quality: {stats['average_quality_score']}")

        logger.info("=" * 60)
