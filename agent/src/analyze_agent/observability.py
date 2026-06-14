"""Structured logging, correlation context, and process-local metrics."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from threading import Lock
from typing import Any

_CORRELATION_CONTEXT: ContextVar[dict[str, str] | None] = ContextVar(
    "analyze_agent_correlation_context",
    default=None,
)
_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "token",
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **(_CORRELATION_CONTEXT.get() or {}),
        }
        event_fields = getattr(record, "event_fields", None)
        if isinstance(event_fields, Mapping):
            payload.update(_redact(dict(event_fields)))
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=True, default=str)


def configure_logging(log_level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)


def log_event(
    logger: logging.Logger,
    event: str,
    **fields: Any,
) -> None:
    logger.info(event, extra={"event_fields": fields})


@contextmanager
def bind_correlation(**values: str) -> Iterator[None]:
    current = dict(_CORRELATION_CONTEXT.get() or {})
    current.update({key: value for key, value in values.items() if value})
    token = _CORRELATION_CONTEXT.set(current)
    try:
        yield
    finally:
        _CORRELATION_CONTEXT.reset(token)


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._observations: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._observations[name].append(value)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "observations": {
                    name: list(values)
                    for name, values in self._observations.items()
                },
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._observations.clear()


METRICS = MetricsRegistry()


def _redact(value: Any, *, key: str = "") -> Any:
    if any(part in key.casefold() for part in _SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(item_key): _redact(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact(item) for item in value]
    return value
