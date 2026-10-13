"""
Safe, read-only diagnostic tools for verifying incident hypotheses.
Never mutates or writes to any infrastructure or service.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from infrapilot.telemetry.metrics_tools import compare_to_baseline, get_metric_series
from infrapilot.telemetry.dependency_tools import check_path_exists
from infrapilot.telemetry.log_tools import search_logs

def compare_metric_timelines(
    metrics_df: pd.DataFrame,
    incident_id: str,
    upstream_service: str,
    upstream_metric: str,
    downstream_service: str,
    downstream_metric: str,
    baseline_window: tuple,
    incident_window: tuple,
) -> Dict[str, Any]:
    """
    Diagnostic: Check whether upstream service anomaly preceded downstream service anomaly.
    Returns: timeline comparison result and whether precedence test passes.
    """
    up_res = compare_to_baseline(metrics_df, incident_id, upstream_service, upstream_metric, baseline_window, incident_window)
    down_res = compare_to_baseline(metrics_df, incident_id, downstream_service, downstream_metric, baseline_window, incident_window)

    up_time = up_res.get("first_anomaly_time")
    down_time = down_res.get("first_anomaly_time")

    if up_time and down_time:
        precedes = pd.to_datetime(up_time) <= pd.to_datetime(down_time)
        delta_sec = (pd.to_datetime(down_time) - pd.to_datetime(up_time)).total_seconds()
        return {
            "test_name": "Timeline Precedence Test",
            "passed": precedes,
            "upstream_time": up_time,
            "downstream_time": down_time,
            "delta_seconds": delta_sec,
            "details": f"{upstream_service} ({upstream_metric}) anomaly began at {up_time}, preceding {downstream_service} ({downstream_metric}) at {down_time} by {delta_sec}s." if precedes else f"{upstream_service} anomaly occurred after {downstream_service} anomaly."
        }
    return {
        "test_name": "Timeline Precedence Test",
        "passed": False,
        "upstream_time": up_time,
        "downstream_time": down_time,
        "delta_seconds": None,
        "details": "Insufficient onset timestamps to establish timeline precedence."
    }

def verify_dependency_viability(
    services_df: pd.DataFrame,
    candidate_service: str,
    symptom_services: List[str]
) -> Dict[str, Any]:
    """
    Diagnostic: Check whether candidate service is in topological path of all symptom services.
    """
    paths_found = {}
    all_viable = True
    for symptom_svc in symptom_services:
        if candidate_service == symptom_svc:
            paths_found[symptom_svc] = [symptom_svc]
            continue
        has_path, path = check_path_exists(services_df, candidate_service, symptom_svc)
        paths_found[symptom_svc] = path
        if not has_path:
            all_viable = False

    return {
        "test_name": "Topological Viability Test",
        "passed": all_viable,
        "paths": paths_found,
        "details": f"Candidate '{candidate_service}' has valid caller paths to {list(paths_found.keys())}" if all_viable else f"Candidate '{candidate_service}' is NOT upstream of one or more symptom services: {symptom_services}"
    }

def compare_event_window_impact(
    metrics_df: pd.DataFrame,
    incident_id: str,
    service: str,
    event_timestamp: str,
    window_minutes: int = 5
) -> Dict[str, Any]:
    """
    Diagnostic: Compare metric behavior immediately before and immediately after an operational event.
    """
    event_t = pd.to_datetime(event_timestamp)
    pre_window = (event_t - pd.Timedelta(minutes=window_minutes), event_t)
    post_window = (event_t, event_t + pd.Timedelta(minutes=window_minutes))

    series = get_metric_series(metrics_df, incident_id, service, "error_rate_pct")
    if series.empty:
        series = get_metric_series(metrics_df, incident_id, service, "p95_latency_ms")

    if series.empty:
        return {
            "test_name": "Event Window Impact Test",
            "passed": False,
            "details": f"No metric series found for {service} around event {event_timestamp}"
        }

    pre_data = series[(series["timestamp"] >= pre_window[0]) & (series["timestamp"] < pre_window[1])]
    post_data = series[(series["timestamp"] >= post_window[0]) & (series["timestamp"] <= post_window[1])]

    pre_val = float(pre_data["value"].mean()) if not pre_data.empty else 0.0
    post_val = float(post_data["value"].mean()) if not post_data.empty else 0.0
    delta = post_val - pre_val

    degraded = delta > 1.0 or post_val > 5.0
    return {
        "test_name": "Event Window Impact Test",
        "passed": degraded,
        "pre_event_mean": round(pre_val, 2),
        "post_event_mean": round(post_val, 2),
        "delta": round(delta, 2),
        "metric_evaluated": series["metric_name"].iloc[0],
        "details": f"Post-event metric surged from {round(pre_val, 2)} to {round(post_val, 2)} within {window_minutes}m of event at {event_timestamp}." if degraded else "No significant degradation observed following event."
    }

def verify_log_error_correlation(
    logs_df: pd.DataFrame,
    incident_id: str,
    service: str,
    query_regex: str,
    start_time: str
) -> Dict[str, Any]:
    """
    Diagnostic: Confirm matching error logs emerged during the anomaly window.
    """
    matching = search_logs(logs_df, incident_id, query=query_regex, service=service, start_time=start_time)
    count = len(matching)
    has_logs = count > 0
    return {
        "test_name": "Log Correlation Test",
        "passed": has_logs,
        "match_count": count,
        "sample": matching["message"].iloc[0] if has_logs else None,
        "details": f"Found {count} logs matching '{query_regex}' on service {service} after {start_time}." if has_logs else f"No logs matching '{query_regex}' on service {service} after {start_time}."
    }
