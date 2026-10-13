"""
Tests for IncidentOrchestrator and end-to-end multi-agent workflow.
"""
import pytest
from infrapilot.orchestrator import IncidentOrchestrator

@pytest.fixture
def orchestrator():
    return IncidentOrchestrator()

def test_scenario_a_database_spike(orchestrator):
    state = orchestrator.investigate("INC-1001")
    assert state.status == "Validated hypothesis"
    assert state.leading_hypothesis is not None
    assert state.leading_hypothesis.candidate_service == "database"
    assert len(state.leading_hypothesis.supporting_evidence_ids) >= 2
    assert state.validation.passed is True
    assert len(state.agent_traces) >= 8
    assert state.report is not None

def test_scenario_b_deployment_regression(orchestrator):
    state = orchestrator.investigate("INC-1002")
    assert state.status == "Validated hypothesis"
    assert state.leading_hypothesis is not None
    assert state.leading_hypothesis.candidate_service == "order_api"
    assert state.validation.passed is True
    assert state.report is not None

def test_scenario_c_cache_stampede(orchestrator):
    state = orchestrator.investigate("INC-1003")
    assert state.status == "Validated hypothesis"
    assert state.leading_hypothesis is not None
    assert state.leading_hypothesis.candidate_service == "cache"
    assert state.validation.passed is True
    assert state.report is not None

def test_scenario_d_escalates_to_human_review(orchestrator):
    state = orchestrator.investigate("INC-1004")
    # Scenario D must escalate to Human Review due to telemetry dropout / contradiction
    assert state.status == "Needs human review"
    assert state.validation.passed is False
    assert state.validation.decision == "HUMAN_REVIEW"
    assert state.retry_count <= 1, "Retry count must never exceed one"
    assert len(state.validation.missing_evidence_flags) > 0

def test_retry_count_strictly_bounded(orchestrator):
    for inc_id in ["INC-1001", "INC-1002", "INC-1003", "INC-1004"]:
        state = orchestrator.investigate(inc_id)
        assert state.retry_count in [0, 1]
