"""
Tests for shared HTTP client utility.

Ensures proper session lifecycle, connection pooling, and cleanup.
"""

import pytest

from libs.http_client import close_http_session, get_http_session, reset_http_session


@pytest.mark.asyncio
async def test_get_http_session_creates_new_session():
    """Test that get_http_session creates a new session on first call."""
    await reset_http_session()  # Ensure clean state

    session = await get_http_session()

    assert session is not None
    assert not session.closed

    await close_http_session()


@pytest.mark.asyncio
async def test_get_http_session_reuses_existing_session():
    """Test that get_http_session returns the same session on multiple calls."""
    await reset_http_session()

    session1 = await get_http_session()
    session2 = await get_http_session()

    assert session1 is session2
    assert not session1.closed

    await close_http_session()


@pytest.mark.asyncio
async def test_close_http_session_closes_session():
    """Test that close_http_session properly closes the session."""
    await reset_http_session()

    session = await get_http_session()
    assert not session.closed

    await close_http_session()
    assert session.closed


@pytest.mark.asyncio
async def test_get_http_session_recreates_after_close():
    """Test that get_http_session creates new session after close."""
    await reset_http_session()

    session1 = await get_http_session()
    session1_id = id(session1)

    await close_http_session()
    assert session1.closed

    session2 = await get_http_session()
    session2_id = id(session2)

    assert session2_id != session1_id
    assert not session2.closed

    await close_http_session()


@pytest.mark.asyncio
async def test_reset_http_session_forces_new_session():
    """Test that reset_http_session forces creation of new session."""
    await reset_http_session()

    session1 = await get_http_session()
    session1_id = id(session1)

    await reset_http_session()

    session2 = await get_http_session()
    session2_id = id(session2)

    assert session2_id != session1_id

    await close_http_session()


@pytest.mark.asyncio
async def test_http_session_has_timeout_configured():
    """Test that HTTP session has timeout configuration."""
    await reset_http_session()

    session = await get_http_session(timeout=15.0)

    assert session.timeout.total == 15.0

    await close_http_session()


@pytest.mark.asyncio
async def test_http_session_has_user_agent():
    """Test that HTTP session has User-Agent header configured."""
    await reset_http_session()

    session = await get_http_session()

    assert "User-Agent" in session.headers
    assert "ai-content-farm" in session.headers["User-Agent"]

    await close_http_session()


@pytest.mark.asyncio
async def test_multiple_close_calls_are_safe():
    """Test that calling close_http_session multiple times is safe."""
    await reset_http_session()

    await get_http_session()

    # Should not raise exception
    await close_http_session()
    await close_http_session()
    await close_http_session()


@pytest.mark.asyncio
async def test_close_without_session_is_safe():
    """Test that closing without creating a session is safe."""
    await reset_http_session()

    # Should not raise exception
    await close_http_session()
