"""
Azure Storage Queue SDK-Level Mocks

Provides comprehensive mocking that closely matches the Azure Storage Queue SDK
interface, using JSON-based data structures instead of the underlying REST API XML.

Based on Azure Storage Queue REST API 2023-11-03 spec and Python SDK documentation.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock

from pydantic import BaseModel, Field


class MockQueueMessage(BaseModel):
    """Mock implementation of azure.storage.queue.QueueMessage.

    Matches the Azure SDK QueueMessage interface exactly for realistic testing.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None
    pop_receipt: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    inserted_on: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_on: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=7)
    )
    next_visible_on: Optional[datetime] = None
    dequeue_count: Optional[int] = 1

    class Config:
        arbitrary_types_allowed = True

    def get(self, key: str, default=None):
        """Dict-like interface for backward compatibility."""
        return getattr(self, key, default)

    def has_key(self, key: str) -> bool:
        """Dict-like interface for backward compatibility."""
        return hasattr(self, key)

    def items(self):
        """Dict-like interface for backward compatibility."""
        return self.__dict__.items()

    def keys(self):
        """Dict-like interface for backward compatibility."""
        return self.__dict__.keys()

    def values(self):
        """Dict-like interface for backward compatibility."""
        return self.__dict__.values()


class MockQueueProperties(BaseModel):
    """Mock implementation of azure.storage.queue.QueueProperties."""

    name: str
    approximate_message_count: int = 0
    metadata: Dict[str, str] = Field(default_factory=dict)
    last_modified: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    etag: str = Field(default_factory=lambda: f'"{uuid.uuid4()}"')


