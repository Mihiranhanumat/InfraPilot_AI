"""
Diagnostic Executor Agent.
Executes targeted, strictly read-only diagnostics to test the leading hypothesis.
Never mutates infrastructure, runs shell commands, or alters cloud resources.
"""
import time
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from infrapilot.state import IncidentState
from infrapilot.schemas import DiagnosticResult, EvidenceRecord, AgentTrace
from infrapilot.telemetry.diagnostic_tools import (
    compare_metric_timelines,
    verify_dependency_viability,
    compare_event_window_impact,
    verify_log_error_correlation
)

class DiagnosticExecutor:
    def __init__(self, metrics_df: pd.DataFrame, logs_df: pd.DataFrame, services_df: pd.DataFrame, events_df: pd.DataFrame):
        self.metrics_df = metrics_df
        self.logs_df = logs_df
        self.services_df = services_df
        self.events_df = events_df
        self.role_description = "Runs safe, read-only diagnostic checks to stress-test the leading root-cause hypothesis."

    def run(self, state: IncidentState) -> List[DiagnosticResult]:
        start_time = time.time()
        tools_called = []
        diagnostics: List[DiagnosticResult] = []
        evidence_ids = []

        leading = state.leading_hypothesis
        if not leading:
            trace = AgentTrace(
                agent_name="Diagnostic Executor",
                role_description=self.role_description,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                tools_called=[],
                findings_summary="Skipped diagnostics: No hypothesis provided.",
                evidence_ids_generated=[],
                decisions="Halted diagnostics.",
                duration_ms=0.0
            )
            state.add_trace(trace)
            return []

        cand_svc = leading.candidate_service
        symptom_svcs = state.scenario_info.affected_services
        inc_id = state.incident_id
        b_win = tuple(state.scenario_info.baseline_window)
        i_win = tuple(state.scenario_info.incident_window)

        # Test 1: Topological Viability
        dep_diag = verify_dependency_viability(self.services_df, cand_svc, symptom_svcs)
        tools_called.append({
            "tool": "verify_dependency_viability",
            "inputs": {"candidate": cand_svc, "symptom_services": symptom_svcs},
            "output": dep_diag["details"]
        })
        diag1 = DiagnosticResult(
            test_name="Topological Viability Test",
            target_hypothesis=leading.claim,
            passed=dep_diag["passed"],
            details=dep_diag["details"],
            evidence_ids=[ev for ev in leading.supporting_evidence_ids if "DEP" in ev]
        )
        diagnostics.append(diag1)

        # Test 2: Timeline Precedence (if candidate is upstream of symptoms)
        if cand_svc not in symptom_svcs and symptom_svcs:
            time_diag = compare_metric_timelines(
                self.metrics_df, inc_id,
                upstream_service=cand_svc,
                upstream_metric="p95_latency_ms" if cand_svc != "cache" else "cache_hit_rate_pct",
                downstream_service=symptom_svcs[0],
                downstream_metric="p95_latency_ms",
                baseline_window=b_win,
                incident_window=i_win
            )
            tools_called.append({
                "tool": "compare_metric_timelines",
                "inputs": {"upstream": cand_svc, "downstream": symptom_svcs[0]},
                "output": time_diag["details"]
            })
            diag2 = DiagnosticResult(
                test_name="Timeline Precedence Test",
                target_hypothesis=leading.claim,
                passed=time_diag["passed"],
                details=time_diag["details"],
                evidence_ids=[ev for ev in leading.supporting_evidence_ids if "METRIC" in ev]
            )
            diagnostics.append(diag2)

        # Test 3: Event Window Impact (if deployment or config change event on candidate)
        cand_events = [e for e in state.event_findings if e.service == cand_svc]
        if cand_events:
            for ev in cand_events:
                if ev.event_type in ["DEPLOYMENT", "CONFIG_CHANGE"]:
                    ev_diag = compare_event_window_impact(self.metrics_df, inc_id, cand_svc, ev.timestamp)
                    tools_called.append({
                        "tool": "compare_event_window_impact",
                        "inputs": {"service": cand_svc, "event_timestamp": ev.timestamp},
                        "output": ev_diag["details"]
                    })
                    diag3 = DiagnosticResult(
                        test_name=f"Event Window Impact ({ev.event_type})",
                        target_hypothesis=leading.claim,
                        passed=ev_diag["passed"],
                        details=ev_diag["details"],
                        evidence_ids=[ev.evidence_id]
                    )
                    diagnostics.append(diag3)
                    break

        # Test 4: Correlated Log Search
        log_regex = "timeout|error|exception|saturated|eviction"
        log_diag = verify_log_error_correlation(self.logs_df, inc_id, cand_svc, log_regex, i_win[0])
        tools_called.append({
            "tool": "verify_log_error_correlation",
            "inputs": {"service": cand_svc, "query_regex": log_regex, "start_time": i_win[0]},
            "output": log_diag["details"]
        })
        diag4 = DiagnosticResult(
            test_name="Log Correlation Verification",
            target_hypothesis=leading.claim,
            passed=log_diag["passed"],
            details=log_diag["details"],
            evidence_ids=[ev for ev in leading.supporting_evidence_ids if "LOG" in ev]
        )
        diagnostics.append(diag4)

        # Register summary evidence
        ev_id = f"DIAG-{cand_svc[:3].upper()}-01"
        passed_count = sum(1 for d in diagnostics if d.passed)
        rec = EvidenceRecord(
            evidence_id=ev_id,
            source_type="diagnostic",
            service=cand_svc,
            description=f"Read-only diagnostic battery completed: {passed_count}/{len(diagnostics)} active checks passed for hypothesis '{leading.claim}'.",
            support_type="supports" if passed_count >= len(diagnostics) - 1 else "neutral",
            confidence_weight=0.9,
            limitations="Non-intrusive historical window diagnostics only."
        )
        state.add_evidence(rec)
        evidence_ids.append(ev_id)

        state.diagnostics = diagnostics

        duration = (time.time() - start_time) * 1000.0
        trace = AgentTrace(
            agent_name="Diagnostic Executor",
            role_description=self.role_description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tools_called=tools_called,
            findings_summary=f"Executed {len(diagnostics)} read-only diagnostic tests against '{cand_svc}'. Passed: {passed_count}/{len(diagnostics)}.",
            evidence_ids_generated=evidence_ids,
            decisions="Diagnostic outputs registered for validation by Critic Agent.",
            duration_ms=round(duration, 2)
        )
        state.add_trace(trace)
        return diagnostics
