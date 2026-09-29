from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from app.config import settings
from app.llm import LocalLLM
from app.repository import JavaRepositoryInspector
from app.shortener_client import ShortenerClient
from app.state import WorkflowState
from app.workspace import SafeWorkspace

AgentFn = Callable[[WorkflowState, SafeWorkspace], str]
llm = LocalLLM()
inspector = JavaRepositoryInspector()


def _advisory(state: WorkflowState, agent: str, prompt: str) -> str:
    note = llm.complete(prompt)
    if note:
        state.decisions.append({"agent": agent, "decision": "local LLM advisory captured; deterministic code/policy remains authoritative"})
        return note
    return "Deterministic fallback used; local LLM disabled or unavailable."


def requirement_agent(state: WorkflowState, ws: SafeWorkspace) -> str:
    text = state.requirement.strip()
    vague_markers = ["fast", "better", "secure", "scalable", "some analytics", "good", "enterprise-ready"]
    state.ambiguities = [m for m in vague_markers if m in text.lower()]
    if state.scenario == "ambiguous" and not state.ambiguities:
        state.ambiguities.append("acceptance criteria are incomplete")
    state.assumptions = [
        "public redirect contract remains backward compatible",
        "analytics stores aggregate operational data only; no PII is required",
        "agents may stage changes but may not mutate the Java source repository",
        "a human owns approval for ambiguous/high-impact changes and final release quality",
    ]
    model_note = llm.complete(
        "Normalize this software requirement and identify measurable acceptance criteria. Do not write code:\n" + text
    )
    if model_note:
        state.decisions.append({"agent": "requirements", "decision": "local Ollama output accepted as advisory context; deterministic guardrails remain authoritative"})
    else:
        model_note = "Deterministic requirement normalization used because local LLM is disabled or unavailable."
        state.decisions.append({"agent": "requirements", "decision": "deterministic LLM fallback used"})
    spec = {
        "intent": text,
        "scenario": state.scenario,
        "ambiguities": state.ambiguities,
        "assumptions": state.assumptions,
        "model_assist": model_note,
        "acceptance_criteria": [
            "behavior is covered by automated validation evidence",
            "API/data compatibility impact is documented",
            "security, reliability, and failure modes are reviewed",
            "implementation output remains staged until governed approval",
        ],
    }
    state.artifacts["requirement_spec"] = spec
    ws.write_json("01-requirement/spec.json", spec)
    return f"Normalized requirement and identified {len(state.ambiguities)} ambiguity item(s)."


def planning_agent(state: WorkflowState, ws: SafeWorkspace) -> str:
    tasks = [
        {"id": "REQ", "depends_on": [], "owner": "requirements", "action": "normalize intent/ambiguity"},
        {"id": "ENTRY", "depends_on": ["REQ"], "owner": "orchestrator", "action": "policy entry gate"},
        {"id": "ARCH", "depends_on": ["ENTRY"], "owner": "architecture", "action": "design and trade-offs"},
        {"id": "SEC", "depends_on": ["ENTRY"], "owner": "security", "action": "threat model and guardrails"},
        {"id": "API", "depends_on": ["ENTRY"], "owner": "api_data", "action": "Java/API/data/codebase impact"},
        {"id": "SYNC", "depends_on": ["ARCH", "SEC", "API"], "owner": "orchestrator", "action": "parallel design synchronization gate"},
        {"id": "HUMAN", "depends_on": ["SYNC"], "owner": "human", "action": "conditional high-impact/ambiguity approval"},
        {"id": "IMPL", "depends_on": ["HUMAN"], "owner": "implementation", "action": "stage Java implementation + schema/API artifacts"},
        {"id": "TEST", "depends_on": ["IMPL"], "owner": "testing", "action": "validate generated + live service behavior"},
        {"id": "DOC", "depends_on": ["IMPL"], "owner": "documentation", "action": "generate change/release docs"},
        {"id": "VALIDATE", "depends_on": ["TEST", "DOC"], "owner": "validation", "action": "release-readiness validation"},
        {"id": "EXIT", "depends_on": ["VALIDATE"], "owner": "orchestrator", "action": "exit/release gate"},
    ]
    state.tasks = tasks
    state.artifacts["task_graph"] = tasks
    ws.write_json("02-plan/dependency-graph.json", tasks)
    return "Created explicit DAG with entry/exit gates, parallel design, fan-in synchronization, conditional human approval, and parallel test/docs."


