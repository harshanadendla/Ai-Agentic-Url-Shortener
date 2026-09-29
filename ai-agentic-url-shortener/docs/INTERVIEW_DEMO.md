# 8-minute interview demo

## 0:00–1:00 — Explain the split
Open the repository tree. Point out that the URL shortener is a real Java/Spring Boot product and Python is only the agentic engineering control plane. This demonstrates both backend engineering and agentic-system design without making the product dependent on Python AI code.

## 1:00–2:00 — Show the Java service
Open `ShortenerService.java`, `LinkCache.java`, the Flyway migration and tests. Explain PostgreSQL authority, Redis cache/rate-limit boundary, atomic click increment, expiry/deactivation, validation, Actuator metrics, and bounded random-code collision handling.

## 2:00–3:00 — Show the orchestration DAG
Open `planning_agent` and `WorkflowEngine`. Trace REQ -> ENTRY -> parallel ARCH/SEC/API -> sync -> conditional human gate -> IMPL -> parallel TEST/DOC -> VALIDATE -> EXIT. Emphasize that this is non-linear stateful orchestration, not a prompt chain.

## 3:00–4:30 — Run the ambiguous case
Create `Make analytics better and fast...`. Show `awaiting_approval`, the ambiguity list, policy artifact and audit events. Approve with `p95 <= 200ms; preserve existing fields`. Show that the clarification becomes part of the state/lineage.

## 4:30–5:30 — Show controlled implementation
Open the generated workspace. The implementation agent staged Java, JUnit and OpenAPI artifacts but could not mutate the read-only source tree. Explain why merge/migration/deploy remain human-owned.

## 5:30–6:30 — Brownfield reasoning
Run the brownfield scenario and open `03-design/api-data.json`. Show that the agent inspected the actual Java codebase and identified impacted modules/endpoints/data. Explain compatibility constraints and why schema change forces approval.

## 6:30–7:15 — Reliability and governance
Show bounded retries, deterministic LLM fallback, `ROLLBACK.json`, safe-stop, policy blocking, replan, persisted state and append-only audit events.

## 7:15–8:00 — Observability and final ownership
Open Prometheus/Grafana or `/metrics`. Call out workflow outcome/success rate, retries, rollback frequency, MTTR, node latency and end-to-end latency. Finish with `FINAL_ENGINEERING_SUMMARY.md` and explain that agents execute within defined boundaries while the human owns release quality.
