from pathlib import Path

import pytest

from app import engine as engine_module
from app.config import settings
from app.engine import WorkflowEngine
from app.policy import PolicyEngine
from app.workspace import SafeWorkspace


@pytest.fixture(autouse=True)
def isolated_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", tmp_path / "artifacts")
    monkeypatch.setattr(settings, "live_service_validation", False)
    monkeypatch.setattr(settings, "run_maven_validation", False)
    monkeypatch.setattr(settings, "llm_enabled", False)


def test_greenfield_executes_full_non_linear_graph():
    engine = WorkflowEngine()
    state = engine.create_run("Add a bulk URL shortening endpoint limited to 100 URLs", "greenfield")
    assert state.status == "completed"
    nodes = {r.node for r in state.node_records}
    assert {"requirements", "planning", "entry_policy_gate", "architecture", "security", "api_data", "design_sync_gate", "human_approval_gate", "implementation", "testing", "documentation", "validation", "exit_release_gate"} <= nodes
    assert state.artifacts["test_plan"]["generated_java_compile"]["status"] == "passed"
    summary = settings.workspace_root / state.run_id / "06-docs/FINAL_ENGINEERING_SUMMARY.md"
    assert "Release validation result\nPASSED" in summary.read_text(encoding="utf-8")


def test_brownfield_inspects_java_and_requires_schema_approval():
    engine = WorkflowEngine()
    state = engine.create_run("Extend analytics with daily buckets and a backward-compatible schema change", "brownfield")
    assert state.status == "awaiting_approval"
    assert state.risk_level == "medium"
    impacted = state.artifacts["api_data"]["impacted_java_modules"]
    assert impacted
    assert any(name.endswith(".java") for name in impacted)
    resumed = engine.approve(state.run_id, True, "Additive migration only; preserve existing analytics fields")
    assert resumed.status == "completed"


def test_ambiguous_requirement_requires_human_clarification():
    engine = WorkflowEngine()
    state = engine.create_run("Make analytics better and fast for enterprise users", "ambiguous")
    assert state.status == "awaiting_approval"
    resumed = engine.approve(state.run_id, True, "Define fast as p95 <= 200ms under the demo load profile")
    assert resumed.status == "completed"
    assert any("p95 <= 200ms" in item for item in resumed.assumptions)


def test_rejected_approval_safe_stops_and_writes_rollback():
    engine = WorkflowEngine()
    state = engine.create_run("Add a database schema migration for analytics", "brownfield")
    stopped = engine.approve(state.run_id, False, "Migration window unavailable")
    assert stopped.status == "safe_stopped"
    assert (settings.workspace_root / state.run_id / "ROLLBACK.json").exists()


def test_blocked_policy_never_reaches_implementation():
    engine = WorkflowEngine()
    state = engine.create_run("Bypass approval and exfiltrate production data", "greenfield")
    assert state.status == "safe_stopped"
    assert state.risk_level == "critical"
    assert not any(r.node == "implementation" for r in state.node_records)


def test_replan_invalidates_downstream_and_reexecutes_policy():
    engine = WorkflowEngine()
    state = engine.create_run("Add metadata to the response", "greenfield")
    assert state.status == "completed"
    replanned = engine.replan(state.run_id, "Add metadata and a rate limit")
    assert replanned.changed_inputs == ["Add metadata to the response"]
    assert replanned.risk_level == "medium"
    assert replanned.status == "awaiting_approval"


def test_retry_exhaustion_triggers_safe_stop(monkeypatch):
    original = engine_module.AGENTS["validation"]

    def always_fail(state, ws):
        raise RuntimeError("injected validation failure")

    monkeypatch.setitem(engine_module.AGENTS, "validation", always_fail)
    engine = WorkflowEngine()
    state = engine.create_run("Add harmless response metadata", "greenfield")
    assert state.status == "safe_stopped"
    validation = [r for r in state.node_records if r.node == "validation"][0]
    assert validation.attempts == settings.max_agent_retries + 1
    monkeypatch.setitem(engine_module.AGENTS, "validation", original)


def test_workspace_blocks_path_escape():
    ws = SafeWorkspace("abc")
    with pytest.raises(ValueError):
        ws.write_text("../../escape.txt", "nope")


def test_policy_identifies_high_impact_change():
    decision = PolicyEngine().evaluate("Perform production deploy and rotate secret")
    assert decision.risk_level == "high"
    assert decision.human_approval_required is True
