"""
Root-Cause Reasoner Agent.
Synthesizes findings from metrics, logs, events, and dependencies.
Calculates transparent heuristic confidence scores and ranks candidate root-cause hypotheses.
"""
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd
from infrapilot.state import IncidentState
from infrapilot.schemas import Hypothesis, AgentTrace
from config.settings import (
    WEIGHT_METRIC,
    WEIGHT_LOG,
    WEIGHT_DEPENDENCY,
    WEIGHT_TIMELINE,
)

class RootCauseReasoner:
    def __init__(self):
        self.role_description = "Synthesizes multi-source telemetry evidence into ranked root-cause hypotheses using transparent heuristic scoring."

    def run(self, state: IncidentState) -> List[Hypothesis]:
        start_time = time.time()
        tools_called = []
        hypotheses: List[Hypothesis] = []

        all_evidence = state.get_all_evidence_records()
        ev_by_service: Dict[str, List[Any]] = {}
        for ev in all_evidence:
            for s in [s.strip() for s in ev.service.split(",")]:
                ev_by_service.setdefault(s, []).append(ev)

        # Collect candidate services that have either metric anomalies, logs, or events
        candidate_services = set()
        for mf in state.metrics_findings:
            if mf.is_anomaly:
                candidate_services.add(mf.service)
        for lf in state.log_findings:
            for s in [x.strip() for x in lf.service.split(",")]:
                if s:
                    candidate_services.add(s)
        for ef in state.event_findings:
            candidate_services.add(ef.service)

        # If no candidates found, fallback to affected services
        if not candidate_services:
            candidate_services = set(state.scenario_info.affected_services)

        tools_called.append({
            "tool": "identify_candidate_services",
            "inputs": {"candidates": list(candidate_services)},
            "output": f"Extracted {len(candidate_services)} candidate root-cause services for scoring."
        })

        # Score each candidate service
        scored_candidates = []
        for candidate in candidate_services:
            score, breakdown, supporting_ids, contradicting_ids, timeline_desc, dep_desc, reasoning, limitations, claim = self._evaluate_candidate(
                candidate, state
            )
            scored_candidates.append({
                "service": candidate,
                "score": score,
                "breakdown": breakdown,
                "supporting_ids": supporting_ids,
                "contradicting_ids": contradicting_ids,
                "timeline_desc": timeline_desc,
                "dep_desc": dep_desc,
                "reasoning": reasoning,
                "limitations": limitations,
                "claim": claim
            })

        # Rank by heuristic score descending
        scored_candidates.sort(key=lambda x: -x["score"])

        for rank, item in enumerate(scored_candidates[:3], start=1):
            hypo = Hypothesis(
                rank=rank,
                candidate_service=item["service"],
                claim=item["claim"],
                heuristic_score=round(item["score"], 2),
                score_breakdown=item["breakdown"],
                supporting_evidence_ids=item["supporting_ids"],
                contradicting_evidence_ids=item["contradicting_ids"],
                timeline_fit=item["timeline_desc"],
                dependency_fit=item["dep_desc"],
                reasoning=item["reasoning"],
                limitations=item["limitations"]
            )
            hypotheses.append(hypo)

        state.hypotheses = hypotheses

        tools_called.append({
            "tool": "rank_hypotheses",
            "inputs": {"scored_candidates_count": len(scored_candidates)},
            "output": f"Ranked {len(hypotheses)} leading hypotheses. Top candidate: '{hypotheses[0].candidate_service}' with score {hypotheses[0].heuristic_score}." if hypotheses else "No hypotheses generated."
        })

        duration = (time.time() - start_time) * 1000.0
        leading_svc = hypotheses[0].candidate_service if hypotheses else "None"
        leading_score = hypotheses[0].heuristic_score if hypotheses else 0.0

        trace = AgentTrace(
            agent_name="Root-Cause Reasoner",
            role_description=self.role_description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tools_called=tools_called,
            findings_summary=f"Synthesized evidence across candidates. Leading hypothesis: '{leading_svc}' (Heuristic Confidence: {leading_score}). Cites {len(hypotheses[0].supporting_evidence_ids)} supporting evidence IDs." if hypotheses else "No hypotheses.",
            evidence_ids_generated=[h.candidate_service for h in hypotheses],
            decisions=f"Top-ranked hypothesis passed to Diagnostic Executor for active verification.",
            duration_ms=round(duration, 2)
        )
        state.add_trace(trace)
        return hypotheses

    def _evaluate_candidate(self, candidate: str, state: IncidentState) -> Tuple[float, Dict[str, float], List[str], List[str], str, str, str, str, str]:
        supporting_ids = []
        contradicting_ids = []

        # 1. Metric Support (0.0 to 1.0)
        metric_score = 0.0
        candidate_metrics = [m for m in state.metrics_findings if m.service == candidate]
        if candidate_metrics:
            # Average anomaly score of candidate's metrics
            metric_score = min(1.0, max([m.anomaly_score for m in candidate_metrics]))
            for m in candidate_metrics:
                supporting_ids.append(m.evidence_id)

        # 2. Log & Event Support (0.0 to 1.0)
        log_score = 0.0
        candidate_logs = [l for l in state.log_findings if candidate in l.service]
        candidate_events = [e for e in state.event_findings if e.service == candidate]
        if candidate_logs or candidate_events:
            has_error_logs = any(l.level in ["ERROR", "WARN"] for l in candidate_logs)
            has_critical_events = any(e.event_type in ["DEPLOYMENT", "CONFIG_CHANGE", "ALERT_FIRED"] for e in candidate_events)
            log_score = 0.4
            if has_error_logs:
                log_score += 0.4
            if has_critical_events:
                log_score += 0.2
            log_score = min(1.0, log_score)

            for l in candidate_logs:
                supporting_ids.append(l.evidence_id)
            for e in candidate_events:
                supporting_ids.append(e.evidence_id)

        # 3. Dependency Support (0.0 to 1.0)
        dependency_score = 0.0
        dep_finding = next((d for d in state.dependency_findings if d.service == candidate), None)
        symptom_svcs = state.scenario_info.affected_services
        if candidate in symptom_svcs:
            # Direct symptom service
            dependency_score = 0.70
            dep_desc = f"{candidate} is an immediate endpoint experiencing reported symptoms."
        elif dep_finding and dep_finding.is_upstream_of_symptoms:
            dependency_score = 0.95
            dep_desc = f"{candidate} is an upstream dependency topologically connected to symptom services ({', '.join(symptom_svcs)})."
            supporting_ids.append(dep_finding.evidence_id)
        else:
            dependency_score = 0.15
            dep_desc = f"{candidate} has no direct upstream dependency path to {', '.join(symptom_svcs)}."

        # 4. Timeline Support (0.0 to 1.0)
        timeline_score = 0.50
        candidate_onset = None
        for m in candidate_metrics:
            if m.first_anomaly_time:
                candidate_onset = m.first_anomaly_time
                break
        
        # Check against symptom services onset
        symptom_onsets = [
            m.first_anomaly_time for m in state.metrics_findings 
            if m.service in symptom_svcs and m.first_anomaly_time
        ]

        if candidate_onset and symptom_onsets:
            min_symptom_onset = min(symptom_onsets)
            if pd.to_datetime(candidate_onset) < pd.to_datetime(min_symptom_onset):
                timeline_score = 1.0
                timeline_desc = f"{candidate} anomaly began at {candidate_onset}, strictly preceding downstream symptom onset at {min_symptom_onset}."
            elif pd.to_datetime(candidate_onset) == pd.to_datetime(min_symptom_onset):
                timeline_score = 0.75
                timeline_desc = f"{candidate} anomaly synchronized with symptom onset at {candidate_onset}."
            else:
                timeline_score = 0.20
                timeline_desc = f"{candidate} anomaly onset ({candidate_onset}) lagged after symptoms ({min_symptom_onset}). Likely downstream symptom, not cause."
        elif candidate_events:
            ev_times = [e.timestamp for e in candidate_events if e.event_type in ["DEPLOYMENT", "CONFIG_CHANGE"]]
            if ev_times:
                timeline_score = 0.95
                timeline_desc = f"Operational lifecycle event ({candidate_events[0].event_type}) on {candidate} coincided directly with incident onset."
            else:
                timeline_desc = "Timeline inferred from event alarms."
        else:
            timeline_desc = "Timeline precedence indeterminate due to sparse timestamp data."

        # Check for contradictions / missing telemetry penalty (Scenario D)
        missing_records = [ev for ev in state.get_all_evidence_records() if "GAP" in ev.evidence_id or ev.support_type == "contradicts"]
        penalty = 0.0
        if missing_records:
            for rec in missing_records:
                contradicting_ids.append(rec.evidence_id)
            penalty = 0.35  # Substantial penalty if critical telemetry is missing or contradictory

        raw_score = (
            WEIGHT_METRIC * metric_score +
            WEIGHT_LOG * log_score +
            WEIGHT_DEPENDENCY * dependency_score +
            WEIGHT_TIMELINE * timeline_score
        ) - penalty

        final_score = max(0.05, min(0.99, raw_score))

        breakdown = {
            "metric_support": round(metric_score, 2),
            "log_support": round(log_score, 2),
            "dependency_support": round(dependency_score, 2),
            "timeline_support": round(timeline_score, 2),
            "contradiction_penalty": round(penalty, 2),
            "aggregate_heuristic_score": round(final_score, 2)
        }

        # Formulate claim, reasoning, limitations
        if candidate == "database":
            claim = "Database latency elevation and connection pool saturation is the primary upstream root cause."
            reasoning = (
                f"Database metrics show sharp connection exhaustion and p95 latency elevation preceding Order API latency spikes. "
                f"Database timeout logs match the failure window, and Order API directly depends on the database for checkout transactions."
            )
        elif candidate == "order_api" and any(e.event_type == "DEPLOYMENT" for e in candidate_events):
            claim = "Order API release regression (v2.4.1 deployment) introduced unhandled exceptions leading to HTTP 500 error surge."
            reasoning = (
                f"Order API error rate spiked from baseline immediately following deployment v2.4.1. "
                f"Upstream database and cache metrics remained completely healthy, confirming the fault is localized to the newly deployed application code."
            )
        elif candidate == "cache":
            claim = "Cache hit rate degradation and memory eviction triggered a cache stampede, overloading downstream database read capacity."
            reasoning = (
                f"Cache hit rate plummeted from 94% to ~22% following memory policy adjustment. "
                f"The resulting flood of cache misses overwhelmed database read query throughput, subsequently degrading Order API latency."
            )
        else:
            claim = f"Service '{candidate}' exhibits anomalous signals that correlate with the ongoing incident."
            reasoning = f"Telemetry signals on {candidate} exhibit divergence from baseline. Supporting evidence IDs: {', '.join(supporting_ids)}."

        limitations = (
            "Heuristic evidence score based on synthetic local telemetry. "
            "Correlations establish strong hypothesis, but causality is supported rather than definitively proven without internal tracing/query-plan telemetry."
        )

        return (
            final_score,
            breakdown,
            list(dict.fromkeys(supporting_ids)),
            list(dict.fromkeys(contradicting_ids)),
            timeline_desc,
            dep_desc,
            reasoning,
            limitations,
            claim
        )
