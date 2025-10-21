"""
Rate limiting utilities with async-compatible fallback.

Provides optional rate limiting with graceful fallback when aiolimiter
is not available (e.g., in test/dev environments).
"""

from typing import Any, Optional, Type

# aiolimiter may not be installed in some environments (dev/test); provide a
# lightweight no-op fallback to keep type hints and optional rate limiting.
try:
    from aiolimiter import AsyncLimiter  # type: ignore[import]

except ImportError:  # pragma: no cover - fallback for environments without aiolimiter

    class AsyncLimiter:  # type: ignore[no-redef]
        """Minimal async-compatible no-op fallback for aiolimiter.AsyncLimiter."""

        def __init__(self, max_rate: int = 1, time_period: float = 1.0) -> None:
            self.max_rate = max_rate
            self.time_period = time_period

        async def __aenter__(self) -> "AsyncLimiter":
            return self

        async def __aexit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc: Optional[BaseException],
            tb: Optional[Any],
        ) -> bool:
            return False

        async def acquire(self) -> None:
            # No-op acquire for compatibility
            return None


__all__ = ["AsyncLimiter"]
