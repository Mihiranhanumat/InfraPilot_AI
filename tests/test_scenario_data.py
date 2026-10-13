"""
Tests for scenario and synthetic telemetry data consistency and completeness.
"""
import pytest
import pandas as pd
from infrapilot.scenario_loader import loader

def test_scenarios_load_successfully():
    scenarios = loader.list_scenarios()
    assert len(scenarios) >= 4, "Should have at least 4 test scenarios defined"
    ids = [s["incident_id"] for s in scenarios]
    assert "INC-1001" in ids
    assert "INC-1002" in ids
    assert "INC-1003" in ids
    assert "INC-1004" in ids

def test_services_data_integrity():
    services_df = loader.load_services()
    assert not services_df.empty
    assert set(["service", "depends_on", "criticality"]).issubset(services_df.columns)
    assert "order_api" in services_df["service"].values
    assert "database" in services_df["depends_on"].values

def test_metrics_telemetry_integrity():
    metrics_df = loader.load_metrics()
    assert not metrics_df.empty
    expected_cols = ["timestamp", "incident_id", "service", "metric_name", "value", "unit"]
    assert set(expected_cols).issubset(metrics_df.columns)
    
    # Ensure every scenario has metric data
    for inc_id in ["INC-1001", "INC-1002", "INC-1003", "INC-1004"]:
        sub = metrics_df[metrics_df["incident_id"] == inc_id]
        assert len(sub) > 0, f"Scenario {inc_id} has no metrics"

def test_logs_telemetry_integrity():
    logs_df = loader.load_logs()
    assert not logs_df.empty
    expected_cols = ["timestamp", "incident_id", "service", "level", "message", "event_type"]
    assert set(expected_cols).issubset(logs_df.columns)
    
    for inc_id in ["INC-1001", "INC-1002", "INC-1003", "INC-1004"]:
        sub = logs_df[logs_df["incident_id"] == inc_id]
        assert len(sub) > 0, f"Scenario {inc_id} has no logs"

def test_events_telemetry_integrity():
    events_df = loader.load_events()
    assert not events_df.empty
    expected_cols = ["timestamp", "incident_id", "service", "event_type", "description"]
    assert set(expected_cols).issubset(events_df.columns)
