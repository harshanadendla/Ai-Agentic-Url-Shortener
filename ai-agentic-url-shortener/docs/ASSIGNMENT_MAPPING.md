# Assessment requirement mapping

| Assessment expectation | Evidence in this repository |
|---|---|
| Requirement understanding | `requirement_agent` normalizes intent, records assumptions and measurable acceptance criteria, and detects ambiguity. Optional Ollama output is advisory and fallback is explicit. |
| Task decomposition | `planning_agent` produces an explicit dependency graph with IDs, dependencies, owners, sequencing, fan-out/fan-in, entry and exit gates. |
| Brownfield codebase reasoning | `JavaRepositoryInspector` performs read-only inspection of Spring Boot Java/XML/YAML/SQL files and `api_data_agent` records impacted modules, endpoints, data and compatibility constraints. |
| Non-linear/stateful orchestration | `WorkflowEngine` runs ARCH/SEC/API in parallel, synchronizes, gates implementation, then runs TEST/DOC in parallel before validation. `WorkflowState` persists cross-stage context. |
| Entry/exit gates | `entry_policy_gate`, `design_sync_gate`, conditional `human_approval_gate`, and `exit_release_gate` are first-class node records and audit events. |
| Sequential + parallel paths | Requirements/planning are sequential; design agents fan out in a thread pool; TEST/DOC fan out after implementation; both regions synchronize before downstream nodes. |
| Decision lineage | State records assumptions, decisions, policy findings, changed inputs, approvals, retries and node summaries; `audit/events.jsonl` is an append-only event log. |
| Human approval checkpoints | Medium/high-risk or ambiguous work enters `awaiting_approval`. Approval comment becomes cross-stage context. Rejection triggers safe-stop. |
| Bounded retries | Each agent node executes at most `MAX_AGENT_RETRIES + 1`; retries and attempts are observable. |
| Fallback | `LocalLLM` falls back to deterministic behavior when Ollama is disabled/unavailable, and the decision is recorded. Redis also has a DB availability fallback. |
| Rollback + safe-stop | Exhausted failure, blocked policy, or rejected approval produces `ROLLBACK.json`; source is unchanged because all agent code output is staged. |
| Security/compliance/change-control guardrails | `PolicyEngine`, read-only Java mount, path-jail workspace, URL/alias validation, traffic limits, human gates and no autonomous merge/migration/deploy. |
| Audit-grade observability | `state.json`, `audit/events.jsonl`, node timestamps/attempts, policy artifacts, approvals, final state and Prometheus metrics. |
| Success/retry/rollback/MTTR/latency metrics | `agent_workflow_runs_total`, `agent_workflow_retries_total`, `agent_workflow_rollbacks_total`, `agent_workflow_mttr_seconds`, `agent_workflow_node_duration_seconds`, `agent_workflow_duration_seconds`. Success rate is derived from completed/total run counters. |
| Dynamic replanning | `/agent/runs/{id}/replan` records old input, invalidates downstream artifacts and re-runs governance under the new requirement. |
| Engineering output generation | Real Spring Boot production code + Flyway schema + Java tests; the implementation agent additionally stages Java source, JUnit and OpenAPI artifacts per scenario. |
| Validation/risk control | Java/JUnit suite, generated Java `javac` validation when available, Docker live cross-language contract test, failure-injection tests, policy findings, release validation. |
| Controlled autonomy | Agents execute multi-step engineering work; source mutation/release is outside their authority; humans own approval and final merge/deploy. |
| Final engineering summary | Every successful run writes `06-docs/FINAL_ENGINEERING_SUMMARY.md` with plan/rationale, artifacts, risks/trade-offs, validation, assumptions, and limitations. |
| Working end-to-end prototype | `docker compose up --build` starts Java service, Python orchestrator, Postgres, Redis, Prometheus and Grafana. Python validation calls the live Java service. |
| Greenfield / brownfield / ambiguous scenarios | `agent-orchestrator/scenarios/*.json` and `scripts/demo.py`; each runs decomposition, orchestration and validation. |
| Setup/testing/limitations/trade-offs | `README.md`, `ARCHITECTURE.md`, `OPERATIONS.md`, `SCENARIOS.md`, `INTERVIEW_DEMO.md`. |
