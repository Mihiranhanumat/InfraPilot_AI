"""
Reporting Agent.
Compiles comprehensive, evidence-grounded incident reports in Markdown and JSON formats.
Ensures explicit auditability, limitations disclosures, and safety notices.
"""
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from infrapilot.state import IncidentState
from infrapilot.schemas import IncidentReport, AgentTrace
from config.settings import REPORTS_DIR, SAFETY_DISCLAIMER

class ReportingAgent:
    def __init__(self):
        self.role_description = "Synthesizes complete multi-agent investigation into audit-ready Markdown and JSON reports."

    def run(self, state: IncidentState) -> IncidentReport:
        start_time = time.time()
        tools_called = []

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        leading = state.leading_hypothesis
        val = state.validation

        # Build IncidentReport object
        report = IncidentReport(
            incident_id=state.incident_id,
            title=state.scenario_info.title,
            generated_at=now_str,
            status=state.status,
            symptoms=[state.scenario_info.incident_summary],
            confidence_label="Heuristic Evidence Score (Transparent Multi-Source Metric)",
            leading_hypothesis=leading,
            all_hypotheses=state.hypotheses,
            evidence_trail=state.get_all_evidence_records(),
            diagnostics_summary=state.diagnostics,
            critic_decision=val.decision if val else "UNKNOWN",
            recovery_recommendations=state.recovery_plan,
            limitations_disclaimer=(
                "Synthetically generated local telemetry. Correlations establish strong hypotheses, "
                "but causality is supported rather than definitively proven. No production claims or absolute certainty guaranteed."
            ),
            safety_notice=SAFETY_DISCLAIMER
        )

        state.report = report

        # Export report files to reports/ directory
        md_content = self.generate_markdown(report)
        json_content = self.generate_json(report)

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        md_file = REPORTS_DIR / f"{state.incident_id}_investigation_report.md"
        json_file = REPORTS_DIR / f"{state.incident_id}_investigation_report.json"

        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)
        with open(json_file, "w", encoding="utf-8") as f:
            f.write(json_content)

        tools_called.append({
            "tool": "export_reports",
            "inputs": {"md_file": str(md_file), "json_file": str(json_file)},
            "output": f"Exported investigation report to Markdown and JSON formats in {REPORTS_DIR.name}/."
        })

        duration = (time.time() - start_time) * 1000.0
        trace = AgentTrace(
            agent_name="Reporting Agent",
            role_description=self.role_description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tools_called=tools_called,
            findings_summary=f"Generated final investigation report for {state.incident_id}. Saved to {md_file.name}.",
            evidence_ids_generated=[],
            decisions="Audit trail compiled. Report ready for engineering download.",
            duration_ms=round(duration, 2)
        )
        state.add_trace(trace)
        return report

    def generate_markdown(self, report: IncidentReport) -> str:
        leading = report.leading_hypothesis
        lead_claim = leading.claim if leading else "No conclusive hypothesis"
        lead_score = f"{leading.heuristic_score * 100:.1f}%" if leading else "N/A"
        lead_svc = leading.candidate_service if leading else "Unknown"

        lines = [
            f"# InfraPilot AI — Incident Investigation Report",
            f"**Incident ID:** `{report.incident_id}` | **Severity:** `{report.status}`",
            f"**Generated:** {report.generated_at}",
            f"**Investigation Status:** `{report.status}` (Critic Verdict: `{report.critic_decision}`)",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            f"- **Observed Symptoms:** {report.symptoms[0] if report.symptoms else 'N/A'}",
            f"- **Leading Hypothesis:** {lead_claim}",
            f"- **Identified Culprit Service:** `{lead_svc}`",
            f"- **Confidence Rating:** **{lead_score}** (*{report.confidence_label}*)",
            "",
            "---",
            "",
            "## 2. Hypothesis Ranking & Heuristic Scoring",
        ]

        for h in report.all_hypotheses:
            lines.append(f"### Rank {h.rank}: `{h.candidate_service}` — Score: {h.heuristic_score * 100:.1f}%")
            lines.append(f"- **Claim:** {h.claim}")
            lines.append(f"- **Reasoning:** {h.reasoning}")
            lines.append(f"- **Timeline Fit:** {h.timeline_fit}")
            lines.append(f"- **Dependency Fit:** {h.dependency_fit}")
            lines.append(f"- **Supporting Evidence IDs:** `{', '.join(h.supporting_evidence_ids)}`")
            if h.contradicting_evidence_ids:
                lines.append(f"- **Contradicting / Missing Evidence IDs:** `{', '.join(h.contradicting_evidence_ids)}`")
            lines.append(f"- **Heuristic Score Breakdown:**")
            for k, v in h.score_breakdown.items():
                lines.append(f"  - `{k}`: {v}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 3. Read-Only Diagnostic Validation",
        ])
        for d in report.diagnostics_summary:
            status_icon = "PASS" if d.passed else "FAIL"
            lines.append(f"- **[{status_icon}] {d.test_name}:** {d.details}")

        lines.extend([
            "",
            "---",
            "",
            "## 4. Evidence Trail",
            "| Evidence ID | Source | Service | Support | Description |",
            "|---|---|---|---|---|",
        ])
        for ev in report.evidence_trail:
            lines.append(f"| `{ev.evidence_id}` | {ev.source_type} | `{ev.service}` | {ev.support_type} | {ev.description} |")

        lines.extend([
            "",
            "---",
            "",
            "## 5. Recommended Recovery Next Steps",
            "> **NOTICE:** All actions are strictly advisory recommendations (`RECOMMENDATION_ONLY`). No automated mutations have been executed. Explicit human approval from an authorized engineer is required.",
            "",
        ])
        for r in report.recovery_recommendations:
            lines.append(f"### Step {r.step_number}: {r.action}")
            lines.append(f"- **Target Service:** `{r.target_service}` | **Category:** `{r.category}` | **Risk:** `{r.risk_level}`")
            lines.append(f"- **Rationale:** {r.rationale}")
            lines.append(f"- **Post-Verification Check:** {r.post_verification_check}")
            lines.append(f"- **Status:** `{r.status}` (Reversible: `{r.is_reversible}`)")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 6. Uncertainty, Limitations & Safety Disclaimers",
            f"- **Telemetry Limitations:** {report.limitations_disclaimer}",
            f"- **Safety Policy Enforcement:** {report.safety_notice}",
            "- **Human Review Gate:** Human engineers must inspect live telemetry and review these findings prior to executing operational runbooks.",
            ""
        ])

        return "\n".join(lines)

    def generate_json(self, report: IncidentReport) -> str:
        data = {
            "incident_id": report.incident_id,
            "title": report.title,
            "generated_at": report.generated_at,
            "status": report.status,
            "symptoms": report.symptoms,
            "critic_decision": report.critic_decision,
            "confidence_label": report.confidence_label,
            "leading_hypothesis": report.leading_hypothesis.to_dict() if report.leading_hypothesis else None,
            "all_hypotheses": [h.to_dict() for h in report.all_hypotheses],
            "evidence_trail": [ev.to_dict() for ev in report.evidence_trail],
            "diagnostics": [
                {"test_name": d.test_name, "passed": d.passed, "details": d.details, "evidence_ids": d.evidence_ids}
                for d in report.diagnostics_summary
            ],
            "recovery_recommendations": [r.to_dict() for r in report.recovery_recommendations],
            "limitations_disclaimer": report.limitations_disclaimer,
            "safety_notice": report.safety_notice
        }
        return json.dumps(data, indent=2)
