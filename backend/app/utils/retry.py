"""Exponential-backoff retry helper for async functions."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay_seconds: float = 2.0,
) -> T:
    """Execute *fn* with exponential backoff on failure.

    Parameters
    ----------
    fn:
        An async callable (zero-args) to attempt.
    retries:
        Maximum number of retry attempts after the initial call.
    base_delay_seconds:
        Delay before the first retry; doubled on each subsequent retry.

    Returns
    -------
    The return value of *fn* on the first successful invocation.

    Raises
    ------
    Exception
        Re-raises the last exception if all attempts fail.
    """

    last_exc: Exception | None = None

    for attempt in range(retries + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                delay = base_delay_seconds * (2 ** attempt)
                logger.warning(
                    "Attempt %d/%d failed (%s). Retrying in %.1fs …",
                    attempt + 1,
                    retries + 1,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "All %d attempts exhausted. Last error: %s",
                    retries + 1,
                    exc,
                )

    raise last_exc  # type: ignore[misc]
