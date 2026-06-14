import asyncio
from pathlib import Path

from analyze_agent import (
    AnalyzeAgent,
    AnalyzeAgentHistory,
    DemoKnowledgeScenario,
    Settings,
    build_runtime,
    load_demo_scenario,
)
from analyze_agent.adapters.fake_knowledge_retriever import (
    FakeKnowledgeBaseRetriever,
)
from analyze_agent.domain.models import (
    AnalyzedRequirement,
    AssetReference,
    AttributeReference,
    ChangeAction,
    FieldAnalysisSignal,
    KeywordAnalysisSignal,
    KeywordStrength,
    KnowledgeMappingCandidate,
    KnowledgeReuseSignals,
    RequirementAnalysisSignals,
    RequirementChange,
    RequirementUpdateSignals,
    SourceAttributeMapping,
)
from fastapi.testclient import TestClient

from analyze_api import create_app
from analyze_api.config import ApiSettings


class DeterministicAnalyzer:
    async def analyze(self, requirement: str) -> RequirementAnalysisSignals:
        fields = [
            name
            for name in ("Facility_id", "ADC_entity_country")
            if name.casefold() in requirement.casefold()
        ]
        return RequirementAnalysisSignals(
            analyzed_requirement=AnalyzedRequirement(
                summary=requirement,
                business_goal="Support the updated ADC review.",
                domain_context=["ADC", "Basel 3"],
            ),
            clear_fields=[
                FieldAnalysisSignal(
                    name=name,
                    requirement_excerpt=name,
                )
                for name in fields
            ],
            keywords=[
                KeywordAnalysisSignal(
                    name="ADC",
                    strength=KeywordStrength.CORE,
                    rationale="Core review domain.",
                ),
                KeywordAnalysisSignal(
                    name="Basel 3",
                    strength=KeywordStrength.CORE,
                    rationale="Regulatory context.",
                ),
            ],
        )


class DeterministicUpdater:
    async def update(
        self,
        *,
        previous_requirement,
        supplemental_information,
        feedback,
        previous_output,
    ) -> RequirementUpdateSignals:
        del previous_output
        additions = [supplemental_information] if supplemental_information else []
        additions.extend(
            item.field_name
            for item in feedback
            if item.field_name and item.field_name not in previous_requirement
        )
        updated = " ".join([previous_requirement, *additions]).strip()
        return RequirementUpdateSignals(
            full_requirement=updated,
            changes=[
                RequirementChange(
                    action=ChangeAction.ADD,
                    target=item,
                    after=item,
                )
                for item in additions
            ],
        )


class DeterministicReconstructor:
    async def reconstruct(self, *, chunks, **kwargs) -> KnowledgeReuseSignals:
        del kwargs
        if not any(
            chunk.metadata.get("case_status") == "success" for chunk in chunks
        ):
            return KnowledgeReuseSignals()
        return KnowledgeReuseSignals(
            candidates=[
                KnowledgeMappingCandidate(
                    field_name="ADC_entity_country",
                    sources=[
                        SourceAttributeMapping(
                            attribute=AttributeReference(
                                attribute_name="entity_country"
                            ),
                            asset=AssetReference(asset_name="adc_entity"),
                        )
                    ],
                    supporting_chunk_ids=[chunks[0].chunk_id],
                    success_case_confirmed=True,
                    intent_match=True,
                    domain_compatible=True,
                    business_definition_compatible=True,
                    rationale="Packaged successful demo mapping.",
                )
            ]
        )


def _settings(database_path: Path) -> Settings:
    return Settings(
        google_api_key=None,
        model="deterministic-demo",
        log_level="WARNING",
        database_path=database_path,
        retriever_timeout_seconds=0.01,
        max_attempts=1,
    )


def _client(tmp_path: Path) -> TestClient:
    settings = _settings(tmp_path / "demo-e2e.sqlite3")

    def agent_factory(scenario: DemoKnowledgeScenario) -> AnalyzeAgent:
        retriever = FakeKnowledgeBaseRetriever(
            default_scenario=load_demo_scenario(scenario)
        )
        return AnalyzeAgent(
            build_runtime(
                settings,
                analyzer=DeterministicAnalyzer(),
                updater=DeterministicUpdater(),
                reconstructor=DeterministicReconstructor(),
                retriever=retriever,
            )
        )

    return TestClient(
        create_app(
            agent_factory=agent_factory,
            history_factory=lambda: AnalyzeAgentHistory.from_settings(settings),
            settings=ApiSettings(event_poll_seconds=0.001),
        )
    )


def _run_job(client: TestClient, path: str, payload: dict) -> dict:
    submission = client.post(path, json=payload)
    assert submission.status_code == 202
    job_id = submission.json()["job_id"]
    for _ in range(100):
        result = client.get(f"/api/v1/jobs/{job_id}").json()
        if result["status"] in {"completed", "failed"}:
            return result
        asyncio.run(asyncio.sleep(0.001))
    raise AssertionError("Demo workflow did not finish.")


def _initial(client: TestClient, scenario: str = "empty") -> dict:
    return _run_job(
        client,
        "/api/v1/jobs/initial",
        {
            "requirement": (
                "Build a Basel 3 ADC review GDA using Facility_id and "
                "ADC_entity_country."
            ),
            "knowledge_base_scenario": scenario,
        },
    )


def test_initial_empty_knowledge_base(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        result = _initial(client)

    assert result["status"] == "completed"
    assert result["result"]["reused_mappings"] == []
    assert result["result"]["clear_fields"][0]["name"] == "Facility_id"


def test_initial_reuses_packaged_mapping(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        result = _initial(client, "complete_mapping")

    assert result["status"] == "completed"
    assert result["result"]["reused_mappings"][0]["field_name"] == (
        "ADC_entity_country"
    )


def test_update_supplement_creates_second_revision(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        initial = _initial(client)
        requirement_id = initial["result"]["requirement_id"]
        updated = _run_job(
            client,
            "/api/v1/jobs/update",
            {
                "requirement_id": requirement_id,
                "supplemental_information": "Include booking country.",
            },
        )
        revisions = client.get(
            f"/api/v1/requirements/{requirement_id}/revisions"
        ).json()

    assert updated["status"] == "completed"
    assert len(revisions) == 2
    assert revisions[-1]["supplemental_information"] == "Include booking country."


def test_update_accept_feedback_creates_mapping(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        initial = _initial(client)
        updated = _run_job(
            client,
            "/api/v1/jobs/update",
            {
                "requirement_id": initial["result"]["requirement_id"],
                "search_feedback": [
                    {
                        "candidate_id": "search-candidate-1",
                        "target_type": "field_mapping",
                        "decision": "accept",
                        "field_name": "ADC_entity_country",
                        "asset": {"asset_name": "adc_entity"},
                        "attribute": {"attribute_name": "entity_country"},
                        "reason": "Confirmed in the search result.",
                    }
                ],
            },
        )

    mappings = updated["result"]["reused_mappings"]
    assert mappings[0]["evidence"][0]["reference"] == "search-candidate-1"


def test_timeout_scenario_degrades_with_warning(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        result = _initial(client, "timeout")

    assert result["status"] == "completed"
    assert result["result"]["warnings"] == [
        "Knowledge Base retrieval timed out."
    ]
