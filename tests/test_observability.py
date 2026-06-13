import json
import logging

from analyze_agent.observability import (
    METRICS,
    JsonLogFormatter,
    bind_correlation,
)


def test_json_logs_include_context_and_redact_secrets() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="operation.completed",
        args=(),
        exc_info=None,
    )
    record.event_fields = {
        "duration_ms": 12,
        "api_key": "super-secret",
        "nested": {"authorization": "Bearer secret"},
    }

    with bind_correlation(request_id="request-1", revision_id="revision-1"):
        payload = json.loads(JsonLogFormatter().format(record))

    assert payload["request_id"] == "request-1"
    assert payload["revision_id"] == "revision-1"
    assert payload["api_key"] == "[REDACTED]"
    assert payload["nested"]["authorization"] == "[REDACTED]"
    assert "super-secret" not in json.dumps(payload)


def test_metrics_registry_tracks_counts_and_observations() -> None:
    METRICS.reset()

    METRICS.increment("tool_calls.test")
    METRICS.observe("tool_duration_ms.test", 3.5)

    snapshot = METRICS.snapshot()
    assert snapshot["counters"]["tool_calls.test"] == 1
    assert snapshot["observations"]["tool_duration_ms.test"] == [3.5]