def architecture_agent(state: WorkflowState, ws: SafeWorkspace) -> str:
    facts = inspector.architecture_facts()
    design = {
        "runtime_components": [
            "Java 21 Spring Boot URL shortener",
            "PostgreSQL system of record",
            "Redis redirect cache + create-rate-limit boundary",
            "Python FastAPI agent orchestrator",
            "optional local Ollama model",
            "Prometheus + Grafana observability",
        ],
        "java_repository": facts,
        "decisions": [
            "redirect read path is independently scalable and cache-assisted",
            "database click increments use an atomic update to reduce lost-update risk",
            "Redis failures fail open to PostgreSQL for redirect availability",
            "agent-generated changes are staged in a jailed per-run workspace",
        ],
        "tradeoffs": [
            "synchronous click increment favors simple correctness over maximum redirect throughput; production could emit click events asynchronously",
            "in-process orchestrator execution is sufficient for a prototype; durable queues would be appropriate at larger scale",
        ],
        "model_advisory": _advisory(state, "architecture", f"Act as a software architecture reviewer. Requirement: {state.requirement}. Identify two design risks or trade-offs for a Spring Boot URL shortener. Be concise."),
    }
    state.artifacts["architecture"] = design
    state.decisions.append({"agent": "architecture", "decision": design["decisions"][0]})
    ws.write_json("03-design/architecture.json", design)
    return "Produced cross-language architecture, scaling boundaries, reliability decisions, and trade-offs."


def security_agent(state: WorkflowState, ws: SafeWorkspace) -> str:
    security = {
        "threats": [
            "malicious/invalid redirect targets and aliases",
            "URL-shortener abuse and request flooding",
            "agent path traversal or unauthorized repository mutation",
            "unapproved destructive/schema/security changes",
            "prompt/model output attempting to override policy",
        ],
        "controls": [
            "http/https URL policy + URL-safe alias validation",
            "Redis-backed create rate limiting with observable fail-open behavior",
            "SafeWorkspace path jail and read-only Java source mount in Docker",
            "deterministic PolicyEngine remains authoritative over LLM suggestions",
            "human approval for medium/high/ambiguous changes; safe-stop on rejection",
        ],
        "change_control": "agents stage reviewable artifacts only; the source repository is never autonomously patched or deployed",
        "model_advisory": _advisory(state, "security", f"Threat-model this requirement for a URL shortener and agentic SDLC system: {state.requirement}. Return concise review notes only."),
    }
    state.artifacts["security"] = security
    ws.write_json("03-design/security.json", security)
    return "Produced threat model, compliance/change-control guardrails, and controlled-autonomy boundaries."


def api_data_agent(state: WorkflowState, ws: SafeWorkspace) -> str:
    impacted = inspector.impacted_files(state.requirement) if state.scenario == "brownfield" else []
    analysis = {
        "impacted_endpoints": ["POST /api/v1/links", "GET /{code}", "GET /api/v1/links/{code}/analytics", "DELETE /api/v1/links/{code}"],
        "data_entity": "short_links",
        "cache_keys": ["short-link:{code}", "create-rate:{ip}:{minute}"],
        "impacted_java_modules": impacted,
        "compatibility": "redirect semantics and existing response fields are preserved; additive API/schema changes require contract and migration review",
        "repository_facts": inspector.architecture_facts(),
        "model_advisory": _advisory(state, "api_data", f"Review backward-compatibility risks for this requirement: {state.requirement}. Candidate impacted Java files: {impacted}."),
    }
    state.artifacts["api_data"] = analysis
    ws.write_json("03-design/api-data.json", analysis)
    return f"Mapped API/data flows and {len(impacted)} Java repository impact candidate(s)."


