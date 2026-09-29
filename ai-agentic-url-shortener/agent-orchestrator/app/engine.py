from __future__ import annotations

import datetime as dt
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict

from prometheus_client import Counter, Histogram

from app.agents import AGENTS
from app.config import settings
from app.policy import PolicyEngine
from app.state import NodeRecord, WorkflowState, utcnow
from app.store import RunStore
from app.workspace import SafeWorkspace

WORKFLOW_RUNS = Counter("agent_workflow_runs_total", "Terminal workflow outcomes", ["scenario", "status"])
WORKFLOW_RETRIES = Counter("agent_workflow_retries_total", "Agent node retries", ["node"])
WORKFLOW_ROLLBACKS = Counter("agent_workflow_rollbacks_total", "Rollback/safe-stop events")
WORKFLOW_LATENCY = Histogram("agent_workflow_duration_seconds", "End-to-end workflow duration", ["scenario", "status"])
NODE_LATENCY = Histogram("agent_workflow_node_duration_seconds", "Per-node execution duration", ["node", "status"])
WORKFLOW_RECOVERY = Histogram("agent_workflow_mttr_seconds", "Mean-time-to-recovery sample: time from first node failure to recovered success", ["node"])
APPROVAL_EVENTS = Counter("agent_workflow_approvals_total", "Human approval decisions", ["decision"])


