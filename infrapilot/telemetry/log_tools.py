"""
Log and Event analysis tools for InfraPilot AI.
"""
from typing import List, Dict, Any, Optional
import pandas as pd
import re

def search_logs(
    logs_df: pd.DataFrame,
    incident_id: str,
    query: Optional[str] = None,
    service: Optional[str] = None,
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> pd.DataFrame:
    """Filter logs for a specific incident with optional regex query, service, level, and time range."""
    df = logs_df[logs_df["incident_id"] == incident_id].copy()
    if service:
        df = df[df["service"] == service]
    if level:
        df = df[df["level"].str.upper() == level.upper()]
    if start_time:
        df = df[df["timestamp"] >= pd.to_datetime(start_time)]
    if end_time:
        df = df[df["timestamp"] <= pd.to_datetime(end_time)]
    if query:
        pattern = re.compile(query, re.IGNORECASE)
        df = df[df["message"].apply(lambda msg: bool(pattern.search(str(msg))))]
    return df.sort_values("timestamp")

def count_log_patterns(
    logs_df: pd.DataFrame,
    incident_id: str,
    patterns: Optional[Dict[str, str]] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Scan and count occurrences of error/warning patterns."""
    if patterns is None:
        patterns = {
            "DB_TIMEOUT_OR_EXHAUSTION": r"connection pool (exhausted|saturated)|timeout.*database|HikariPool",
            "HTTP_5XX_ERROR": r"500 Internal Server|504 Gateway Timeout|HTTP 5\d\d",
            "APPLICATION_EXCEPTION": r"NullPointerException|Exception|Traceback|ErrorValidator",
            "CACHE_DEGRADATION": r"eviction rate|cache miss|purged under memory",
            "QUERY_LATENCY_OR_TIMEOUT": r"Query execution timeout|High concurrent read throughput"
        }

    df = logs_df[logs_df["incident_id"] == incident_id].copy()
    if start_time:
        df = df[df["timestamp"] >= pd.to_datetime(start_time)]
    if end_time:
        df = df[df["timestamp"] <= pd.to_datetime(end_time)]

    pattern_counts = []
    for pattern_name, regex in patterns.items():
        pattern_re = re.compile(regex, re.IGNORECASE)
        matches = df[df["message"].apply(lambda msg: bool(pattern_re.search(str(msg))))]
        if not matches.empty:
            services_affected = matches["service"].unique().tolist()
            first_seen = matches["timestamp"].min().strftime("%Y-%m-%dT%H:%M:%S")
            sample_msg = matches["message"].iloc[0]
            pattern_counts.append({
                "pattern_name": pattern_name,
                "regex": regex,
                "count": len(matches),
                "services": services_affected,
                "first_seen": first_seen,
                "sample_message": sample_msg,
                "log_level": matches["level"].iloc[0],
            })
    return pattern_counts

def get_recent_events(
    events_df: pd.DataFrame,
    incident_id: str,
    service: Optional[str] = None,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve operational lifecycle events (deployments, alerts, maintenance) for incident."""
    df = events_df[events_df["incident_id"] == incident_id].copy()
    if service:
        df = df[df["service"] == service]
    if event_type:
        df = df[df["event_type"].str.upper() == event_type.upper()]
    df = df.sort_values("timestamp")
    
    events = []
    for _, row in df.iterrows():
        events.append({
            "timestamp": row["timestamp"].strftime("%Y-%m-%dT%H:%M:%S") if hasattr(row["timestamp"], "strftime") else str(row["timestamp"]),
            "service": row["service"],
            "event_type": row["event_type"],
            "description": row["description"]
        })
    return events
