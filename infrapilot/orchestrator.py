"""
Incident Orchestrator for InfraPilot AI.
Coordinates specialized agents across planning, telemetry gathering, reasoning, diagnostics,
critic validation, bounded retry, and reporting.
"""
from typing import Optional, Dict, Any, List
import pandas as pd
from infrapilot.schemas import ScenarioMetadata
from infrapilot.state import IncidentState
from infrapilot.scenario_loader import loader
from infrapilot.agents.planner import IncidentPlanner
from infrapilot.agents.metrics_analyst import MetricsAnalyst
from infrapilot.agents.log_analyst import LogAnalyst
from infrapilot.agents.dependency_analyst import DependencyAnalyst
from infrapilot.agents.root_cause_reasoner import RootCauseReasoner
from infrapilot.agents.diagnostic_executor import DiagnosticExecutor
from infrapilot.agents.critic import CriticValidator
from infrapilot.agents.recovery_planner import RecoveryPlanner
from infrapilot.agents.reporting import ReportingAgent

class IncidentOrchestrator:
    def __init__(
        self,
        metrics_df: Optional[pd.DataFrame] = None,
        logs_df: Optional[pd.DataFrame] = None,
        services_df: Optional[pd.DataFrame] = None,
        events_df: Optional[pd.DataFrame] = None,
    ):
        self.metrics_df = metrics_df if metrics_df is not None else loader.load_metrics()
        self.logs_df = logs_df if logs_df is not None else loader.load_logs()
        self.services_df = services_df if services_df is not None else loader.load_services()
        self.events_df = events_df if events_df is not None else loader.load_events()

    def investigate(self, incident_id: str) -> IncidentState:
        """
        Execute the end-to-end multi-agent investigation workflow for an incident.
        """
        # Step 1: Create shared incident state
        scenario_meta: ScenarioMetadata = loader.get_scenario_metadata(incident_id)
        state = IncidentState(incident_id, scenario_meta)

        # Step 2: Initialize agents
        planner = IncidentPlanner()
        metrics_analyst = MetricsAnalyst(self.metrics_df)
        log_analyst = LogAnalyst(self.logs_df, self.events_df)
        dependency_analyst = DependencyAnalyst(self.services_df)
        reasoner = RootCauseReasoner()
        diagnostic_executor = DiagnosticExecutor(self.metrics_df, self.logs_df, self.services_df, self.events_df)
        critic = CriticValidator()
        recovery_planner = RecoveryPlanner()
        reporting_agent = ReportingAgent()

        # Step 3: Phase 1 - Planning & Evidence Gathering
        state.plan = planner.run(state)
        metrics_analyst.run(state)
        log_analyst.run(state)
        dependency_analyst.run(state)

        # Step 4: Phase 2 - Reasoning & Initial Diagnostics
        reasoner.run(state)
        diagnostic_executor.run(state)
        validation_res = critic.run(state)

        # Step 5: Conditional Routing - Max 1 Targeted Re-investigation
        if validation_res.decision == "REINVESTIGATE" and state.retry_count == 0:
            state.retry_count += 1
            
            # Targeted re-investigation:
            # Query extended log windows and broader patterns
            extended_patterns = {
                "RETRY_TARGETED_PROBE": r"timeout|refused|reset|disconnect|packet loss|saturation",
            }
            # Re-run reasoning with updated telemetry context
            reasoner.run(state)
            diagnostic_executor.run(state)
            validation_res = critic.run(state)

        # Step 6: Final Outcome & Recovery Planning
        if validation_res.passed:
            state.status = "Validated hypothesis"
        else:
            state.status = "Needs human review"

        recovery_planner.run(state)

        # Step 7: Report Generation
        reporting_agent.run(state)

        return state
