"""Check the local Backend endpoints used by the demo UI."""

from __future__ import annotations

import json
import os
from urllib.request import urlopen

BASE_URL = os.getenv("ANALYZE_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _get(path: str) -> dict:
    with urlopen(f"{BASE_URL}{path}", timeout=5) as response:  # noqa: S310
        return json.load(response)


def main() -> None:
    health = _get("/health")
    configuration = _get("/api/v1/configuration")
    metrics = _get("/api/v1/metrics")
    if health != {"status": "ok"}:
        raise RuntimeError(f"Unexpected health response: {health}")
    if configuration.get("knowledge_base_provider") != "fake":
        raise RuntimeError("Demo Backend is not using the Fake Knowledge Base.")
    if "counters" not in metrics or "observations" not in metrics:
        raise RuntimeError("Metrics response is incomplete.")
    print(
        "Smoke test passed: Backend healthy, configuration readable, "
        "Fake Knowledge Base explicit, metrics available."
    )


if __name__ == "__main__":
    main()
