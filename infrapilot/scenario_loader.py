"""
Scenario and Telemetry Data Loader for InfraPilot AI.
"""
import json
from typing import List, Dict, Any, Optional
import pandas as pd
from config.settings import (
    SERVICES_CSV,
    METRICS_CSV,
    LOGS_CSV,
    EVENTS_CSV,
    SCENARIOS_JSON,
)
from infrapilot.schemas import ScenarioMetadata

class ScenarioLoader:
    def __init__(self):
        self._scenarios: Optional[List[Dict[str, Any]]] = None

    def list_scenarios(self) -> List[Dict[str, Any]]:
        if self._scenarios is None:
            with open(SCENARIOS_JSON, "r", encoding="utf-8") as f:
                self._scenarios = json.load(f)
        return self._scenarios

    def get_scenario_metadata(self, incident_id: str) -> ScenarioMetadata:
        scenarios = self.list_scenarios()
        for sc in scenarios:
            if sc["incident_id"] == incident_id:
                return ScenarioMetadata(
                    incident_id=sc["incident_id"],
                    title=sc["title"],
                    severity=sc["severity"],
                    incident_summary=sc["incident_summary"],
                    affected_services=sc["affected_services"],
                    baseline_window=sc["baseline_window"],
                    incident_window=sc["incident_window"],
                    expected_cause_family=sc.get("expected_cause_family"),
                    distractor_note=sc.get("distractor_note"),
                )
        raise ValueError(f"Incident {incident_id} not found in {SCENARIOS_JSON}")

    def load_services(self) -> pd.DataFrame:
        return pd.read_csv(SERVICES_CSV)

    def load_metrics(self) -> pd.DataFrame:
        df = pd.read_csv(METRICS_CSV)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def load_logs(self) -> pd.DataFrame:
        df = pd.read_csv(LOGS_CSV)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def load_events(self) -> pd.DataFrame:
        df = pd.read_csv(EVENTS_CSV)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

loader = ScenarioLoader()
