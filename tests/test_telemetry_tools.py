"""
Tests for pure telemetry tools (metrics, logs, dependencies, diagnostics).
"""
import pytest
from infrapilot.scenario_loader import loader
from infrapilot.telemetry.metrics_tools import (
    compare_to_baseline,
    rank_anomalies,
    find_first_anomaly
)
from infrapilot.telemetry.log_tools import (
    search_logs,
    count_log_patterns,
    get_recent_events
)
from infrapilot.telemetry.dependency_tools import (
    build_dependency_graph,
    get_upstream_services,
    get_downstream_impact,
    check_path_exists
)
from infrapilot.telemetry.diagnostic_tools import (
    compare_metric_timelines,
    verify_dependency_viability
)

@pytest.fixture
def test_data():
    return {
        "metrics": loader.load_metrics(),
        "logs": loader.load_logs(),
        "events": loader.load_events(),
        "services": loader.load_services(),
    }

def test_metrics_anomaly_detection(test_data):
    df = test_data["metrics"]
    # Check Database latency spike in INC-1001
    res = compare_to_baseline(
        df, "INC-1001", "database", "p95_latency_ms",
        baseline_window=("2026-10-13T10:00:00", "2026-10-13T10:15:00"),
        incident_window=("2026-10-13T10:16:00", "2026-10-13T10:30:00")
    )
    assert res["is_anomaly"] is True
    assert res["incident_mean"] > res["baseline_mean"] * 10.0
    assert res["first_anomaly_time"] is not None

def test_metrics_earliest_anomaly(test_data):
    df = test_data["metrics"]
    first = find_first_anomaly(
        df, "INC-1001",
        baseline_window=("2026-10-13T10:00:00", "2026-10-13T10:15:00"),
        incident_window=("2026-10-13T10:16:00", "2026-10-13T10:30:00")
    )
    assert first is not None
    # Database anomaly should appear before or at 10:16:00
    assert first["service"] == "database"

def test_log_search_and_patterns(test_data):
    logs_df = test_data["logs"]
    patterns = count_log_patterns(logs_df, "INC-1001")
    assert len(patterns) > 0
    pattern_names = [p["pattern_name"] for p in patterns]
    assert "DB_TIMEOUT_OR_EXHAUSTION" in pattern_names

def test_dependency_topology(test_data):
    services_df = test_data["services"]
    G = build_dependency_graph(services_df)
    assert G.has_edge("order_api", "database")
    assert G.has_edge("frontend", "order_api")
    
    upstream = get_upstream_services(services_df, "frontend")
    assert "order_api" in upstream
    assert "database" in upstream

    downstream = get_downstream_impact(services_df, "database")
    assert "order_api" in downstream
    assert "frontend" in downstream

    has_path, path = check_path_exists(services_df, "database", "frontend")
    assert has_path is True
    assert path == ["frontend", "order_api", "database"]

def test_read_only_diagnostics(test_data):
    metrics_df = test_data["metrics"]
    services_df = test_data["services"]
    
    # Precedence test for INC-1001 (DB precedes Order API)
    diag = compare_metric_timelines(
        metrics_df, "INC-1001",
        upstream_service="database", upstream_metric="p95_latency_ms",
        downstream_service="order_api", downstream_metric="p95_latency_ms",
        baseline_window=("2026-10-13T10:00:00", "2026-10-13T10:15:00"),
        incident_window=("2026-10-13T10:16:00", "2026-10-13T10:30:00")
    )
    assert diag["passed"] is True
    assert diag["delta_seconds"] >= 0

    # Viability test
    viab = verify_dependency_viability(services_df, "database", ["order_api", "frontend"])
    assert viab["passed"] is True