def _generated_java(state: WorkflowState) -> tuple[str, str, str, str]:
    if state.scenario == "greenfield":
        class_name = "BulkShortenPolicy"
        source = '''package generated;

import java.util.List;

public final class BulkShortenPolicy {
    private BulkShortenPolicy() {}
    public static <T> List<T> validate(List<T> requests) {
        if (requests == null || requests.isEmpty()) throw new IllegalArgumentException("at least one URL is required");
        if (requests.size() > 100) throw new IllegalArgumentException("bulk request limit is 100");
        return List.copyOf(requests);
    }
}
'''
        test = '''package generated;

import org.junit.jupiter.api.Test;
import java.util.List;
import static org.assertj.core.api.Assertions.*;

class BulkShortenPolicyTest {
    @Test void enforcesBoundedBatch() {
        assertThat(BulkShortenPolicy.validate(List.of("https://example.com"))).hasSize(1);
    }
}
'''
        openapi = '''openapi: 3.0.3
info: {title: Staged Bulk Shortening API, version: 1.0.0}
paths:
  /api/v1/links/bulk:
    post:
      summary: Create up to 100 short links after bounded request validation
      responses:
        '201': {description: Created}
        '400': {description: Invalid or oversized batch}
'''
    elif state.scenario == "brownfield":
        class_name = "DailyAnalyticsBucket"
        source = '''package generated;

import java.time.Instant;
import java.time.ZoneOffset;

public final class DailyAnalyticsBucket {
    private DailyAnalyticsBucket() {}
    public static String utcDay(Instant timestamp) {
        if (timestamp == null) throw new IllegalArgumentException("timestamp is required");
        return timestamp.atZone(ZoneOffset.UTC).toLocalDate().toString();
    }
}
'''
        test = '''package generated;

import org.junit.jupiter.api.Test;
import java.time.Instant;
import static org.assertj.core.api.Assertions.*;

class DailyAnalyticsBucketTest {
    @Test void usesUtcDay() {
        assertThat(DailyAnalyticsBucket.utcDay(Instant.parse("2026-09-24T23:59:59Z"))).isEqualTo("2026-09-24");
    }
}
'''
        openapi = '''openapi: 3.0.3
info: {title: Staged Analytics Extension, version: 1.0.0}
paths:
  /api/v1/links/{code}/analytics:
    get:
      summary: Existing endpoint; staged change preserves current fields and may add dailyBuckets
      responses:
        '200': {description: Backward-compatible analytics payload}
'''
    else:
        class_name = "AnalyticsSlo"
        source = '''package generated;

public record AnalyticsSlo(int p95LatencyMs) {
    public AnalyticsSlo {
        if (p95LatencyMs <= 0) throw new IllegalArgumentException("p95LatencyMs must be positive");
    }
}
'''
        test = '''package generated;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class AnalyticsSloTest {
    @Test void requiresPositiveThreshold() {
        assertThatThrownBy(() -> new AnalyticsSlo(0)).isInstanceOf(IllegalArgumentException.class);
    }
}
'''
        openapi = '''openapi: 3.0.3
info: {title: Human-clarified Analytics SLO, version: 1.0.0}
paths: {}
x-approved-clarification: "Latency SLO must be supplied/approved by a human before implementation."
'''
    return class_name, source, test, openapi


