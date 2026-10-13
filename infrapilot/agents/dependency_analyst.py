"""
Dependency Analyst Agent.
Investigates service topology, establishes upstream/downstream relationships,
and verifies structural failure propagation paths.
"""
import time
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from infrapilot.state import IncidentState
from infrapilot.schemas import DependencyFinding, EvidenceRecord, AgentTrace
from infrapilot.telemetry.dependency_tools import (
    build_dependency_graph,
    get_upstream_services,
    get_downstream_impact,
    check_path_exists,
)

class DependencyAnalyst:
    def __init__(self, services_df: pd.DataFrame):
        self.services_df = services_df
        self.role_description = "Evaluates service call graphs, verifies upstream dependencies and downstream blast radius."

    def run(self, state: IncidentState) -> List[DependencyFinding]:
        start_time = time.time()
        tools_called = []
        evidence_ids = []
        findings: List[DependencyFinding] = []

        affected_services = state.scenario_info.affected_services
        G = build_dependency_graph(self.services_df)
        all_services = list(G.nodes)

        tools_called.append({
            "tool": "build_dependency_graph",
            "inputs": {"services_count": len(all_services)},
            "output": f"Graph initialized with {len(all_services)} services and {G.number_of_edges()} dependency links."
        })

        idx = 1
        for svc in all_services:
            upstream = get_upstream_services(self.services_df, svc)
            downstream = get_downstream_impact(self.services_df, svc)
            
            # Check if this service is upstream of any affected symptom services
            is_upstream_of_symptoms = False
            paths = []
            for aff in affected_services:
                if aff == svc:
                    is_upstream_of_symptoms = True
                    paths.append(f"{svc} (direct symptom)")
                else:
                    has_path, path = check_path_exists(self.services_df, svc, aff)
                    if has_path:
                        is_upstream_of_symptoms = True
                        paths.append(" -> ".join(path))

            ev_id = f"DEP-{svc[:3].upper()}-{idx:02d}"
            finding = DependencyFinding(
                service=svc,
                upstream_of=downstream,  # services that call this service
                downstream_of=upstream,  # services this service calls
                is_upstream_of_symptoms=is_upstream_of_symptoms,
                path_to_symptoms=paths,
                criticality="critical" if svc in ["database", "order_api"] else "high",
                evidence_id=ev_id
            )
            findings.append(finding)

            # Generate evidence record if related to affected services
            if is_upstream_of_symptoms:
                desc = (
                    f"Topology verification: '{svc}' is an upstream dependency of symptom services ({', '.join(affected_services)}). "
                    f"Call paths: {'; '.join(paths) if paths else 'Direct'}."
                )
                rec = EvidenceRecord(
                    evidence_id=ev_id,
                    source_type="dependency",
                    service=svc,
                    description=desc,
                    support_type="supports",
                    confidence_weight=0.9,
                    limitations="Static service dependency configuration from services.csv."
                )
                state.add_evidence(rec)
                evidence_ids.append(ev_id)
            
            idx += 1

        state.dependency_findings = findings

        tools_called.append({
            "tool": "trace_upstream_dependencies",
            "inputs": {"symptom_services": affected_services},
            "output": f"Mapped {len(evidence_ids)} upstream dependency relationships linking to symptom endpoints."
        })

        duration = (time.time() - start_time) * 1000.0
        trace = AgentTrace(
            agent_name="Dependency Analyst",
            role_description=self.role_description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tools_called=tools_called,
            findings_summary=f"Evaluated {len(all_services)} services. Verified that degradation in upstream dependencies can cascade downstream to {', '.join(affected_services)}.",
            evidence_ids_generated=evidence_ids,
            decisions="Topological paths established; evidence registered for upstream candidates.",
            duration_ms=round(duration, 2)
        )
        state.add_trace(trace)
        return findings
