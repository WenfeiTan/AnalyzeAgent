"""Bounded timeout and retry helpers for asynchronous external calls."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    timeout_seconds: float
    max_attempts: int
    base_delay_seconds: float = 0.05


async def call_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy,
    is_retryable: Callable[[BaseException], bool],
) -> T:
    last_error: BaseException | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await asyncio.wait_for(
                operation(),
                timeout=policy.timeout_seconds,
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            last_error = error
            if attempt >= policy.max_attempts or not is_retryable(error):
                raise
            await asyncio.sleep(policy.base_delay_seconds * attempt)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Retry loop completed without a result or error.")
