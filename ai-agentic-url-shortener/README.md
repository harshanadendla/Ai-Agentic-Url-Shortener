# Agentic URL Shortener — Java Product + Python AI Orchestrator

This repository is a production-oriented prototype for the **Agentic-Proficient Software Engineer** assessment. It intentionally separates the application and AI concerns:

- **Java 21 / Spring Boot** implements the actual URL-shortener product.
- **Python / FastAPI** implements the agentic SDLC control plane.
- **PostgreSQL** is the system of record.
- **Redis** accelerates redirects and backs create-rate limiting.
- **Ollama** is an optional local/open-source LLM boundary; workflows have deterministic fallbacks.
- **Prometheus + Grafana** expose application and workflow reliability signals.

The URL shortener is not the point of the assessment by itself. The differentiator is the controlled-autonomy orchestration that transforms a requirement into reviewable engineering artifacts while keeping humans in control of high-impact actions.

## Architecture

```text
                           Requirement
                                |
                       Python Orchestrator
                                |
          +---------------------+---------------------+
          |                     |                     |
   Requirement Agent      Planning Agent       Entry Policy Gate
                                                     |
                          +--------------------------+--------------------------+
                          |                          |                          |
                    Architecture Agent         Security Agent            API/Data Agent
                          |                          |                          |
                          +--------------------------+--------------------------+
                                                     |
                                             Design Sync Gate
                                                     |
                                      Conditional Human Approval
                                                     |
                                          Implementation Agent
                                  (stages Java/JUnit/OpenAPI only)
                                                     |
                                      +--------------+--------------+
                                      |                             |
                                  Test Agent                   Docs Agent
                                      |                             |
                                      +--------------+--------------+
                                                     |
                                            Validation Agent
                                                     |
                                             Exit/Release Gate
                                                     |
                                            Human merge/deploy

       read-only repo inspection                    live contract validation
 Python --------------------------------> Java repo <------------------------- Python
                                                  |
                                      Spring Boot URL Shortener
                                      /          |          \
                                  PostgreSQL    Redis     Actuator
```

## Product service — Java/Spring Boot

The Spring service supports:

- `POST /api/v1/links` — create a short link, optional custom alias and expiry
- `GET /{code}` — HTTP 307 redirect
- `GET /api/v1/links/{code}/analytics` — click count and lifecycle metadata
- `DELETE /api/v1/links/{code}` — deactivate a link
- `/docs` — Swagger UI
- `/actuator/health` and `/actuator/prometheus` — health and metrics

Reliability/security choices include collision-bounded code generation, database uniqueness, atomic analytics increments, Redis cache fail-open to PostgreSQL, rate limiting, URL/alias validation, graceful shutdown, health probes, and Flyway migrations.

## Agentic control plane — Python

The Python service provides:

- `POST /agent/runs` — start `greenfield`, `brownfield`, or `ambiguous` workflow
- `GET /agent/runs/{id}` — inspect state, lineage, artifacts, retries, approvals
- `POST /agent/runs/{id}/approve` — human approve/reject with clarification
- `POST /agent/runs/{id}/replan` — replace an upstream requirement and dynamically rebuild downstream work
- `/metrics` — workflow reliability metrics

Each run writes an isolated artifact tree under `agent-orchestrator/artifacts/<run-id>/` containing requirements, dependency graph, policy decision, design analysis, staged Java/JUnit/OpenAPI output, test evidence, final engineering summary, release validation, rollback evidence when applicable, and an append-only audit event stream.

## Fastest full-stack start

Prerequisites: Docker Desktop / Docker Engine with Compose.

```bash
docker compose up --build
```

Then open:

- Java API docs: `http://localhost:8080/docs`
- Python orchestrator docs: `http://localhost:8000/docs`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin` for the local demo)

### Create a URL

```bash
curl -s -X POST http://localhost:8080/api/v1/links \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com/docs","customAlias":"docs123"}'
```

```bash
curl -i http://localhost:8080/docs123
curl -s http://localhost:8080/api/v1/links/docs123/analytics
```

### Start an ambiguous agentic run

```bash
curl -s -X POST http://localhost:8000/agent/runs \
  -H 'content-type: application/json' \
  -d '{"scenario":"ambiguous","requirement":"Make analytics better and fast for enterprise users."}'
```

The run intentionally pauses at `human_approval_gate`. Resume with a measurable clarification:

```bash
curl -s -X POST http://localhost:8000/agent/runs/RUN_ID/approve \
  -H 'content-type: application/json' \
  -d '{"approved":true,"comment":"Define fast as p95 <= 200ms under the demo load profile; preserve existing fields."}'
```

When running via Docker, the Python testing agent performs a **live cross-language smoke test** against the Java service: create -> redirect -> analytics -> deactivate.

## Local development without Docker

Python:

```bash
cd agent-orchestrator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
python scripts/demo.py
uvicorn app.main:app --reload --port 8000
```

Java:

```bash
cd shortener-service
mvn test
mvn spring-boot:run
```

For a local Java run, start PostgreSQL and Redis or use the Docker services.

## Optional local LLM

The orchestration does **not** require a paid model. Start the optional Ollama profile:

```bash
docker compose --profile llm up --build
```

Pull any compatible local model into Ollama, set `LLM_ENABLED=true`, and restart `agent-orchestrator`. LLM output is advisory only; deterministic policy and governance code remains authoritative, and the workflow records when fallback is used.

## Required assessment scenarios

```bash
cd agent-orchestrator
python scripts/demo.py
```

The demo executes:

1. **Greenfield** — new bulk-shortening capability; low-risk work can auto-advance under policy.
2. **Brownfield** — analytics/schema evolution; agents inspect the Java codebase and pause for change-control approval.
3. **Ambiguous** — vague performance requirement; workflow pauses until a human supplies measurable clarification.

See `docs/ASSIGNMENT_MAPPING.md` for the requirement-by-requirement evidence map and `docs/INTERVIEW_DEMO.md` for a concise presentation flow.