class MockSendMessageResponse(BaseModel):
    """Mock response from send_message operation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pop_receipt: str = Field(default_factory=lambda: str(uuid.uuid4()))
    time_next_visible: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    insertion_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiration_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=7)
    )


class MockQueueClient:
    """
    Mock implementation of azure.storage.queue.aio.QueueClient.

    Provides SDK-level mocking that matches the Azure Python SDK interface exactly,
    using JSON-based data structures for realistic testing without Azure dependencies.
    """

    def __init__(self, account_url: str, queue_name: str, credential=None, **kwargs):
        """Initialize mock queue client to match Azure SDK constructor."""
        self.account_url = account_url
        self.queue_name = queue_name
        self.credential = credential
        self._connected = False
        self._messages: List[MockQueueMessage] = []
        self._queue_exists = False
        self._metadata: Dict[str, str] = {}

        # Track API calls for testing
        self.call_history: List[Dict[str, Any]] = []

    def _log_call(self, method: str, **kwargs):
        """Log API calls for test verification."""
        self.call_history.append(
            {
                "method": method,
                "timestamp": datetime.now(timezone.utc),
                "kwargs": kwargs,
            }
        )

    async def create_queue(
        self,
        *,
        metadata: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> None:
        """Create queue - matches Azure SDK signature."""
        self._log_call("create_queue", metadata=metadata, timeout=timeout)

        if self._queue_exists:
            from azure.core.exceptions import ResourceExistsError

            raise ResourceExistsError("Queue already exists")

        self._queue_exists = True
        if metadata:
            self._metadata.update(metadata)

    async def delete_queue(self, *, timeout: Optional[int] = None, **kwargs) -> None:
        """Delete queue - matches Azure SDK signature."""
        self._log_call("delete_queue", timeout=timeout)

        if not self._queue_exists:
            from azure.core.exceptions import ResourceNotFoundError

            raise ResourceNotFoundError("Queue not found")

        self._queue_exists = False
        self._messages.clear()
        self._metadata.clear()

    async def send_message(
        self,
        content: Any,
        *,
        visibility_timeout: Optional[int] = None,
        time_to_live: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> MockQueueMessage:
        """Send message - matches Azure SDK signature exactly."""
        self._log_call(
            "send_message",
            content=content,
            visibility_timeout=visibility_timeout,
            time_to_live=time_to_live,
            timeout=timeout,
        )

        if not self._queue_exists:
            await self.create_queue()

        # Handle JSON content
        if isinstance(content, (dict, list)):
            content = json.dumps(content)

        # Calculate visibility and expiration times
        now = datetime.now(timezone.utc)
        next_visible = now
        if visibility_timeout:
            next_visible = now + timedelta(seconds=visibility_timeout)

        expires_on = now + timedelta(days=7)  # Default 7-day TTL
        if time_to_live:
            if time_to_live == -1:  # Infinity
                expires_on = now + timedelta(days=365)  # 1 year as "infinity"
            else:
                expires_on = now + timedelta(seconds=time_to_live)

        message = MockQueueMessage(
            content=content,
            next_visible_on=next_visible,
            expires_on=expires_on,
            dequeue_count=0,  # Not yet received
        )

        self._messages.append(message)
        return message

    async def receive_messages(
        self,
        *,
        messages_per_page: Optional[int] = None,
        visibility_timeout: Optional[int] = None,
        max_messages: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> List[MockQueueMessage]:
        """Receive messages - matches Azure SDK signature."""
        self._log_call(
            "receive_messages",
            messages_per_page=messages_per_page,
            visibility_timeout=visibility_timeout,
            max_messages=max_messages,
            timeout=timeout,
        )

        if not self._queue_exists:
            return []

        now = datetime.now(timezone.utc)

        # Find visible messages (not expired, visibility timeout passed)
        visible_messages = [
            msg
            for msg in self._messages
            if (not msg.next_visible_on or msg.next_visible_on <= now)
            and (not msg.expires_on or msg.expires_on > now)
        ]

        # Limit number of messages
        limit = max_messages or messages_per_page or 32  # Azure default is 32
        messages_to_return = visible_messages[:limit]

        # Update message properties for received messages
        visibility_delta = timedelta(seconds=visibility_timeout or 30)  # Default 30s
        for msg in messages_to_return:
            msg.dequeue_count = (msg.dequeue_count or 0) + 1
            msg.next_visible_on = now + visibility_delta
            msg.pop_receipt = str(uuid.uuid4())  # New pop receipt

        return messages_to_return

    async def receive_message(
        self,
        *,
        visibility_timeout: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Optional[MockQueueMessage]:
        """Receive single message - matches Azure SDK signature."""
        messages = await self.receive_messages(
            max_messages=1,
            visibility_timeout=visibility_timeout,
            timeout=timeout,
            **kwargs,
        )
        return messages[0] if messages else None

    async def peek_messages(
        self,
        max_messages: Optional[int] = None,
        *,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> List[MockQueueMessage]:
        """Peek messages without affecting visibility - matches Azure SDK signature."""
        self._log_call("peek_messages", max_messages=max_messages, timeout=timeout)

        if not self._queue_exists:
            return []

        now = datetime.now(timezone.utc)

        # Find visible messages (but don't modify them)
        visible_messages = [
            msg
            for msg in self._messages
            if (not msg.next_visible_on or msg.next_visible_on <= now)
            and (not msg.expires_on or msg.expires_on > now)
        ]

        limit = max_messages or 1
        return visible_messages[:limit]

    async def delete_message(
        self,
        message: Union[str, MockQueueMessage],
        pop_receipt: Optional[str] = None,
        *,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> None:
        """Delete message - matches Azure SDK signature."""
        if isinstance(message, MockQueueMessage):
            message_id = message.id
            receipt = message.pop_receipt
        else:
            message_id = message
            receipt = pop_receipt

        self._log_call(
            "delete_message",
            message_id=message_id,
            pop_receipt=receipt,
            timeout=timeout,
        )

        # Find and remove message
        for i, msg in enumerate(self._messages):
            if msg.id == message_id:
                if receipt and msg.pop_receipt != receipt:
                    from azure.core.exceptions import HttpResponseError

                    raise HttpResponseError("Invalid pop receipt")

                del self._messages[i]
                return

        # Message not found
        from azure.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("Message not found")

    async def update_message(
        self,
        message: Union[str, MockQueueMessage],
        pop_receipt: Optional[str] = None,
        content: Optional[Any] = None,
        *,
        visibility_timeout: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> MockQueueMessage:
        """Update message - matches Azure SDK signature."""
        if isinstance(message, MockQueueMessage):
            message_id = message.id
            receipt = message.pop_receipt
        else:
            message_id = message
            receipt = pop_receipt

        self._log_call(
            "update_message",
            message_id=message_id,
            content=content,
            visibility_timeout=visibility_timeout,
            timeout=timeout,
        )

        # Find message
        for msg in self._messages:
            if msg.id == message_id:
                if receipt and msg.pop_receipt != receipt:
                    from azure.core.exceptions import HttpResponseError

                    raise HttpResponseError("Invalid pop receipt")

                # Update message
                if content is not None:
                    if isinstance(content, (dict, list)):
                        content = json.dumps(content)
                    msg.content = content

                if visibility_timeout is not None:
                    now = datetime.now(timezone.utc)
                    msg.next_visible_on = now + timedelta(seconds=visibility_timeout)

                # Generate new pop receipt
                msg.pop_receipt = str(uuid.uuid4())
                return msg

        from azure.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("Message not found")

    async def clear_messages(self, *, timeout: Optional[int] = None, **kwargs) -> None:
        """Clear all messages - matches Azure SDK signature."""
        self._log_call("clear_messages", timeout=timeout)
        self._messages.clear()

    async def get_queue_properties(
        self, *, timeout: Optional[int] = None, **kwargs
    ) -> MockQueueProperties:
        """Get queue properties - matches Azure SDK signature."""
        self._log_call("get_queue_properties", timeout=timeout)

        if not self._queue_exists:
            from azure.core.exceptions import ResourceNotFoundError

            raise ResourceNotFoundError("Queue not found")

        return MockQueueProperties(
            name=self.queue_name,
            approximate_message_count=len(self._messages),
            metadata=self._metadata.copy(),
        )

    async def set_queue_metadata(
        self,
        metadata: Optional[Dict[str, str]] = None,
        *,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Set queue metadata - matches Azure SDK signature."""
        self._log_call("set_queue_metadata", metadata=metadata, timeout=timeout)

        if not self._queue_exists:
            from azure.core.exceptions import ResourceNotFoundError

            raise ResourceNotFoundError("Queue not found")

        if metadata:
            self._metadata.update(metadata)

        return {
            "etag": f'"{uuid.uuid4()}"',
            "last_modified": datetime.now(timezone.utc),
        }

    async def close(self) -> None:
        """Close client - matches Azure SDK signature."""
        self._log_call("close")
        self._connected = False

    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        self._connected = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # Properties to match Azure SDK
    @property
    def url(self) -> str:
        """Full endpoint URL - matches Azure SDK property."""
        return f"{self.account_url}/{self.queue_name}"

    @property
    def primary_endpoint(self) -> str:
        """Primary endpoint URL - matches Azure SDK property."""
        return self.account_url

    @property
    def queue_name_property(self) -> str:
        """Queue name property - matches Azure SDK."""
        return self.queue_name


