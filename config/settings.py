"""
InfraPilot AI - Configuration and Global Settings
"""
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"

SERVICES_CSV = DATA_DIR / "services.csv"
METRICS_CSV = DATA_DIR / "metrics.csv"
LOGS_CSV = DATA_DIR / "logs.csv"
EVENTS_CSV = DATA_DIR / "events.csv"
SCENARIOS_JSON = DATA_DIR / "scenarios.json"

# Anomaly Detection Heuristic Thresholds
LATENCY_ANOMALY_MULTIPLIER = 1.5
ERROR_RATE_THRESHOLD_PCT = 2.0
CPU_ANOMALY_THRESHOLD_PCT = 75.0
DB_CONN_THRESHOLD_PCT = 75.0
CACHE_HIT_DROP_THRESHOLD_PCT = 25.0

# Transparent Scoring Weights (normalized sum = 1.0)
WEIGHT_METRIC = 0.30
WEIGHT_LOG = 0.25
WEIGHT_DEPENDENCY = 0.25
WEIGHT_TIMELINE = 0.20

# Orchestrator Guardrails
MAX_RETRIES = 1
CONFIDENCE_PASS_THRESHOLD = 0.65
HUMAN_REVIEW_THRESHOLD = 0.60

# Safety Policy
SAFETY_DISCLAIMER = "SIMULATION ONLY: Read-only diagnostics. No real cloud resources or infrastructure commands are modified."
ALLOWLIST_RECOVERY_CATEGORIES = [
    "QUERY_INVESTIGATION",
    "CONNECTION_POOL_TUNING",
    "DEPLOYMENT_ROLLBACK_VERIFICATION",
    "CACHE_POLICY_REVIEW",
    "CONFIGURATION_AUDIT",
    "DOWNSTREAM_MONITORING"
]

FORBIDDEN_KEYWORDS = [
    "rm -rf", "drop table", "shutdown", "reboot", "kill -9", "terminate",
    "destroy", "delete from", "format", "truncate", "kubectl delete", "aws ec2 terminate"
]
