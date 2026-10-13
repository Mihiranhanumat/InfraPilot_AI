"""
Metrics analysis tools for InfraPilot AI.
"""
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from config.settings import (
    LATENCY_ANOMALY_MULTIPLIER,
    ERROR_RATE_THRESHOLD_PCT,
    CPU_ANOMALY_THRESHOLD_PCT,
    DB_CONN_THRESHOLD_PCT,
    CACHE_HIT_DROP_THRESHOLD_PCT,
)

def get_metric_series(
    metrics_df: pd.DataFrame,
    incident_id: str,
    service: Optional[str] = None,
    metric_name: Optional[str] = None
) -> pd.DataFrame:
    """Retrieve filtered metric time series."""
    df = metrics_df[metrics_df["incident_id"] == incident_id].copy()
    if service:
        df = df[df["service"] == service]
    if metric_name:
        df = df[df["metric_name"] == metric_name]
    return df.sort_values("timestamp")

def compare_to_baseline(
    metrics_df: pd.DataFrame,
    incident_id: str,
    service: str,
    metric_name: str,
    baseline_window: Tuple[str, str],
    incident_window: Tuple[str, str]
) -> Dict[str, Any]:
    """Compare metric behavior in baseline window vs incident window."""
    series = get_metric_series(metrics_df, incident_id, service, metric_name)
    if series.empty:
        return {
            "service": service,
            "metric_name": metric_name,
            "has_data": False,
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "baseline_mean": 0.0,
            "incident_mean": 0.0,
            "change_pct": 0.0,
            "first_anomaly_time": None,
            "unit": "",
        }

    b_start, b_end = pd.to_datetime(baseline_window[0]), pd.to_datetime(baseline_window[1])
    i_start, i_end = pd.to_datetime(incident_window[0]), pd.to_datetime(incident_window[1])

    b_df = series[(series["timestamp"] >= b_start) & (series["timestamp"] <= b_end)]
    i_df = series[(series["timestamp"] >= i_start) & (series["timestamp"] <= i_end)]

    if b_df.empty or i_df.empty:
        return {
            "service": service,
            "metric_name": metric_name,
            "has_data": False,
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "baseline_mean": 0.0,
            "incident_mean": 0.0,
            "change_pct": 0.0,
            "first_anomaly_time": None,
            "unit": series["unit"].iloc[0] if not series.empty else "",
        }

    unit = series["unit"].iloc[0]
    b_mean = float(b_df["value"].mean())
    i_mean = float(i_df["value"].mean())
    i_max = float(i_df["value"].max())

    change_pct = ((i_mean - b_mean) / (b_mean + 1e-5)) * 100.0

    is_anomaly = False
    anomaly_score = 0.0
    first_anomaly_time = None

    if metric_name == "p95_latency_ms":
        threshold = b_mean * LATENCY_ANOMALY_MULTIPLIER
        if i_mean >= threshold or i_max > b_mean * 2.0:
            is_anomaly = True
            ratio = (i_mean / (b_mean + 1e-5))
            anomaly_score = min(1.0, 0.4 + (ratio - 1.0) * 0.1)
            # Find earliest point exceeding threshold
            breaches = i_df[i_df["value"] >= threshold]
            if not breaches.empty:
                first_anomaly_time = breaches["timestamp"].iloc[0].strftime("%Y-%m-%dT%H:%M:%S")

    elif metric_name == "error_rate_pct":
        if i_mean >= ERROR_RATE_THRESHOLD_PCT or i_max >= ERROR_RATE_THRESHOLD_PCT:
            is_anomaly = True
            anomaly_score = min(1.0, 0.5 + (i_mean / 50.0) * 0.5)
            breaches = i_df[i_df["value"] >= ERROR_RATE_THRESHOLD_PCT]
            if not breaches.empty:
                first_anomaly_time = breaches["timestamp"].iloc[0].strftime("%Y-%m-%dT%H:%M:%S")

    elif metric_name == "db_connections_pct":
        if i_mean >= DB_CONN_THRESHOLD_PCT or i_max >= DB_CONN_THRESHOLD_PCT:
            is_anomaly = True
            anomaly_score = min(1.0, 0.6 + (i_mean / 100.0) * 0.4)
            breaches = i_df[i_df["value"] >= DB_CONN_THRESHOLD_PCT]
            if not breaches.empty:
                first_anomaly_time = breaches["timestamp"].iloc[0].strftime("%Y-%m-%dT%H:%M:%S")

    elif metric_name == "cpu_pct":
        if i_mean >= CPU_ANOMALY_THRESHOLD_PCT:
            is_anomaly = True
            anomaly_score = min(1.0, 0.5 + (i_mean / 100.0) * 0.5)
            breaches = i_df[i_df["value"] >= CPU_ANOMALY_THRESHOLD_PCT]
            if not breaches.empty:
                first_anomaly_time = breaches["timestamp"].iloc[0].strftime("%Y-%m-%dT%H:%M:%S")

    elif metric_name == "cache_hit_rate_pct":
        drop = b_mean - i_mean
        if drop >= CACHE_HIT_DROP_THRESHOLD_PCT:
            is_anomaly = True
            anomaly_score = min(1.0, 0.6 + (drop / 100.0) * 0.4)
            breaches = i_df[i_df["value"] <= (b_mean - CACHE_HIT_DROP_THRESHOLD_PCT)]
            if not breaches.empty:
                first_anomaly_time = breaches["timestamp"].iloc[0].strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "service": service,
        "metric_name": metric_name,
        "has_data": True,
        "baseline_mean": round(b_mean, 2),
        "incident_mean": round(i_mean, 2),
        "change_pct": round(change_pct, 1),
        "is_anomaly": is_anomaly,
        "anomaly_score": round(anomaly_score, 2),
        "first_anomaly_time": first_anomaly_time,
        "unit": unit,
    }

def rank_anomalies(
    metrics_df: pd.DataFrame,
    incident_id: str,
    baseline_window: Tuple[str, str],
    incident_window: Tuple[str, str]
) -> List[Dict[str, Any]]:
    """Scan all (service, metric) pairs and rank anomalies by severity and onset."""
    inc_df = metrics_df[metrics_df["incident_id"] == incident_id]
    pairs = inc_df[["service", "metric_name"]].drop_duplicates().values

    results = []
    for service, m_name in pairs:
        res = compare_to_baseline(metrics_df, incident_id, service, m_name, baseline_window, incident_window)
        if res.get("is_anomaly"):
            results.append(res)

    # Sort primarily by anomaly score descending, then by onset time
    results.sort(
        key=lambda x: (
            -x["anomaly_score"],
            x["first_anomaly_time"] if x["first_anomaly_time"] else "9999"
        )
    )
    return results

def find_first_anomaly(
    metrics_df: pd.DataFrame,
    incident_id: str,
    baseline_window: Tuple[str, str],
    incident_window: Tuple[str, str]
) -> Optional[Dict[str, Any]]:
    """Determine which service/metric breached anomaly thresholds first chronologically."""
    anomalies = rank_anomalies(metrics_df, incident_id, baseline_window, incident_window)
    timed = [a for a in anomalies if a.get("first_anomaly_time")]
    if not timed:
        return None
    timed.sort(key=lambda x: x["first_anomaly_time"])
    return timed[0]
