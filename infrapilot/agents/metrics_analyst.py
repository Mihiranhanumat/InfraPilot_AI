"""
Metrics Analyst Agent.
Executes telemetry metrics tools, detects baseline anomalies, finds earliest metric onset,
and registers verifiable evidence IDs into the incident state.
"""
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd
from infrapilot.state import IncidentState
from infrapilot.schemas import MetricFinding, EvidenceRecord, AgentTrace
from infrapilot.telemetry.metrics_tools import (
    compare_to_baseline,
    rank_anomalies,
    find_first_anomaly,
    get_metric_series
)

class MetricsAnalyst:
    def __init__(self, metrics_df: pd.DataFrame):
        self.metrics_df = metrics_df
        self.role_description = "Evaluates metric time series, flags anomalies vs baseline, and detects earliest onset."

    def run(self, state: IncidentState) -> List[MetricFinding]:
        start_time = time.time()
        tools_called = []
        evidence_ids = []
        findings: List[MetricFinding] = []

        inc_id = state.incident_id
        b_window = tuple(state.scenario_info.baseline_window)
        i_window = tuple(state.scenario_info.incident_window)

        # Tool 1: rank_anomalies
        anomalies_raw = rank_anomalies(self.metrics_df, inc_id, b_window, i_window)
        tools_called.append({
            "tool": "rank_anomalies",
            "inputs": {"incident_id": inc_id, "baseline_window": b_window, "incident_window": i_window},
            "output": f"Detected {len(anomalies_raw)} anomalous metric series."
        })

        # Tool 2: find_first_anomaly
        first_anom = find_first_anomaly(self.metrics_df, inc_id, b_window, i_window)
        tools_called.append({
            "tool": "find_first_anomaly",
            "inputs": {"incident_id": inc_id},
            "output": f"Earliest anomaly identified on {first_anom['service']} ({first_anom['metric_name']}) at {first_anom.get('first_anomaly_time')}" if first_anom else "No timed anomaly found."
        })

        # Check for missing telemetry (crucial for Scenario D)
        target_svcs = state.plan.target_services if state.plan else ["database", "order_api"]
        missing_services = []
        for svc in target_svcs:
            series = get_metric_series(self.metrics_df, inc_id, service=svc)
            # Check if empty or if data is cut short during incident window
            if series.empty:
                missing_services.append(svc)
            else:
                max_ts = series["timestamp"].max()
                if max_ts < pd.to_datetime(i_window[1]) - pd.Timedelta(minutes=5):
                    missing_services.append(f"{svc} (dropout after {max_ts.strftime('%H:%M')})")

        if missing_services:
            ev_id = f"METRIC-GAP-{inc_id[-4:]}"
            rec = EvidenceRecord(
                evidence_id=ev_id,
                source_type="metric",
                service=", ".join(missing_services),
                description=f"Telemetry dropout detected: metrics missing or truncated during incident window for {', '.join(missing_services)}.",
                support_type="contradicts",
                confidence_weight=0.8,
                limitations="Lack of full metric telemetry impairs automated root cause confidence."
            )
            state.add_evidence(rec)
            evidence_ids.append(ev_id)

        # Register findings & evidence
        idx = 1
        for a in anomalies_raw:
            svc = a["service"]
            m_name = a["metric_name"]
            ev_id = f"METRIC-{svc[:3].upper()}-{idx:02d}"
            
            # Formulate finding
            finding = MetricFinding(
                metric_name=m_name,
                service=svc,
                baseline_value=a["baseline_mean"],
                incident_value=a["incident_mean"],
                change_pct=a["change_pct"],
                is_anomaly=True,
                anomaly_score=a["anomaly_score"],
                unit=a["unit"],
                evidence_id=ev_id,
                first_anomaly_time=a.get("first_anomaly_time")
            )
            findings.append(finding)

            # Register evidence record
            desc = (
                f"{svc} {m_name} rose from baseline {a['baseline_mean']}{a['unit']} to {a['incident_mean']}{a['unit']} "
                f"({'+' if a['change_pct'] > 0 else ''}{a['change_pct']}%), earliest onset {a.get('first_anomaly_time')}."
            )
            rec = EvidenceRecord(
                evidence_id=ev_id,
                source_type="metric",
                service=svc,
                timestamp=a.get("first_anomaly_time"),
                description=desc,
                support_type="supports",
                confidence_weight=round(a["anomaly_score"], 2),
                limitations="Synthetically sampled metrics over 1-minute intervals."
            )
            state.add_evidence(rec)
            evidence_ids.append(ev_id)
            idx += 1

        state.metrics_findings = findings

        duration = (time.time() - start_time) * 1000.0
        trace = AgentTrace(
            agent_name="Metrics Analyst",
            role_description=self.role_description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tools_called=tools_called,
            findings_summary=f"Discovered {len(findings)} metric anomalies across services. Earliest breach: {first_anom['service']} ({first_anom['metric_name']}) at {first_anom.get('first_anomaly_time')}." if first_anom else f"Discovered {len(findings)} anomalies.",
            evidence_ids_generated=evidence_ids,
            decisions="Evidence recorded with baseline comparison deltas.",
            duration_ms=round(duration, 2)
        )
        state.add_trace(trace)
        return findings
