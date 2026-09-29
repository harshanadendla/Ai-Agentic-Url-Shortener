# Operations and reliability

## Health
- Java: `/actuator/health`
- Python: `/health`
- PostgreSQL/Redis use Docker health checks.

## Metrics
Java exposes `/actuator/prometheus`. Python exposes `/metrics`.

Useful PromQL examples:

```promql
sum(rate(agent_workflow_runs_total{status="completed"}[5m]))
/
sum(rate(agent_workflow_runs_total[5m]))
```

```promql
sum(rate(agent_workflow_retries_total[5m]))
```

```promql
histogram_quantile(0.95, sum by (le) (rate(agent_workflow_duration_seconds_bucket[5m])))
```

```promql
histogram_quantile(0.95, sum by (le,node) (rate(agent_workflow_mttr_seconds_bucket[5m])))
```

## Failure modes
- **Redis unavailable:** cache and create-rate-limit operations fail open and emit metrics; PostgreSQL remains authoritative.
- **PostgreSQL unavailable:** create/redirect cannot guarantee authoritative state and fail rather than inventing data.
- **Ollama unavailable:** deterministic requirement processing is used and explicitly recorded.
- **Agent node failure:** bounded retries; exhausted retries trigger safe-stop and rollback evidence.
- **Human rejection:** immediate safe-stop; implementation does not proceed.
- **Orchestrator restart:** run state is persisted in each run workspace and can be read again by ID.
- **Changed upstream requirement:** replan invalidates downstream artifacts and re-runs gates/policy.

## Change control
Agents never patch the Java source tree, merge code, run Flyway against production, or deploy. Their implementation output is reviewable staged evidence. A human owns those irreversible/high-impact operations.
