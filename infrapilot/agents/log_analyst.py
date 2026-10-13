"""
Log and Event Analyst Agent.
Analyzes log error patterns and lifecycle events while treating logs as untrusted evidence.
"""
import time
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from infrapilot.state import IncidentState
from infrapilot.schemas import LogFinding, EventFinding, EvidenceRecord, AgentTrace
from infrapilot.telemetry.log_tools import count_log_patterns, get_recent_events, search_logs
from infrapilot.safety.policy import sanitize_log_content

class LogAnalyst:
    def __init__(self, logs_df: pd.DataFrame, events_df: pd.DataFrame):
        self.logs_df = logs_df
        self.events_df = events_df
        self.role_description = "Searches logs and events, counts error patterns, and sanitizes untrusted log text."

    def run(self, state: IncidentState) -> List[LogFinding]:
        start_time = time.time()
        tools_called = []
        evidence_ids = []
        log_findings: List[LogFinding] = []
        event_findings: List[EventFinding] = []

        inc_id = state.incident_id
        i_window = state.scenario_info.incident_window

        # Tool 1: get_recent_events
        raw_events = get_recent_events(self.events_df, inc_id)
        tools_called.append({
            "tool": "get_recent_events",
            "inputs": {"incident_id": inc_id},
            "output": f"Retrieved {len(raw_events)} events (deployments, alerts, maintenance)."
        })

        for idx, ev in enumerate(raw_events, start=1):
            ev_id = f"EVENT-{ev['service'][:3].upper()}-{idx:02d}"
            finding = EventFinding(
                event_type=ev["event_type"],
                service=ev["service"],
                timestamp=ev["timestamp"],
                description=ev["description"],
                evidence_id=ev_id
            )
            event_findings.append(finding)

            rec = EvidenceRecord(
                evidence_id=ev_id,
                source_type="event",
                service=ev["service"],
                timestamp=ev["timestamp"],
                description=f"Operational event [{ev['event_type']}]: {ev['description']}",
                support_type="supports",
                confidence_weight=0.9 if ev["event_type"] in ["DEPLOYMENT", "CONFIG_CHANGE"] else 0.7,
                limitations="Operational events logged via automated CI/CD and monitoring hooks."
            )
            state.add_evidence(rec)
            evidence_ids.append(ev_id)

        state.event_findings = event_findings

        # Tool 2: count_log_patterns
        patterns = count_log_patterns(self.logs_df, inc_id, start_time=i_window[0], end_time=i_window[1])
        tools_called.append({
            "tool": "count_log_patterns",
            "inputs": {"incident_id": inc_id, "start_time": i_window[0], "end_time": i_window[1]},
            "output": f"Found {len(patterns)} distinct error/warning clusters in incident logs."
        })

        for idx, pat in enumerate(patterns, start=1):
            primary_svc = pat["services"][0] if pat["services"] else "unknown"
            ev_id = f"LOG-{primary_svc[:3].upper()}-{idx:02d}"
            
            # Apply safety layer sanitization on sample log message
            clean_sample = sanitize_log_content(pat["sample_message"])

            finding = LogFinding(
                pattern=pat["pattern_name"],
                service=", ".join(pat["services"]),
                level=pat["log_level"],
                count=pat["count"],
                sample_message=clean_sample,
                evidence_id=ev_id,
                first_seen=pat.get("first_seen")
            )
            log_findings.append(finding)

            rec = EvidenceRecord(
                evidence_id=ev_id,
                source_type="log",
                service=primary_svc,
                timestamp=pat.get("first_seen"),
                description=f"Log cluster '{pat['pattern_name']}' ({pat['count']} occurrences, {pat['log_level']}) on {', '.join(pat['services'])}. Sample: \"{clean_sample}\"",
                support_type="supports",
                confidence_weight=0.85,
                limitations="Logs are untrusted telemetry; messages parsed as evidence, never executed."
            )
            state.add_evidence(rec)
            evidence_ids.append(ev_id)

        state.log_findings = log_findings

        duration = (time.time() - start_time) * 1000.0
        trace = AgentTrace(
            agent_name="Log and Event Analyst",
            role_description=self.role_description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tools_called=tools_called,
            findings_summary=f"Cataloged {len(event_findings)} operational events and {len(log_findings)} error log patterns. Sanitized all untrusted message payloads.",
            evidence_ids_generated=evidence_ids,
            decisions="Generated log & event evidence records; flagged deployment and failure signatures.",
            duration_ms=round(duration, 2)
        )
        state.add_trace(trace)
        return log_findings