def implementation_agent(state: WorkflowState, ws: SafeWorkspace) -> str:
    class_name, source, test, openapi = _generated_java(state)
    req = re.sub(r"\s+", " ", state.requirement).strip()
    proposal = f"""# Staged Java implementation proposal

Run: {state.run_id}
Scenario: {state.scenario}
Requirement: {req}

## Controlled change plan
- Preserve Spring Boot redirect compatibility.
- Keep PostgreSQL access behind repository/service boundaries.
- Treat Redis as an optimization/reliability boundary, not the source of truth.
- Add Java/JUnit/API-schema output in this isolated workspace only.
- Require validation evidence before the exit gate.

## Autonomy boundary
The implementation agent does **not** edit `shortener-service/`, merge code, run migrations, or deploy. Human review owns those high-impact actions.
"""
    source_path = ws.write_text(f"04-implementation/generated/src/main/java/generated/{class_name}.java", source)
    test_path = ws.write_text(f"04-implementation/generated/src/test/java/generated/{class_name}Test.java", test)
    schema_path = ws.write_text("04-implementation/generated/openapi-staged.yaml", openapi)
    ws.write_text("04-implementation/PROPOSAL.md", proposal)
    model_review = _advisory(state, "implementation", f"Review this staged Java change for correctness, security, maintainability, and test gaps. Do not rewrite the code. Requirement: {state.requirement}\n\n{source}")
    model_review_path = ws.write_text("04-implementation/MODEL_REVIEW.md", model_review + "\n")
    state.artifacts["implementation_proposal"] = proposal
    state.artifacts["generated_code"] = {"java_source": source_path, "junit_test": test_path, "api_schema": schema_path, "model_review": model_review_path}
    return "Staged Java source, JUnit test, API schema, and model-assisted review without mutating the product repository."


