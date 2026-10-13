"""
Tests for Critic/Validator agent and evidence grounding checks.
"""
import pytest
from infrapilot.state import IncidentState
from infrapilot.schemas import ScenarioMetadata, Hypothesis
from infrapilot.agents.critic import CriticValidator

@pytest.fixture
def sample_state():
    meta = ScenarioMetadata(
        incident_id="INC-TEST",
        title="Test Incident",
        severity="HIGH",
        incident_summary="Test symptom",
        affected_services=["order_api"],
        baseline_window=["2026-10-13T10:00:00", "2026-10-13T10:15:00"],
        incident_window=["2026-10-13T10:16:00", "2026-10-13T10:30:00"]
    )
    return IncidentState("INC-TEST", meta)

def test_critic_rejects_unregistered_evidence_ids(sample_state):
    critic = CriticValidator()
    # Inject a hypothesis citing hallucinated/unregistered evidence IDs
    fake_hypothesis = Hypothesis(
        rank=1,
        candidate_service="database",
        claim="Database is failing",
        heuristic_score=0.90,
        score_breakdown={},
        supporting_evidence_ids=["METRIC-FAKE-99", "LOG-FABRICATED-01"],
        contradicting_evidence_ids=[],
        timeline_fit="Good",
        dependency_fit="Good",
        reasoning="Fake reasoning",
        limitations="None"
    )
    sample_state.hypotheses = [fake_hypothesis]
    # No evidence added to sample_state.evidence_store
    
    val_res = critic.run(sample_state)
    assert val_res.passed is False
    assert len(val_res.unsupported_claims) > 0
    assert "METRIC-FAKE-99" in val_res.unsupported_claims[0]

def test_critic_reinvestigate_on_first_try(sample_state):
    critic = CriticValidator()
    # Weak hypothesis with retry_count = 0
    hypo = Hypothesis(
        rank=1,
        candidate_service="database",
        claim="Inconclusive guess",
        heuristic_score=0.45,  # Low score
        score_breakdown={},
        supporting_evidence_ids=[],
        contradicting_evidence_ids=[],
        timeline_fit="",
        dependency_fit="",
        reasoning="",
        limitations=""
    )
    sample_state.hypotheses = [hypo]
    sample_state.retry_count = 0

    val_res = critic.run(sample_state)
    assert val_res.decision == "REINVESTIGATE"
    assert val_res.retry_recommended is True

def test_critic_escalates_to_human_review_after_retry(sample_state):
    critic = CriticValidator()
    hypo = Hypothesis(
        rank=1,
        candidate_service="database",
        claim="Inconclusive guess",
        heuristic_score=0.45,
        score_breakdown={},
        supporting_evidence_ids=[],
        contradicting_evidence_ids=[],
        timeline_fit="",
        dependency_fit="",
        reasoning="",
        limitations=""
    )
    sample_state.hypotheses = [hypo]
    sample_state.retry_count = 1  # Retry budget already used

    val_res = critic.run(sample_state)
    assert val_res.decision == "HUMAN_REVIEW"
    assert val_res.passed is False
    assert val_res.retry_recommended is False
