from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PolicyDecision:
    risk_level: str
    human_approval_required: bool
    findings: list[str]
    blocked: bool = False


class PolicyEngine:
    """Security/compliance/change-control guardrails before autonomous work proceeds."""

    HIGH_RISK = {
        "production deploy": "production deployment requires explicit human release ownership",
        "drop table": "destructive schema operation detected",
        "delete database": "destructive data operation detected",
        "rotate secret": "credential/security operation detected",
        "disable auth": "security control weakening detected",
        "pii": "potential personal-data impact requires review",
    }
    MEDIUM_RISK = {
        "schema": "database/schema compatibility review required",
        "migration": "database migration review required",
        "rate limit": "traffic-control behavior change requires review",
        "authentication": "security boundary change requires review",
        "cache": "runtime consistency/caching behavior change requires review",
    }
    BLOCKED = {
        "exfiltrate": "data-exfiltration request is outside agent autonomy",
        "bypass approval": "attempt to bypass governance is prohibited",
    }

    def evaluate(self, requirement: str) -> PolicyDecision:
        text = requirement.lower()
        blocked = [reason for key, reason in self.BLOCKED.items() if key in text]
        if blocked:
            return PolicyDecision("critical", True, blocked, blocked=True)
        high = [reason for key, reason in self.HIGH_RISK.items() if key in text]
        if high:
            return PolicyDecision("high", True, high)
        medium = [reason for key, reason in self.MEDIUM_RISK.items() if key in text]
        if medium:
            return PolicyDecision("medium", True, medium)
        return PolicyDecision("low", False, ["no elevated policy trigger detected"])
