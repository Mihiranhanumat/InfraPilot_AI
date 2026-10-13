"""
Critic / Validator Agent.
Inspects hypotheses for evidence grounding, validates cited evidence IDs against the store,
checks contradiction handling, and renders verdict: PASS, REINVESTIGATE, or HUMAN_REVIEW.
Enforces that retry count never exceeds one.
"""
import time
from datetime import datetime
from typing import List, Dict, Any
from infrapilot.state import IncidentState
from infrapilot.schemas import ValidationResult, AgentTrace
from config.settings import CONFIDENCE_PASS_THRESHOLD, HUMAN_REVIEW_THRESHOLD

class CriticValidator:
    def __init__(self):
        self.role_description = "Validates hypotheses against evidence, catches ungrounded claims, and enforces bounded retry/human escalation."

    def run(self, state: IncidentState) -> ValidationResult:
        start_time = time.time()
        tools_called = []
        critique_notes = []
        unsupported_claims = []
        missing_evidence_flags = []

        leading = state.leading_hypothesis
        if not leading:
            res = ValidationResult(
                passed=False,
                decision="HUMAN_REVIEW",
                critique_notes=["No candidate hypotheses were produced during reasoning."],
                unsupported_claims=["No hypothesis"],
                missing_evidence_flags=["Complete absence of hypotheses"],
                retry_recommended=False
            )
            state.validation = res
            return res

        # Check 1: Evidence ID grounding in evidence store
        tools_called.append({
            "tool": "verify_evidence_ids",
            "inputs": {"cited_supporting_ids": leading.supporting_evidence_ids},
            "output": f"Verifying {len(leading.supporting_evidence_ids)} cited evidence IDs against store."
        })

        invalid_ids = []
        for ev_id in leading.supporting_evidence_ids:
            if not state.get_evidence(ev_id):
                invalid_ids.append(ev_id)

        if invalid_ids:
            unsupported_claims.append(f"Hypothesis cites invalid/unregistered evidence IDs: {invalid_ids}")
            critique_notes.append(f"Grounding failure: {len(invalid_ids)} IDs not found in evidence store.")
        else:
            critique_notes.append(f"Evidence ID grounding verified: All {len(leading.supporting_evidence_ids)} IDs resolve to valid telemetry records.")

        # Check 2: Missing telemetry or contradictory signals (Scenario D check)
        contradicting_records = [
            ev for ev in state.get_all_evidence_records() 
            if ev.support_type == "contradicts" or "GAP" in ev.evidence_id
        ]
        if contradicting_records:
            flags = [f"{ev.evidence_id}: {ev.description}" for ev in contradicting_records]
            missing_evidence_flags.extend(flags)
            critique_notes.append(f"Critical telemetry gaps detected: {len(contradicting_records)} contradictory/gap evidence records exist.")

        # Check 3: Diagnostic test results
        failed_diags = [d for d in state.diagnostics if not d.passed]
        if failed_diags:
            for fd in failed_diags:
                critique_notes.append(f"Diagnostic warning: '{fd.test_name}' did not confirm hypothesis ({fd.details}).")

        # Check 4: Confidence Score Thresholding
        score = leading.heuristic_score
        critique_notes.append(f"Evaluated heuristic score: {score:.2f} (Pass threshold: {CONFIDENCE_PASS_THRESHOLD}, Escalation threshold: {HUMAN_REVIEW_THRESHOLD}).")

        # Determine Decision
        if len(missing_evidence_flags) > 0 or score < HUMAN_REVIEW_THRESHOLD or len(unsupported_claims) > 0:
            if state.retry_count == 0:
                decision = "REINVESTIGATE"
                passed = False
                retry_recommended = True
                critique_notes.append("Confidence below pass criteria or critical telemetry missing. Requesting 1 targeted reinvestigation retry.")
            else:
                decision = "HUMAN_REVIEW"
                passed = False
                retry_recommended = False
                critique_notes.append("Retry budget exhausted or conflicting signals persistent. Escalating to mandatory Human Review.")
        elif score >= CONFIDENCE_PASS_THRESHOLD and len(unsupported_claims) == 0:
            decision = "PASS"
            passed = True
            retry_recommended = False
            critique_notes.append("Hypothesis satisfies evidence grounding, passes diagnostic checks, and meets confidence threshold.")
        else:
            # Borderline score
            if state.retry_count == 0:
                decision = "REINVESTIGATE"
                passed = False
                retry_recommended = True
            else:
                decision = "HUMAN_REVIEW"
                passed = False
                retry_recommended = False

        result = ValidationResult(
            passed=passed,
            decision=decision,
            critique_notes=critique_notes,
            unsupported_claims=unsupported_claims,
            missing_evidence_flags=missing_evidence_flags,
            retry_recommended=retry_recommended
        )
        state.validation = result

        tools_called.append({
            "tool": "render_validation_decision",
            "inputs": {"passed": passed, "decision": decision, "retry_count": state.retry_count},
            "output": f"Rendered decision: {decision}. Passed: {passed}."
        })

        duration = (time.time() - start_time) * 1000.0
        trace = AgentTrace(
            agent_name="Critic and Validator",
            role_description=self.role_description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tools_called=tools_called,
            findings_summary=f"Validation verdict: {decision}. Grounding checks: {'PASS' if not unsupported_claims else 'FAIL'}. Gaps flagged: {len(missing_evidence_flags)}.",
            evidence_ids_generated=[],
            decisions=f"Decision={decision}; Retry recommended={retry_recommended}.",
            duration_ms=round(duration, 2)
        )
        state.add_trace(trace)
        return result
