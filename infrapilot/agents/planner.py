"""
Incident Planner Agent.
Formulates the investigation checklist, identifies target services, and assigns data sources.
"""
import time
from datetime import datetime
from typing import List, Dict, Any
from infrapilot.state import IncidentState
from infrapilot.schemas import IncidentPlan, AgentTrace

class IncidentPlanner:
    def __init__(self):
        self.role_description = "Formulates targeted investigation checklist and defines inquiry vectors."

    def run(self, state: IncidentState) -> IncidentPlan:
        start_time = time.time()
        tools_called = []
        
        info = state.scenario_info
        
        # Tool call record: planning evaluation
        target_services = list(info.affected_services)
        # Always include core system dependencies for comprehensive coverage
        for svc in ["database", "order_api", "cache"]:
            if svc not in target_services:
                target_services.append(svc)

        tools_called.append({
            "tool": "plan_inquiry_scope",
            "inputs": {"affected_services": info.affected_services, "severity": info.severity},
            "output": f"Scoped investigation to {len(target_services)} target services."
        })

        investigation_questions = [
            f"Which service experienced the earliest metric anomaly between {info.baseline_window[1]} and {info.incident_window[0]}?",
            "Are there deployment, configuration, or alert events that coincide with symptom onset?",
            "Can upstream failure propagation explain the observed latency/error symptoms in the service dependency graph?",
            "Do log patterns corroborate timeouts, resource exhaustion, or unhandled exceptions?",
            "Are there contradictory signals or missing telemetry that would impede confidence?"
        ]

        plan = IncidentPlan(
            incident_id=info.incident_id,
            symptom_summary=info.incident_summary,
            target_services=target_services,
            investigation_questions=investigation_questions,
            assigned_data_sources=["metrics.csv", "logs.csv", "events.csv", "services.csv"]
        )

        duration = (time.time() - start_time) * 1000.0
        trace = AgentTrace(
            agent_name="Incident Planner",
            role_description=self.role_description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tools_called=tools_called,
            findings_summary=f"Established 5 investigation vectors across {len(target_services)} services ({', '.join(target_services)}).",
            evidence_ids_generated=[],
            decisions="Dispatched metrics, log, and dependency investigation tasks.",
            duration_ms=round(duration, 2)
        )
        state.add_trace(trace)
        state.plan = plan
        return plan