# Convenience functions for easy test setup
def create_mock_queue_client(
    queue_name: str = "test-queue", account_name: str = "test-account"
) -> MockQueueClient:
    """Create a mock queue client for testing."""
    account_url = f"https://{account_name}.queue.core.windows.net"
    return MockQueueClient(account_url=account_url, queue_name=queue_name)


async def setup_mock_queue_with_messages(
    queue_name: str = "test-queue",
    messages: Optional[List[Union[str, Dict[str, Any]]]] = None,
) -> MockQueueClient:
    """Create a mock queue client with pre-populated messages."""
    client = create_mock_queue_client(queue_name)
    await client.create_queue()

    if messages:
        for msg in messages:
            await client.send_message(msg)

    return client


# Mock exception classes for completeness
class MockResourceExistsError(Exception):
    """Mock Azure ResourceExistsError."""

    pass


class MockResourceNotFoundError(Exception):
    """Mock Azure ResourceNotFoundError."""

    pass


class MockHttpResponseError(Exception):
    """Mock Azure HttpResponseError."""

    pass


# Patch helper for tests
def patch_azure_queue_client():
    """
    Decorator/context manager to patch Azure Storage Queue client with mocks.

    Usage:
        @patch_azure_queue_client()
        async def test_my_function():
            # Your test code here
            pass
    """
    from unittest.mock import patch

    def decorator(func):
        return patch("azure.storage.queue.aio.QueueClient", MockQueueClient)(func)

    return decorator
