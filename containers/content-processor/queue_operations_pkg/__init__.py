"""
Queue operations package.

Pure functional wrappers around Azure Queue Storage operations.

This package provides:
- Message creation functions (pure)
- Queue client operations (async)
- Backward-compatible exports for existing code

For new code, prefer importing directly from:
- queue_operations_pkg.queue_message_builder
- queue_operations_pkg.queue_client_operations
"""

# Import all functions from queue_operations module for backward compatibility
from .queue_operations import (
    clear_queue,
    create_markdown_trigger_message,
    create_queue_message,
    delete_queue_message,
    generate_correlation_id,
    get_queue_properties,
    peek_queue_messages,
    receive_queue_messages,
    send_queue_message,
    should_trigger_next_stage,
    trigger_markdown_for_article,
)

__all__ = [
    "clear_queue",
    "create_markdown_trigger_message",
    "create_queue_message",
    "delete_queue_message",
    "generate_correlation_id",
    "get_queue_properties",
    "peek_queue_messages",
    "receive_queue_messages",
    "send_queue_message",
    "should_trigger_next_stage",
    "trigger_markdown_for_article",
]
