import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from analyze_agent import (
    AnalyzeResponse,
    ConfigurationError,
    DemoKnowledgeScenario,
    RequirementRevision,
    RequirementSummary,
    StageEvent,
    StageStatus,
    WorkflowStage,
)
from fastapi.testclient import TestClient

from analyze_api import create_app
from analyze_api.config import ApiSettings


def _response(request_id: UUID, requirement_id: UUID | None = None) -> AnalyzeResponse:
    return AnalyzeResponse.model_validate(
        {
            "request_id": str(request_id),
            "requirement_id": str(requirement_id or uuid4()),
            "revision_id": str(uuid4()),
            "analyzed_requirement": {
                "summary": "Build an ADC review GDA.",
                "business_goal": "Support ADC review.",
            },
            "clear_fields": [],
            "keywords": [],
            "reused_mappings": [],
            "warnings": [],
            "trace": {
                "prompt_version": "test-v1",
                "model": "fake",
                "knowledge_base_queries": [],
                "processing_time_ms": 1,
            },
        }
    )


class FakeAgent:
    def __init__(self, scenario: DemoKnowledgeScenario) -> None:
        self.scenario = scenario

    async def analyze_initial(self, request, *, event_sink, job_id):
        event_sink.emit(
            StageEvent(
                job_id=job_id,
                request_id=request.request_id,
                stage=WorkflowStage.ANALYZING_REQUIREMENT,
                status=StageStatus.COMPLETED,
                sequence=1,
                timestamp=datetime.now(UTC),
                duration_ms=1,
            )
        )
        await asyncio.sleep(0)
        return _response(request.request_id)

    async def analyze_update(self, request, *, event_sink, job_id):
        await asyncio.sleep(0)
        return _response(request.request_id, request.requirement_id)


class RecordingFactory:
    def __init__(self) -> None:
        self.scenarios: list[DemoKnowledgeScenario] = []

    def __call__(self, scenario: DemoKnowledgeScenario) -> FakeAgent:
        self.scenarios.append(scenario)
        return FakeAgent(scenario)


class FailingFactory:
    def __call__(self, scenario: DemoKnowledgeScenario) -> FakeAgent:
        del scenario
        raise ConfigurationError("secret configuration detail")


class FakeHistory:
    requirement_id = uuid4()
    revision_id = uuid4()

    def list_requirements(self) -> list[RequirementSummary]:
        now = datetime.now(UTC)
        return [
            RequirementSummary(
                requirement_id=self.requirement_id,
                latest_revision_number=1,
                summary="Build an ADC review GDA.",
                created_at=now,
                updated_at=now,
            )
        ]

    def get_latest_revision(self, requirement_id: UUID) -> RequirementRevision:
        assert requirement_id == self.requirement_id
        return self._revision()

    def list_revisions(self, requirement_id: UUID) -> list[RequirementRevision]:
        return [self.get_latest_revision(requirement_id)]

    def _revision(self) -> RequirementRevision:
        return RequirementRevision(
            requirement_id=self.requirement_id,
            revision_id=self.revision_id,
            revision_number=1,
            full_requirement="Build an ADC review GDA.",
            created_at=datetime.now(UTC),
        )


def _client(factory=None) -> TestClient:
    return TestClient(
        create_app(
            agent_factory=factory or RecordingFactory(),
            history_factory=FakeHistory,
            settings=ApiSettings(event_poll_seconds=0.001),
        )
    )


def _wait_for_terminal(client: TestClient, job_id: str) -> dict:
    for _ in range(100):
        payload = client.get(f"/api/v1/jobs/{job_id}").json()
        if payload["status"] in {"completed", "failed"}:
            return payload
    raise AssertionError("Job did not reach a terminal state.")


def test_health_and_versioned_openapi() -> None:
    with _client() as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/v1/openapi.json").status_code == 200


def test_initial_job_returns_result_and_replayable_sse() -> None:
    with _client() as client:
        submission = client.post(
            "/api/v1/jobs/initial",
            json={
                "requirement": "Build an ADC review GDA.",
                "knowledge_base_scenario": "complete_mapping",
            },
        )
        assert submission.status_code == 202
        job_id = submission.json()["job_id"]

        result = _wait_for_terminal(client, job_id)
        assert result["status"] == "completed"
        assert result["result"]["analyzed_requirement"]["summary"]

        events = client.get(f"/api/v1/jobs/{job_id}/events")
        assert events.status_code == 200
        assert "event: stage" in events.text
        assert "event: job" in events.text
        assert '"stage":"analyzing_requirement"' in events.text


def test_concurrent_jobs_keep_scenarios_isolated() -> None:
    factory = RecordingFactory()
    with _client(factory) as client:
        first = client.post(
            "/api/v1/jobs/initial",
            json={
                "requirement": "Build an ADC review GDA.",
                "knowledge_base_scenario": "empty",
            },
        ).json()
        second = client.post(
            "/api/v1/jobs/initial",
            json={
                "requirement": "Build a Basel review GDA.",
                "knowledge_base_scenario": "partial_mapping",
            },
        ).json()
        _wait_for_terminal(client, first["job_id"])
        _wait_for_terminal(client, second["job_id"])

    assert factory.scenarios == [
        DemoKnowledgeScenario.EMPTY,
        DemoKnowledgeScenario.PARTIAL_MAPPING,
    ]


def test_configuration_failure_is_safe() -> None:
    with _client(FailingFactory()) as client:
        submission = client.post(
            "/api/v1/jobs/initial",
            json={"requirement": "Build an ADC review GDA."},
        ).json()
        result = _wait_for_terminal(client, submission["job_id"])

    assert result["status"] == "failed"
    assert result["error"] == {
        "code": "configuration_error",
        "message": "Gemini API key is not configured.",
    }


def test_update_job_uses_existing_requirement_id() -> None:
    requirement_id = uuid4()
    with _client() as client:
        submission = client.post(
            "/api/v1/jobs/update",
            json={
                "requirement_id": str(requirement_id),
                "supplemental_information": "Include ADC entity country.",
            },
        )
        result = _wait_for_terminal(client, submission.json()["job_id"])

    assert submission.status_code == 202
    assert result["status"] == "completed"
    assert result["result"]["requirement_id"] == str(requirement_id)


def test_validation_and_missing_jobs_use_stable_error_shape() -> None:
    with _client() as client:
        invalid = client.post("/api/v1/jobs/initial", json={"requirement": ""})
        missing = client.get(f"/api/v1/jobs/{uuid4()}")

    assert invalid.status_code == 422
    assert invalid.json() == {
        "error": {
            "code": "validation_error",
            "message": "Request payload failed validation.",
        }
    }
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "job_not_found"


def test_history_endpoints_use_public_history_facade() -> None:
    with _client() as client:
        items = client.get("/api/v1/requirements").json()
        requirement_id = items[0]["requirement_id"]

        latest = client.get(
            f"/api/v1/requirements/{requirement_id}/latest"
        )
        revisions = client.get(
            f"/api/v1/requirements/{requirement_id}/revisions"
        )

    assert latest.status_code == 200
    assert latest.json()["revision_number"] == 1
    assert len(revisions.json()) == 1
