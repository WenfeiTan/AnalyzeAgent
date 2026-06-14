from analyze_agent.application.knowledge_reuse import build_reused_mappings
from analyze_agent.domain.models import (
    AssetReference,
    AttributeReference,
    KnowledgeChunk,
    KnowledgeMappingCandidate,
    SourceAttributeMapping,
)


def _source(
    *,
    attribute_name: str = "entity_country",
    asset_name: str = "adc_entity",
) -> SourceAttributeMapping:
    return SourceAttributeMapping(
        attribute=AttributeReference(attribute_name=attribute_name),
        asset=AssetReference(asset_name=asset_name),
    )


def _candidate(**overrides) -> KnowledgeMappingCandidate:
    payload = {
        "field_name": "ADC_entity_country",
        "sources": [_source()],
        "supporting_chunk_ids": ["chunk-1"],
        "success_case_confirmed": True,
        "intent_match": True,
        "domain_compatible": True,
        "business_definition_compatible": True,
        "rationale": "Verified successful ADC mapping.",
    }
    payload.update(overrides)
    return KnowledgeMappingCandidate.model_validate(payload)


def _chunk(text: str | None = None) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id="chunk-1",
        text=text
        or (
            "Successful case: ADC_entity_country maps to entity_country "
            "on asset adc_entity."
        ),
        metadata={"case_status": "success"},
    )


def test_complete_evidence_becomes_high_confidence_mapping() -> None:
    mappings = build_reused_mappings(
        candidates=[_candidate()],
        chunks=[_chunk()],
        negative_constraints=[],
    )

    assert len(mappings) == 1
    assert mappings[0].confidence.score == 0.9
    assert mappings[0].evidence[0].reference == "chunk-1"


def test_partial_mapping_without_asset_is_not_reconstructed() -> None:
    mappings = build_reused_mappings(
        candidates=[_candidate(sources=[])],
        chunks=[_chunk()],
        negative_constraints=[],
    )

    assert mappings == []


def test_fabricated_source_identity_is_rejected() -> None:
    mappings = build_reused_mappings(
        candidates=[_candidate(sources=[_source(asset_name="invented_asset")])],
        chunks=[_chunk()],
        negative_constraints=[],
    )

    assert mappings == []


def test_unknown_supporting_chunk_is_rejected() -> None:
    mappings = build_reused_mappings(
        candidates=[_candidate(supporting_chunk_ids=["missing"])],
        chunks=[_chunk()],
        negative_constraints=[],
    )

    assert mappings == []


def test_context_conflict_is_rejected() -> None:
    mappings = build_reused_mappings(
        candidates=[_candidate(context_conflict=True)],
        chunks=[_chunk()],
        negative_constraints=[],
    )

    assert mappings == []


def test_negative_constraint_blocks_reuse() -> None:
    mappings = build_reused_mappings(
        candidates=[_candidate()],
        chunks=[_chunk()],
        negative_constraints=["adc_entity_country"],
    )

    assert mappings == []

