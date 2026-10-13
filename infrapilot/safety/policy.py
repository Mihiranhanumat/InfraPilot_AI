"""
Safety policy and execution guardrails for InfraPilot AI.
Strictly ensures:
1. No destructive commands or live mutations can be initiated.
2. Log content is treated as untrusted text data (cannot trigger instructions).
3. All remediation suggestions are validated against allowlists and flagged RECOMMENDATION_ONLY.
"""
from typing import List, Tuple, Dict, Any
import re
from config.settings import FORBIDDEN_KEYWORDS, ALLOWLIST_RECOVERY_CATEGORIES, SAFETY_DISCLAIMER
from infrapilot.schemas import RecoveryRecommendation

DANGEROUS_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"system prompt",
    r"you are now in maintenance mode",
    r"execute (command|script|shell)",
    r"drop table",
    r"rm -rf",
    r"truncate table",
    r"delete from",
    r"grant all privileges",
]

def is_safe_action(action_text: str) -> Tuple[bool, str]:
    """
    Check if an action is strictly non-destructive and read-only/advisory.
    Returns: (is_safe, reason)
    """
    lowered = action_text.lower()
    for kw in FORBIDDEN_KEYWORDS:
        if kw in lowered:
            return False, f"Action contains forbidden destructive keyword: '{kw}'"

    for pattern in DANGEROUS_INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return False, f"Action matches dangerous command pattern: '{pattern}'"

    # Must not contain active execution verbs targeting cloud or OS
    if re.search(r"\b(execute|run|exec|bash|sh|powershell|cmd\.exe)\b", lowered):
        return False, "Direct shell execution is strictly prohibited by safety policy."

    return True, "Action passed read-only safety policy checks."

def sanitize_log_content(raw_log: str) -> str:
    """
    Sanitize log text to prevent prompt injection or execution of commands found in logs.
    Logs are untrusted telemetry evidence, never executable instructions.
    """
    if not isinstance(raw_log, str):
        return ""
    
    cleaned = raw_log.strip()
    # Mask injection patterns if found in log text
    for pattern in DANGEROUS_INJECTION_PATTERNS:
        cleaned = re.sub(pattern, "[UNTRUSTED_CONTENT_FILTERED]", cleaned, flags=re.IGNORECASE)
    
    return cleaned

def enforce_safety_on_recommendation(rec: RecoveryRecommendation) -> RecoveryRecommendation:
    """
    Validate and enforce safety properties on a recovery recommendation.
    """
    is_safe, reason = is_safe_action(rec.action)
    if not is_safe:
        rec.action = f"[BLOCKED BY SAFETY POLICY] {rec.action}"
        rec.rationale = f"Original suggestion blocked: {reason}"
        rec.risk_level = "HIGH"

    # Category check
    if rec.category not in ALLOWLIST_RECOVERY_CATEGORIES:
        rec.category = "CONFIGURATION_AUDIT"

    # Enforce non-executing metadata
    rec.status = "RECOMMENDATION_ONLY"
    rec.requires_human_approval = True
    return rec

def validate_all_recommendations(recs: List[RecoveryRecommendation]) -> List[RecoveryRecommendation]:
    """Enforce policy across all generated recommendations."""
    return [enforce_safety_on_recommendation(r) for r in recs]
