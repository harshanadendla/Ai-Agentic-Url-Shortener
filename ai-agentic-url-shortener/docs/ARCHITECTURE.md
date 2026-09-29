# Architecture overview

## Components

### 1. `shortener-service` — Java 21 / Spring Boot
The product service owns HTTP APIs, validation, redirect behavior, persistence, click analytics, cache interaction, rate limiting, health, and product metrics. PostgreSQL is authoritative. Redis is used as an optimization and traffic-control boundary and is deliberately allowed to fail open for availability.

### 2. `agent-orchestrator` — Python / FastAPI
The control plane owns requirement understanding, decomposition, codebase reasoning, orchestration, policy, approvals, retries, fallback, staging, testing coordination, documentation, release validation, replanning, audit, and workflow metrics. It receives the Java source tree read-only in Docker.

### 3. PostgreSQL
`short_links` is the URL-shortener system of record. Flyway owns schema versioning.

### 4. Redis
Caches resolved links and maintains fixed-window creation counters. Cache/rate-limit errors emit metrics and fail open so Redis does not become a redirect availability dependency.

### 5. Optional Ollama
Local open-source model inference. Model output assists requirement normalization only. It cannot override policy, mutate source, approve changes, or release code. If unavailable, the deterministic path records fallback and continues.

### 6. Prometheus + Grafana
Prometheus scrapes Java Actuator and Python workflow metrics. The Python side exports outcomes, retries, rollback/safe-stop events, node/end-to-end latency, approval decisions, and MTTR samples for recovered node failures.

## Orchestration model

The workflow is an explicit dependency graph rather than a simple linear chain:

```text
REQ -> PLAN -> ENTRY_POLICY_GATE
                    |
         +----------+----------+
         |          |          |
       ARCH        SEC       API/DATA
         |          |          |
         +----------+----------+
                    |
             DESIGN_SYNC_GATE
                    |
           HUMAN_APPROVAL_GATE (conditional)
                    |
                  IMPL
              +-----+-----+
              |           |
            TEST         DOCS
              |           |
              +-----+-----+
                    |
                VALIDATE
                    |
             EXIT_RELEASE_GATE
```

Parallel branches synchronize before implementation. Test and documentation also fan out after implementation and synchronize before release validation.

## Stateful context and lineage

`WorkflowState` carries the requirement, ambiguity, assumptions, task graph, artifacts, policy findings, decisions, approvals, retries, node attempts, changed upstream inputs, and checkpoint. State is also persisted to `artifacts/<run>/state.json`; `audit/events.jsonl` is append-only event evidence.

## Controlled autonomy

The implementation agent writes only into `SafeWorkspace`. Docker mounts the Java repository read-only into the Python container. The agent cannot merge, modify source, run a migration, or deploy. Medium/high-risk and ambiguous work stops at a human gate. Rejection triggers safe-stop/rollback evidence.

## Failure and recovery

Each agent node has bounded retry (`MAX_AGENT_RETRIES + 1`). The local model has deterministic fallback. Exhausted retries trigger safe-stop; because product source is never mutated, rollback is a controlled no-op on the source and the staged workspace remains available for audit. `ROLLBACK.json` records the boundary and reason.

## Dynamic replanning

`POST /agent/runs/{id}/replan` records the previous requirement, invalidates downstream work, preserves lineage, then re-executes requirement understanding, policy, dependency graph, design branches, gates, and approvals under the new input.