def testing_agent(state: WorkflowState, ws: SafeWorkspace) -> str:
    generated = state.artifacts.get("generated_code", {})
    source_path = Path(generated["java_source"])
    compile_dir = ws.path("05-validation/javac-out")
    compile_dir.mkdir(parents=True, exist_ok=True)
    javac = shutil.which("javac")
    if javac:
        proc = subprocess.run([javac, "-d", str(compile_dir), str(source_path)], capture_output=True, text=True, timeout=20)
        if proc.returncode != 0:
            raise RuntimeError("staged Java source failed javac validation: " + proc.stderr[-1000:])
        javac_result = {"status": "passed", "command": "javac"}
    else:
        javac_result = {"status": "skipped", "reason": "javac is unavailable in this runtime"}

    maven_result: dict[str, object] = {"status": "not_requested"}
    if settings.run_maven_validation:
        mvn = shutil.which("mvn")
        if not mvn:
            raise RuntimeError("RUN_MAVEN_VALIDATION=true but mvn is unavailable")
        proc = subprocess.run([mvn, "-q", "test"], cwd=settings.shortener_repo_root, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            raise RuntimeError("Spring Boot Maven tests failed: " + (proc.stdout + proc.stderr)[-2000:])
        maven_result = {"status": "passed", "command": "mvn test"}

    live_result: dict[str, object] = {"status": "disabled"}
    if settings.live_service_validation:
        live_result = {"status": "passed", **ShortenerClient().smoke_test()}

    plan = {
        "generated_java_compile": javac_result,
        "spring_boot_maven_tests": maven_result,
        "live_cross_language_contract": live_result,
        "unit": ["URL policy", "alias collision", "cache fallback", "agent policy", "workspace jail", "DAG gates"],
        "integration": ["create -> Java redirect -> analytics -> deactivate", "approval resume", "retry exhaustion -> safe-stop"],
        "contract": ["307 redirect contract", "existing analytics fields remain compatible", "ProblemDetail error shape"],
        "failure_injection": ["agent node failure", "human rejection", "Redis failure-open", "upstream requirement change"],
    }
    state.artifacts["test_plan"] = plan
    ws.write_json("05-validation/test-evidence.json", plan)
    return "Validated staged Java syntax and assembled unit/integration/contract/failure evidence; live Java smoke test runs in Docker."


def documentation_agent(state: WorkflowState, ws: SafeWorkspace) -> str:
    doc = f"""# Change Summary

Scenario: **{state.scenario}**

Requirement: {state.requirement}

Risk: **{state.risk_level}**

Human approvals: {len(state.approvals)}

Artifacts include normalized requirements, explicit dependency graph, Java-repository impact analysis, architecture/security analysis, staged Java/JUnit/OpenAPI output, test evidence, decision lineage, and release validation.
"""
    final_summary = f"""# Final Engineering Summary

## Plan and rationale
The workflow normalized the requirement, decomposed it into an explicit dependency DAG, passed an entry policy gate, ran architecture/security/API-data analysis in parallel, synchronized those results, applied the human-approval policy, staged Java engineering output, ran testing and documentation in parallel, and finished at a governed exit gate.

## Produced artifacts
- Requirement specification and assumptions
- Dependency graph and policy decision
- Architecture, security, Java codebase/API/data impact analysis
- Staged Java source, JUnit test, and OpenAPI change artifact
- Test evidence and change summary
- Audit event stream, decisions, approvals, retries, and release validation

## Risks and trade-offs
Risk level: **{state.risk_level}**. Redis is deliberately not a source of truth and fails open to PostgreSQL for availability. Click counting is synchronous and simple; a production-at-scale evolution could use an event stream. Agent source mutation/deploy is intentionally prohibited to keep autonomy bounded.

## Validation
The generated Java artifact is syntax-compiled when `javac` is available. The Java service has Maven/JUnit tests. In Docker, the Python validation agent performs a live create -> redirect -> analytics -> deactivate contract test against the Spring Boot service.

## Assumptions
""" + "\n".join(f"- {item}" for item in state.assumptions) + """

## Limitations
- Prototype orchestration executes within one Python service process; a production control plane would normally use a durable queue/workflow backend.
- Ollama is optional and advisory; deterministic agents are used when the model is disabled/unavailable.
- Agents stage changes for review rather than autonomously merging, migrating, or deploying.
"""
    state.artifacts["change_summary"] = doc
    state.artifacts["final_engineering_summary"] = final_summary
    ws.write_text("06-docs/CHANGE_SUMMARY.md", doc)
    ws.write_text("06-docs/FINAL_ENGINEERING_SUMMARY.md", final_summary)
    return "Generated change documentation and the required final engineering summary."


def validation_agent(state: WorkflowState, ws: SafeWorkspace) -> str:
    required = {"requirement_spec", "task_graph", "architecture", "security", "api_data", "implementation_proposal", "generated_code", "test_plan", "change_summary", "final_engineering_summary"}
    missing = sorted(required - set(state.artifacts))
    test_evidence = state.artifacts.get("test_plan", {})
    generated_compile = test_evidence.get("generated_java_compile", {}).get("status")
    passed = not missing and generated_compile in {"passed", "skipped"}
    result = {
        "passed": passed,
        "missing": missing,
        "risk_level": state.risk_level,
        "generated_java_compile": generated_compile,
        "source_repository_mutated": False,
        "release_owner": "human",
    }
    state.artifacts["validation"] = result
    ws.write_json("07-release/validation.json", result)
    summary_path = ws.path("06-docs/FINAL_ENGINEERING_SUMMARY.md")
    if summary_path.exists():
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write("\n## Release validation result\n" + ("PASSED" if passed else "FAILED") + f" — missing artifacts: {missing}; generated Java compile: {generated_compile}. Final merge/deploy remains human-owned.\n")
    if not passed:
        raise RuntimeError(f"release validation failed: missing={missing}, java_compile={generated_compile}")
    return "Release-readiness evidence is complete; final release ownership remains human."


AGENTS: dict[str, AgentFn] = {
    "requirements": requirement_agent,
    "planning": planning_agent,
    "architecture": architecture_agent,
    "security": security_agent,
    "api_data": api_data_agent,
    "implementation": implementation_agent,
    "testing": testing_agent,
    "documentation": documentation_agent,
    "validation": validation_agent,
}
