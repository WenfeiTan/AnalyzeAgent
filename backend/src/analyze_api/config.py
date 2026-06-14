"""Environment-backed settings owned by the HTTP Backend."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApiSettings:
    allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    max_jobs: int = 100
    max_events_per_job: int = 200
    event_poll_seconds: float = 0.05

    @classmethod
    def from_environment(cls) -> ApiSettings:
        origins = tuple(
            item.strip()
            for item in os.getenv(
                "ANALYZE_API_ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if item.strip()
        )
        return cls(
            allowed_origins=origins,
            max_jobs=_positive_int("ANALYZE_API_MAX_JOBS", 100),
            max_events_per_job=_positive_int(
                "ANALYZE_API_MAX_EVENTS_PER_JOB",
                200,
            ),
            event_poll_seconds=_positive_float(
                "ANALYZE_API_EVENT_POLL_SECONDS",
                0.05,
            ),
        )


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _positive_float(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value
