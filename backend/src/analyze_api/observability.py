"""Process-local Web job metrics and safe operational logging."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime
from threading import Lock
from typing import Any

_LOGGER = logging.getLogger("analyze_api.jobs")


class WebJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        fields = getattr(record, "event_fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        return json.dumps(payload, ensure_ascii=True, default=str)


def configure_web_observability(log_level: str) -> None:
    if not _LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(WebJsonFormatter())
        _LOGGER.addHandler(handler)
    _LOGGER.setLevel(log_level)
    _LOGGER.propagate = False


class WebMetrics:
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


def log_job_event(event: str, **fields: Any) -> None:
    _LOGGER.info(event, extra={"event_fields": fields})
