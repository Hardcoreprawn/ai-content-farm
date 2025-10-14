"""
Backward compatibility module for queue operations.

This module re-exports all functions from the split modules to maintain
existing import paths while keeping individual files under 400 lines.

For new code, prefer importing directly from:
- queue_operations_pkg.queue_message_builder: Message creation functions
- queue_operations_pkg.queue_client_operations: Queue client operations
"""

# Queue client operations
from queue_operations_pkg.queue_client_operations import (
    clear_queue,
    delete_queue_message,
    get_queue_properties,
    peek_queue_messages,
    receive_queue_messages,
    send_queue_message,
    trigger_markdown_for_article,
)

# Message creation functions
from queue_operations_pkg.queue_message_builder import (
    create_markdown_trigger_message,
    create_queue_message,
    generate_correlation_id,
    should_trigger_next_stage,
)

__all__ = [
    # Message builders
    "create_queue_message",
    "generate_correlation_id",
    "create_markdown_trigger_message",
    "should_trigger_next_stage",
    # Queue operations
    "send_queue_message",
    "receive_queue_messages",
    "delete_queue_message",
    "peek_queue_messages",
    "get_queue_properties",
    "clear_queue",
    "trigger_markdown_for_article",
]
