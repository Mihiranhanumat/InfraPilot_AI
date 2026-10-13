"""
Shared Incident State for InfraPilot AI.
"""
from typing import Dict, List, Optional
from infrapilot.schemas import (
    ScenarioMetadata,
    IncidentPlan,
    EvidenceRecord,
    MetricFinding,
    LogFinding,
    EventFinding,
    DependencyFinding,
    DiagnosticResult,
    Hypothesis,
    ValidationResult,
    RecoveryRecommendation,
    IncidentReport,
    AgentTrace,
)

class IncidentState:
    def __init__(self, incident_id: str, scenario_info: ScenarioMetadata):
        self.incident_id: str = incident_id
        self.scenario_info: ScenarioMetadata = scenario_info
        self.status: str = "Investigating"
        
        # Orchestrator and agent outputs
        self.plan: Optional[IncidentPlan] = None
        self.agent_traces: List[AgentTrace] = []
        self.evidence_store: Dict[str, EvidenceRecord] = {}
        
        # Telemetry findings
        self.metrics_findings: List[MetricFinding] = []
        self.log_findings: List[LogFinding] = []
        self.event_findings: List[EventFinding] = []
        self.dependency_findings: List[DependencyFinding] = []
        
        # Reasoning and verification
        self.hypotheses: List[Hypothesis] = []
        self.diagnostics: List[DiagnosticResult] = []
        self.validation: Optional[ValidationResult] = None
        self.retry_count: int = 0
        
        # Remediation and final report
        self.recovery_plan: List[RecoveryRecommendation] = []
        self.report: Optional[IncidentReport] = None

    def add_evidence(self, record: EvidenceRecord) -> str:
        """Register evidence with unique ID into centralized evidence store."""
        self.evidence_store[record.evidence_id] = record
        return record.evidence_id

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        return self.evidence_store.get(evidence_id)

    def add_trace(self, trace: AgentTrace) -> None:
        self.agent_traces.append(trace)

    def get_all_evidence_records(self) -> List[EvidenceRecord]:
        return list(self.evidence_store.values())

    @property
    def leading_hypothesis(self) -> Optional[Hypothesis]:
        return self.hypotheses[0] if self.hypotheses else None
