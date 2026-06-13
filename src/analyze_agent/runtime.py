"""Runtime composition and dependency injection for ADK tools."""

from __future__ import annotations

from dataclasses import dataclass

from analyze_agent.adapters.fake_knowledge_retriever import (
    FakeKnowledgeBaseRetriever,
)
from analyze_agent.adapters.gemini_knowledge_reconstructor import (
    GeminiKnowledgeReconstructor,
)
from analyze_agent.adapters.gemini_requirement_analyzer import (
    ANALYZE_REQUIREMENT_PROMPT_VERSION,
    GeminiRequirementAnalyzer,
)
from analyze_agent.adapters.gemini_requirement_updater import (
    GeminiRequirementUpdater,
)
from analyze_agent.adapters.resilient import (
    ResilientKnowledgeBaseRetriever,
    ResilientKnowledgeReconstructor,
    ResilientRequirementAnalyzer,
    ResilientRequirementUpdater,
)
from analyze_agent.application.analysis_pipeline import AnalysisPipeline
from analyze_agent.application.initial_analysis import InitialAnalysisService
from analyze_agent.application.update_analysis import UpdatedAnalysisService
from analyze_agent.config import ConfigurationError, Settings, load_settings
from analyze_agent.observability import configure_logging
from analyze_agent.persistence.sqlite_repository import SQLiteRequirementRepository
from analyze_agent.ports.knowledge_reconstructor import KnowledgeReconstructor
from analyze_agent.ports.knowledge_retriever import KnowledgeBaseRetriever
from analyze_agent.ports.requirement_analyzer import RequirementAnalyzer
from analyze_agent.ports.requirement_repository import RequirementRepository
from analyze_agent.ports.requirement_updater import RequirementUpdater
from analyze_agent.resilience import RetryPolicy


@dataclass(frozen=True, slots=True)
class AnalyzeAgentRuntime:
    initial_service: InitialAnalysisService
    updated_service: UpdatedAnalysisService
    retriever: KnowledgeBaseRetriever


_runtime: AnalyzeAgentRuntime | None = None


def configure_runtime(runtime: AnalyzeAgentRuntime | None) -> None:
    """Inject or reset the process runtime, primarily for tests and orchestration."""

    global _runtime
    _runtime = runtime


def get_runtime() -> AnalyzeAgentRuntime:
    global _runtime
    if _runtime is None:
        settings = load_settings(require_api_key=True)
        _runtime = build_runtime(settings)
    return _runtime


def build_runtime(
    settings: Settings,
    *,
    analyzer: RequirementAnalyzer | None = None,
    updater: RequirementUpdater | None = None,
    reconstructor: KnowledgeReconstructor | None = None,
    retriever: KnowledgeBaseRetriever | None = None,
    repository: RequirementRepository | None = None,
) -> AnalyzeAgentRuntime:
    configure_logging(settings.log_level)
    if analyzer is None or updater is None or reconstructor is None:
        if not settings.google_api_key:
            raise ConfigurationError(
                "GOOGLE_API_KEY is required when Gemini adapters are not injected."
            )

    analyzer = analyzer or GeminiRequirementAnalyzer(
        api_key=settings.google_api_key or "",
        model=settings.model,
        repair_attempts=settings.schema_repair_attempts,
    )
    updater = updater or GeminiRequirementUpdater(
        api_key=settings.google_api_key or "",
        model=settings.model,
        repair_attempts=settings.schema_repair_attempts,
    )
    reconstructor = reconstructor or GeminiKnowledgeReconstructor(
        api_key=settings.google_api_key or "",
        model=settings.model,
        repair_attempts=settings.schema_repair_attempts,
    )
    retriever = retriever or FakeKnowledgeBaseRetriever()

    model_policy = RetryPolicy(
        timeout_seconds=settings.model_timeout_seconds,
        max_attempts=settings.max_attempts,
    )
    retriever_policy = RetryPolicy(
        timeout_seconds=settings.retriever_timeout_seconds,
        max_attempts=settings.max_attempts,
    )
    analyzer = ResilientRequirementAnalyzer(analyzer, model_policy)
    updater = ResilientRequirementUpdater(updater, model_policy)
    reconstructor = ResilientKnowledgeReconstructor(reconstructor, model_policy)
    retriever = ResilientKnowledgeBaseRetriever(retriever, retriever_policy)

    if repository is None:
        sqlite_repository = SQLiteRequirementRepository(settings.database_path)
        sqlite_repository.initialize()
        repository = sqlite_repository

    pipeline = AnalysisPipeline(
        analyzer=analyzer,
        retriever=retriever,
        model=settings.model,
        prompt_version=ANALYZE_REQUIREMENT_PROMPT_VERSION,
        knowledge_reconstructor=reconstructor,
    )
    return AnalyzeAgentRuntime(
        initial_service=InitialAnalysisService(
            analyzer=analyzer,
            retriever=retriever,
            repository=repository,
            model=settings.model,
            prompt_version=ANALYZE_REQUIREMENT_PROMPT_VERSION,
            knowledge_reconstructor=reconstructor,
        ),
        updated_service=UpdatedAnalysisService(
            updater=updater,
            pipeline=pipeline,
            repository=repository,
        ),
        retriever=retriever,
    )
