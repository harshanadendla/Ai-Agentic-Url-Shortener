from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, field
from typing import Any


def utcnow() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


@dataclass
class NodeRecord:
    node: str
    status: str
    started_at: str
    finished_at: str | None = None
    attempts: int = 0
    summary: str = ""
    error: str | None = None


@dataclass
class WorkflowState:
    run_id: str
    requirement: str
    scenario: str
    status: str = "created"
    current_node: str | None = None
    created_at: str = field(default_factory=utcnow)
    finished_at: str | None = None
    risk_level: str = "unknown"
    ambiguities: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    policy_findings: list[str] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    retries: dict[str, int] = field(default_factory=dict)
    node_records: list[NodeRecord] = field(default_factory=list)
    changed_inputs: list[str] = field(default_factory=list)
    checkpoint: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, payload: dict[str, Any]) -> "WorkflowState":
        payload = dict(payload)
        records = [NodeRecord(**r) for r in payload.pop("node_records", [])]
        state = cls(**payload)
        state.node_records = records
        return state
