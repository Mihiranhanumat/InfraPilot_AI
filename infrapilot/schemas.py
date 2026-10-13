"""
Data schemas for InfraPilot AI.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ScenarioMetadata:
    incident_id: str
    title: str
    severity: str
    incident_summary: str
    affected_services: List[str]
    baseline_window: List[str]
    incident_window: List[str]
    expected_cause_family: Optional[str] = None
    distractor_note: Optional[str] = None

@dataclass
class EvidenceRecord:
    evidence_id: str
    source_type: str  # metric, log, event, dependency, diagnostic
    service: str
    description: str
    support_type: str = "supports"  # supports, contradicts, neutral
    timestamp: Optional[str] = None
    confidence_weight: float = 1.0
    limitations: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "service": self.service,
            "description": self.description,
            "support_type": self.support_type,
            "timestamp": self.timestamp,
            "confidence_weight": self.confidence_weight,
            "limitations": self.limitations,
        }

@dataclass
class MetricFinding:
    metric_name: str
    service: str
    baseline_value: float
    incident_value: float
    change_pct: float
    is_anomaly: bool
    anomaly_score: float
    unit: str
    evidence_id: str
    first_anomaly_time: Optional[str] = None

@dataclass
class LogFinding:
    pattern: str
    service: str
    level: str
    count: int
    sample_message: str
    evidence_id: str
    event_type: Optional[str] = None
    first_seen: Optional[str] = None

@dataclass
class EventFinding:
    event_type: str
    service: str
    timestamp: str
    description: str
    evidence_id: str

@dataclass
class DependencyFinding:
    service: str
    upstream_of: List[str]
    downstream_of: List[str]
    is_upstream_of_symptoms: bool
    path_to_symptoms: List[str]
    criticality: str
    evidence_id: str

@dataclass
class DiagnosticResult:
    test_name: str
    target_hypothesis: str
    passed: bool
    details: str
    evidence_ids: List[str] = field(default_factory=list)

@dataclass
class Hypothesis:
    rank: int
    candidate_service: str
    claim: str
    heuristic_score: float
    score_breakdown: Dict[str, float]
    supporting_evidence_ids: List[str]
    contradicting_evidence_ids: List[str]
    timeline_fit: str
    dependency_fit: str
    reasoning: str
    limitations: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "candidate_service": self.candidate_service,
            "claim": self.claim,
            "heuristic_score": self.heuristic_score,
            "score_breakdown": self.score_breakdown,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "contradicting_evidence_ids": self.contradicting_evidence_ids,
            "timeline_fit": self.timeline_fit,
            "dependency_fit": self.dependency_fit,
            "reasoning": self.reasoning,
            "limitations": self.limitations,
        }

@dataclass
class ValidationResult:
    passed: bool
    decision: str  # PASS, REINVESTIGATE, HUMAN_REVIEW
    critique_notes: List[str]
    unsupported_claims: List[str]
    missing_evidence_flags: List[str]
    retry_recommended: bool = False

@dataclass
class RecoveryRecommendation:
    step_number: int
    action: str
    category: str
    target_service: str
    rationale: str
    risk_level: str  # LOW, MEDIUM, HIGH
    is_reversible: bool
    post_verification_check: str
    status: str = "RECOMMENDATION_ONLY"
    requires_human_approval: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "action": self.action,
            "category": self.category,
            "target_service": self.target_service,
            "rationale": self.rationale,
            "risk_level": self.risk_level,
            "is_reversible": self.is_reversible,
            "post_verification_check": self.post_verification_check,
            "status": self.status,
            "requires_human_approval": self.requires_human_approval,
        }

@dataclass
class IncidentPlan:
    incident_id: str
    symptom_summary: str
    target_services: List[str]
    investigation_questions: List[str]
    assigned_data_sources: List[str]

@dataclass
class AgentTrace:
    agent_name: str
    role_description: str
    timestamp: str
    tools_called: List[Dict[str, Any]]
    findings_summary: str
    evidence_ids_generated: List[str]
    decisions: str
    duration_ms: float

@dataclass
class IncidentReport:
    incident_id: str
    title: str
    generated_at: str
    status: str
    symptoms: List[str]
    confidence_label: str
    leading_hypothesis: Optional[Hypothesis]
    all_hypotheses: List[Hypothesis]
    evidence_trail: List[EvidenceRecord]
    diagnostics_summary: List[DiagnosticResult]
    critic_decision: str
    recovery_recommendations: List[RecoveryRecommendation]
    limitations_disclaimer: str
    safety_notice: str