class WorkflowEngine:
    """Stateful explicit DAG executor with governance, retries, fan-out/fan-in, and durable audit state."""

    def __init__(self):
        self.runs: dict[str, WorkflowState] = {}
        self._locks: dict[str, threading.RLock] = {}
        self.policy = PolicyEngine()
        self.store = RunStore()
        self._run_started_monotonic: dict[str, float] = {}

    def create_run(self, requirement: str, scenario: str, auto_approve: bool = False) -> WorkflowState:
        if scenario not in {"greenfield", "brownfield", "ambiguous"}:
            raise ValueError("scenario must be greenfield, brownfield, or ambiguous")
        run_id = uuid.uuid4().hex[:12]
        state = WorkflowState(run_id=run_id, requirement=requirement.strip(), scenario=scenario)
        state.artifacts["auto_approve"] = auto_approve
        self.runs[run_id] = state
        self._locks[run_id] = threading.RLock()
        self._run_started_monotonic[run_id] = time.monotonic()
        self._save(state)
        self._execute_until_human_gate(state)
        return state

    def get(self, run_id: str) -> WorkflowState | None:
        state = self.runs.get(run_id)
        if state is not None:
            return state
        state = self.store.load(run_id)
        if state is not None:
            self.runs[run_id] = state
            self._locks[run_id] = threading.RLock()
        return state

    def approve(self, run_id: str, approved: bool, comment: str = "") -> WorkflowState:
        state = self.get(run_id)
        if state is None:
            raise KeyError(run_id)
        if state.status != "awaiting_approval":
            raise ValueError(f"run is not awaiting approval (status={state.status})")
        APPROVAL_EVENTS.labels("approved" if approved else "rejected").inc()
        event = {"approved": approved, "comment": comment, "at": utcnow()}
        state.approvals.append(event)
        if comment.strip():
            state.assumptions.append("Human clarification: " + comment.strip())
            state.decisions.append({"agent": "human", "decision": comment.strip()})
        self._audit_event(state, "human_approval", event)
        if not approved:
            self._record_gate(state, "human_approval_gate", "rejected", "Human rejected the proposed high-impact/ambiguous work.")
            self._safe_stop(state, "human approval rejected")
            return state

        self._record_gate(state, "human_approval_gate", "succeeded", "Human approval received; controlled execution may continue.")
        state.status = "running"
        self._save(state)
        self._execute_post_approval(state)
        return state

    def replan(self, run_id: str, new_requirement: str) -> WorkflowState:
        state = self.get(run_id)
        if state is None:
            raise KeyError(run_id)
        previous = state.requirement
        state.changed_inputs.append(previous)
        state.requirement = new_requirement.strip()
        state.decisions.append({"agent": "orchestrator", "decision": "upstream requirement changed; downstream artifacts invalidated and dependency graph will be re-executed"})
        keep = {"auto_approve": state.artifacts.get("auto_approve", False)}
        state.artifacts = keep
        state.ambiguities.clear()
        state.assumptions.clear()
        state.tasks.clear()
        state.policy_findings.clear()
        state.approvals.clear()
        state.retries.clear()
        state.node_records.clear()
        state.finished_at = None
        state.current_node = None
        state.status = "created"
        state.checkpoint = None
        self._run_started_monotonic[run_id] = time.monotonic()
        self._audit_event(state, "replan", {"old_requirement": previous, "new_requirement": state.requirement})
        self._save(state)
        self._execute_until_human_gate(state)
        return state

    def _run_node(self, state: WorkflowState, node: str, ws: SafeWorkspace) -> None:
        lock = self._locks[state.run_id]
        record = NodeRecord(node=node, status="running", started_at=utcnow())
        with lock:
            state.node_records.append(record)
            state.current_node = node
            self._audit_event(state, "node_started", {"node": node})
            self._save(state)

        max_attempts = settings.max_agent_retries + 1
        first_failure_at: float | None = None
        started = time.monotonic()
        for attempt in range(1, max_attempts + 1):
            with lock:
                record.attempts = attempt
                state.retries[node] = attempt - 1
            if attempt > 1:
                WORKFLOW_RETRIES.labels(node).inc()
            try:
                summary = AGENTS[node](state, ws)
                if first_failure_at is not None:
                    WORKFLOW_RECOVERY.labels(node).observe(time.monotonic() - first_failure_at)
                with lock:
                    record.summary = summary
                    record.status = "succeeded"
                    record.error = None
                    record.finished_at = utcnow()
                    self._audit_event(state, "node_succeeded", {"node": node, "attempts": attempt, "summary": summary})
                    self._save(state)
                NODE_LATENCY.labels(node, "succeeded").observe(time.monotonic() - started)
                return
            except Exception as exc:
                if first_failure_at is None:
                    first_failure_at = time.monotonic()
                with lock:
                    record.error = str(exc)
                    self._audit_event(state, "node_attempt_failed", {"node": node, "attempt": attempt, "error": str(exc)})
                    self._save(state)
                if attempt >= max_attempts:
                    with lock:
                        record.status = "failed"
                        record.finished_at = utcnow()
                    NODE_LATENCY.labels(node, "failed").observe(time.monotonic() - started)
                    raise

    def _execute_until_human_gate(self, state: WorkflowState) -> None:
        ws = SafeWorkspace(state.run_id)
        state.status = "running"
        state.checkpoint = state.snapshot()
        self._save(state)
        try:
            self._run_node(state, "requirements", ws)
            self._run_node(state, "planning", ws)

            decision = self.policy.evaluate(state.requirement)
            state.risk_level = decision.risk_level
            state.policy_findings = list(decision.findings)
            ws.write_json("02-plan/policy-decision.json", asdict(decision))
            if decision.blocked:
                self._record_gate(state, "entry_policy_gate", "blocked", "; ".join(decision.findings))
                self._safe_stop(state, "entry policy blocked the request")
                return
            self._record_gate(state, "entry_policy_gate", "succeeded", f"risk={decision.risk_level}")

            self._parallel_design(state, ws)
            self._record_gate(state, "design_sync_gate", "succeeded", "Architecture, security, and API/data branches joined successfully.")

            needs_human = decision.human_approval_required or state.scenario == "ambiguous" or bool(state.ambiguities and state.scenario == "ambiguous")
            auto = bool(state.artifacts.get("auto_approve")) or (
                settings.auto_approve_low_risk and state.risk_level == "low" and state.scenario != "ambiguous"
            )
            if needs_human and not auto:
                state.status = "awaiting_approval"
                state.current_node = "human_approval_gate"
                self._record_gate(state, "human_approval_gate", "waiting", "Human clarification/approval required before implementation.")
                self._save(state)
                return

            state.approvals.append({"approved": True, "comment": "auto-approved by low-risk policy", "at": utcnow(), "actor": "policy"})
            self._record_gate(state, "human_approval_gate", "succeeded", "Low-risk policy auto-approval applied.")
            self._execute_post_approval(state)
        except Exception as exc:
            self._safe_stop(state, f"pre-approval execution failed: {exc}")

    def _parallel_design(self, state: WorkflowState, ws: SafeWorkspace) -> None:
        nodes = ["architecture", "security", "api_data"]
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="design-agent") as pool:
            futures = {pool.submit(self._run_node, state, node, ws): node for node in nodes}
            for future in as_completed(futures):
                future.result()

    def _execute_post_approval(self, state: WorkflowState) -> None:
        ws = SafeWorkspace(state.run_id)
        try:
            self._run_node(state, "implementation", ws)
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="post-impl-agent") as pool:
                futures = {pool.submit(self._run_node, state, node, ws): node for node in ("testing", "documentation")}
                for future in as_completed(futures):
                    future.result()
            self._run_node(state, "validation", ws)
            self._record_gate(state, "exit_release_gate", "succeeded", "Validation evidence complete. Human owns final merge/deploy decision.")
            state.status = "completed"
            state.current_node = None
            state.finished_at = utcnow()
            ws.write_json("07-release/final-state.json", state.snapshot())
            self._audit_event(state, "workflow_completed", {"status": state.status})
            self._save(state)
            self._record_terminal_metrics(state)
        except Exception as exc:
            self._safe_stop(state, f"post-approval execution failed: {exc}")

    def _record_gate(self, state: WorkflowState, node: str, status: str, summary: str) -> None:
        now = utcnow()
        record = NodeRecord(node=node, status=status, started_at=now, finished_at=now, attempts=1, summary=summary)
        state.node_records.append(record)
        state.current_node = node
        self._audit_event(state, "gate", {"node": node, "status": status, "summary": summary})
        self._save(state)

    def _safe_stop(self, state: WorkflowState, reason: str) -> None:
        if state.status == "safe_stopped" and state.finished_at:
            return
        WORKFLOW_ROLLBACKS.inc()
        state.status = "safe_stopped"
        state.finished_at = utcnow()
        state.current_node = None
        state.decisions.append({
            "agent": "orchestrator",
            "decision": "safe-stop/rollback boundary activated; product source was never mutated; staged workspace retained as audit evidence",
            "reason": reason,
        })
        ws = SafeWorkspace(state.run_id)
        ws.write_json("ROLLBACK.json", {
            "reason": reason,
            "strategy": "workspace isolation means rollback is non-destructive: no product source/migration/deploy occurred",
            "source_mutated": False,
            "checkpoint_available": state.checkpoint is not None,
            "staged_artifacts_retained_for_audit": True,
        })
        self._audit_event(state, "safe_stop", {"reason": reason, "source_mutated": False})
        self._save(state)
        self._record_terminal_metrics(state)

    def _audit_event(self, state: WorkflowState, event_type: str, payload: dict[str, object]) -> None:
        event = {"at": utcnow(), "run_id": state.run_id, "type": event_type, "status": state.status, "payload": payload}
        SafeWorkspace(state.run_id).append_jsonl("audit/events.jsonl", event)

    def _save(self, state: WorkflowState) -> None:
        self.store.save(state)

    def _record_terminal_metrics(self, state: WorkflowState) -> None:
        started = self._run_started_monotonic.pop(state.run_id, None)
        WORKFLOW_RUNS.labels(state.scenario, state.status).inc()
        if started is not None:
            WORKFLOW_LATENCY.labels(state.scenario, state.status).observe(max(0.0, time.monotonic() - started))


engine = WorkflowEngine()
