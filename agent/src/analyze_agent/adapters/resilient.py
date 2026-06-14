"""Timeout and retry wrappers for external Analyze Agent dependencies."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from analyze_agent.domain.models import (
    AnalyzedRequirement,
    KnowledgeChunk,
    KnowledgeReuseSignals,
    RequirementAnalysisSignals,
    RequirementUpdateSignals,
    SearchFeedback,
)
from analyze_agent.ports.analyzer_errors import RequirementAnalysisError
from analyze_agent.ports.knowledge_reconstructor import KnowledgeReconstructor
from analyze_agent.ports.knowledge_retriever import KnowledgeBaseRetriever
from analyze_agent.ports.reconstructor_errors import KnowledgeReconstructionError
from analyze_agent.ports.requirement_analyzer import RequirementAnalyzer
from analyze_agent.ports.requirement_updater import RequirementUpdater
from analyze_agent.ports.retriever_errors import (
    KnowledgeRetrievalError,
    KnowledgeRetrievalTimeout,
)
from analyze_agent.resilience import RetryPolicy, call_with_retry


class ResilientRequirementAnalyzer:
    def __init__(self, delegate: RequirementAnalyzer, policy: RetryPolicy) -> None:
        self._delegate = delegate
        self._policy = policy

    async def analyze(self, requirement: str) -> RequirementAnalysisSignals:
        try:
            return await call_with_retry(
                lambda: self._delegate.analyze(requirement),
                policy=self._policy,
                is_retryable=_retryable_model_error,
            )
        except TimeoutError as error:
            raise RequirementAnalysisError(
                "Requirement analysis timed out.",
                retryable=True,
            ) from error


class ResilientRequirementUpdater:
    def __init__(self, delegate: RequirementUpdater, policy: RetryPolicy) -> None:
        self._delegate = delegate
        self._policy = policy

    async def update(
        self,
        *,
        previous_requirement: str,
        supplemental_information: str | None,
        feedback: list[SearchFeedback],
        previous_output: Mapping[str, Any] | None,
    ) -> RequirementUpdateSignals:
        try:
            return await call_with_retry(
                lambda: self._delegate.update(
                    previous_requirement=previous_requirement,
                    supplemental_information=supplemental_information,
                    feedback=feedback,
                    previous_output=previous_output,
                ),
                policy=self._policy,
                is_retryable=_retryable_model_error,
            )
        except TimeoutError as error:
            raise RequirementAnalysisError(
                "Requirement update timed out.",
                retryable=True,
            ) from error


class ResilientKnowledgeReconstructor:
    def __init__(self, delegate: KnowledgeReconstructor, policy: RetryPolicy) -> None:
        self._delegate = delegate
        self._policy = policy

    async def reconstruct(
        self,
        *,
        requirement: str,
        analyzed_requirement: AnalyzedRequirement,
        chunks: list[KnowledgeChunk],
    ) -> KnowledgeReuseSignals:
        try:
            return await call_with_retry(
                lambda: self._delegate.reconstruct(
                    requirement=requirement,
                    analyzed_requirement=analyzed_requirement,
                    chunks=chunks,
                ),
                policy=self._policy,
                is_retryable=_retryable_reconstruction_error,
            )
        except TimeoutError as error:
            raise KnowledgeReconstructionError(
                "Knowledge reconstruction timed out.",
                retryable=True,
            ) from error


class ResilientKnowledgeBaseRetriever:
    def __init__(self, delegate: KnowledgeBaseRetriever, policy: RetryPolicy) -> None:
        self._delegate = delegate
        self._policy = policy

    async def search(self, text: str) -> list[KnowledgeChunk]:
        try:
            return await call_with_retry(
                lambda: self._delegate.search(text),
                policy=self._policy,
                is_retryable=_retryable_retrieval_error,
            )
        except TimeoutError as error:
            raise KnowledgeRetrievalTimeout() from error


def _retryable_model_error(error: BaseException) -> bool:
    return isinstance(error, TimeoutError) or (
        isinstance(error, RequirementAnalysisError) and error.retryable
    )


def _retryable_reconstruction_error(error: BaseException) -> bool:
    return isinstance(error, TimeoutError) or (
        isinstance(error, KnowledgeReconstructionError) and error.retryable
    )


def _retryable_retrieval_error(error: BaseException) -> bool:
    return (
        isinstance(error, asyncio.TimeoutError)
        or isinstance(error, KnowledgeRetrievalError)
        and error.retryable
    )
