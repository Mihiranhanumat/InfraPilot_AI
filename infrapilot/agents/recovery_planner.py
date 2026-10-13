"""
Recovery Planner Agent.
Formulates safe, reversible, human-reviewed recovery recommendations and verification checks.
Enforces that all actions are advisory recommendations only.
"""
import time
from datetime import datetime
from typing import List, Dict, Any
from infrapilot.state import IncidentState
from infrapilot.schemas import RecoveryRecommendation, AgentTrace
from infrapilot.safety.policy import validate_all_recommendations

class RecoveryPlanner:
    def __init__(self):
        self.role_description = "Formulates prioritized, reversible next steps with mandatory human sign-off."

    def run(self, state: IncidentState) -> List[RecoveryRecommendation]:
        start_time = time.time()
        tools_called = []
        raw_recommendations: List[RecoveryRecommendation] = []

        leading = state.leading_hypothesis
        cand_svc = leading.candidate_service if leading else "unknown"

        tools_called.append({
            "tool": "formulate_remediation_steps",
            "inputs": {"candidate_service": cand_svc, "validation_passed": state.validation.passed if state.validation else False},
            "output": f"Generating safe, non-destructive recommendations tailored to {cand_svc}."
        })

        if cand_svc == "database":
            raw_recommendations.extend([
                RecoveryRecommendation(
                    step_number=1,
                    action="Inspect active database queries and slow query logs for unindexed scans or connection pool locks.",
                    category="QUERY_INVESTIGATION",
                    target_service="database",
                    rationale="Pinpoint long-running blocking queries causing thread saturation without restarting the cluster.",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Observe active connection count drop below 70% threshold in monitoring dashboard."
                ),
                RecoveryRecommendation(
                    step_number=2,
                    action="Review database connection pool settings and HikariCP maximumPoolSize across Order API worker instances.",
                    category="CONNECTION_POOL_TUNING",
                    target_service="order_api",
                    rationale="Prevent connection exhaustion cascades while queries are being optimized.",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Verify Order API connection wait time drops below 50ms."
                ),
                RecoveryRecommendation(
                    step_number=3,
                    action="Compare recent database schema changes or index migrations against incident onset timestamp.",
                    category="CONFIGURATION_AUDIT",
                    target_service="database",
                    rationale="Rule out inadvertent index drops or locks introduced by automated migration jobs.",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Confirm query execution plan cost matches pre-incident baseline."
                ),
                RecoveryRecommendation(
                    step_number=4,
                    action="Monitor downstream Order API p95 latency and HTTP 504 error rate after authorized engineer intervention.",
                    category="DOWNSTREAM_MONITORING",
                    target_service="order_api",
                    rationale="Ensure recovery propagates downstream to restore end-to-end checkout functionality.",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Confirm Order API p95 latency stabilizes below 60ms and error rate < 0.2%."
                )
            ])
        elif cand_svc == "order_api":
            raw_recommendations.extend([
                RecoveryRecommendation(
                    step_number=1,
                    action="Inspect git diff and release commit history for deployment v2.4.1 (OrderValidator.java:142).",
                    category="DEPLOYMENT_ROLLBACK_VERIFICATION",
                    target_service="order_api",
                    rationale="Isolate the NullPointerException introduced in discount code validation logic.",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Confirm regression reproduction in staging environment."
                ),
                RecoveryRecommendation(
                    step_number=2,
                    action="Execute controlled deployment rollback to previous stable artifact v2.4.0 via CI/CD pipeline.",
                    category="DEPLOYMENT_ROLLBACK_VERIFICATION",
                    target_service="order_api",
                    rationale="Fastest path to restore production checkout availability while hotfix is coded.",
                    risk_level="MEDIUM",
                    is_reversible=True,
                    post_verification_check="Verify HTTP 500 errors subside to 0% immediately following rollback pod rotation."
                ),
                RecoveryRecommendation(
                    step_number=3,
                    action="Monitor Order API ingress error rate and frontend checkout completions post-rollback.",
                    category="DOWNSTREAM_MONITORING",
                    target_service="order_api",
                    rationale="Ensure users can place orders without errors.",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Check frontend checkout conversion metrics return to baseline."
                )
            ])
        elif cand_svc == "cache":
            raw_recommendations.extend([
                RecoveryRecommendation(
                    step_number=1,
                    action="Inspect Redis cache memory usage, key eviction rates, and maxmemory-policy settings.",
                    category="CACHE_POLICY_REVIEW",
                    target_service="cache",
                    rationale="Determine if keys were aggressively evicted prematurely, causing read stampede.",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Verify eviction rate drops to near zero."
                ),
                RecoveryRecommendation(
                    step_number=2,
                    action="Enable read request coalescing / singleflight in Order API to mitigate stampede load on database.",
                    category="CONFIGURATION_AUDIT",
                    target_service="order_api",
                    rationale="Prevent redundant parallel queries to database while cache warms.",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Observe database CPU utilization drops below 40%."
                ),
                RecoveryRecommendation(
                    step_number=3,
                    action="Re-warm critical product catalog keys and monitor cache hit ratio.",
                    category="DOWNSTREAM_MONITORING",
                    target_service="cache",
                    rationale="Restores normal cache hit efficiency (>90%).",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Verify cache hit rate climbs above 90% and DB latency drops below 20ms."
                )
            ])
        else:
            raw_recommendations.extend([
                RecoveryRecommendation(
                    step_number=1,
                    action="Conduct manual telemetry triage and verify telemetry agent health for missing services.",
                    category="CONFIGURATION_AUDIT",
                    target_service=cand_svc,
                    rationale="Automated diagnosis is inconclusive due to missing or conflicting telemetry.",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Restore full metrics streaming before taking operational action."
                ),
                RecoveryRecommendation(
                    step_number=2,
                    action="Require on-call SRE review before modifying any cloud resources or application state.",
                    category="DOWNSTREAM_MONITORING",
                    target_service=cand_svc,
                    rationale="Safety guardrail prevents unintended actions on ambiguous data.",
                    risk_level="LOW",
                    is_reversible=True,
                    post_verification_check="Engineering lead confirmation logged."
                )
            ])

        # Enforce safety policy across all recommendations
        safe_recommendations = validate_all_recommendations(raw_recommendations)
        state.recovery_plan = safe_recommendations

        duration = (time.time() - start_time) * 1000.0
        trace = AgentTrace(
            agent_name="Recovery Planner",
            role_description=self.role_description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tools_called=tools_called,
            findings_summary=f"Formulated {len(safe_recommendations)} advisory recommendations for {cand_svc}. All marked RECOMMENDATION_ONLY.",
            evidence_ids_generated=[],
            decisions="Strict read-only safety guardrails applied. Human sign-off required.",
            duration_ms=round(duration, 2)
        )
        state.add_trace(trace)
        return safe_recommendations
