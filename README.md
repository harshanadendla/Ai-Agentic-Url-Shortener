# Ai-Agentic-Url-Shortener

# Agentic URL Shortener

A URL-shortening service with a separate agentic engineering workflow. Java/Spring Boot serves the product API; Python/FastAPI coordinates requirements analysis, planning, design, implementation artifacts, validation, and human approval.

This is a prototype for demonstrating controlled agent autonomy. Generated changes are staged in isolated workspaces for review; workflows do not automatically merge or deploy them. The default workflow runs without an LLM or paid API key.

## Technology stack

| Component | Technology |
| --- | --- |
| URL API | Java 21, Spring Boot 3.3.5, Maven |
| Agent orchestrator | Python 3.12, FastAPI |
| Persistent storage | PostgreSQL 16, Flyway |
| Cache and rate limiting | Redis 7 |
| Monitoring | Prometheus, Grafana |
| Optional local model | Ollama |
| Tests | JUnit, Spring Boot Test, H2, pytest |

## Run with Docker (recommended)

Install Docker Engine with Compose v2, or Docker Desktop. No local Java, Maven, or Python installation is needed for this path. Initial builds require internet access to download images and dependencies.

Navigate to the repository directory containing `docker-compose.yml`:

```bash
cd ai-agentic-url-shortener
docker compose up --build -d
docker compose ps
```

If already in the repository root, skip the `cd` command. The first build can take several minutes. The orchestrator starts after the Java service passes its health check.

Verify both services:

```bash
curl -f http://localhost:8080/actuator/health
curl -f http://localhost:8000/health
```

| Service | Address |
| --- | --- |
| Java Swagger UI | http://localhost:8080/docs |
| Python Swagger UI | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Grafana's demo credentials are `admin` / `admin`. Prometheus is provisioned as a Grafana data source; dashboards can be created from the available metrics. Ports 5432 and 6379 are also exposed for PostgreSQL and Redis.

View logs:

```bash
docker compose logs -f shortener-service agent-orchestrator
```

Stop the stack:

```bash
docker compose down
```

`docker compose down` preserves named data volumes and generated artifacts.

For a clean database/cache/monitoring reset:

```bash
docker compose down -v
```

This deletes the stack's named volumes. Use it only when you want to discard that data. Artifacts in `agent-orchestrator/artifacts/` remain on disk.

## Try the URL API

### Create a short link

```bash
curl -i -X POST http://localhost:8080/api/v1/links \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/docs","customAlias":"docs123"}'
```

`customAlias` is optional; omit it to generate a code. Custom aliases must contain 4–32 letters, digits, underscores, or hyphens. Optional `expiresAt` accepts a future ISO-8601 timestamp.

Reusing an existing alias produces a conflict; choose another alias when repeating this example.

### Redirect and inspect analytics

```bash
curl -i http://localhost:8080/docs123
curl -s http://localhost:8080/api/v1/links/docs123/analytics
```

The redirect returns HTTP **307** with a `Location` header. Use `curl -i` to inspect it, or open the short URL in a browser. Analytics includes click count and lifecycle metadata.

### Deactivate the link

```bash
curl -i -X DELETE http://localhost:8080/api/v1/links/docs123
```

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/v1/links` | Create a link |
| GET | `/{code}` | Redirect to its destination |
| GET | `/api/v1/links/{code}/analytics` | Read analytics |
| DELETE | `/api/v1/links/{code}` | Deactivate a link |

The service includes URL validation, bounded code-generation retries, database uniqueness, atomic click increments, Redis caching with database fallback, and create-rate limiting.

## Try the agent workflow

Supported scenarios are `greenfield`, `brownfield`, and `ambiguous`.

Start a run that requires clarification:

```bash
curl -s -X POST http://localhost:8000/agent/runs \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"ambiguous","requirement":"Make analytics better and fast for enterprise users."}'
```

Copy the returned `run_id` and replace `RUN_ID` below. An ambiguous run pauses with status `awaiting_approval`.

Inspect the run:

```bash
curl -s http://localhost:8000/agent/runs/RUN_ID
```

Approve with measurable clarification:

```bash
curl -s -X POST http://localhost:8000/agent/runs/RUN_ID/approve \
  -H 'Content-Type: application/json' \
  -d '{"approved":true,"comment":"Define fast as p95 <= 200ms under the demo load profile; preserve existing fields."}'
```

To reject a paused run, submit `approved: false` with a comment.

To revise a requirement and rebuild downstream work:

```bash
curl -s -X POST http://localhost:8000/agent/runs/RUN_ID/replan \
  -H 'Content-Type: application/json' \
  -d '{"requirement":"Add daily analytics buckets while preserving existing response fields."}'
```

Run all three bundled scenarios inside the Docker container:

```bash
docker compose exec agent-orchestrator python scripts/demo.py
```

The demo script supplies approval comments automatically for demonstration purposes. API-based approval allows you to review and decide manually.

With the Compose configuration, the testing agent also exercises the live Java API: create → redirect → analytics → deactivate.

Artifacts are written to `agent-orchestrator/artifacts/<run-id>/`, including requirements, dependency graphs, policy decisions, repository impact analysis, staged Java/JUnit/OpenAPI files, test evidence, engineering summaries, state, and audit events.

## Local development

Requirements:

- Java **21**
- Maven **3.9+** recommended
- Python **3.12**
- PostgreSQL and Redis

This repository does not include a Maven wrapper; use `mvn`.

### 1. Start infrastructure

From the repository root:

```bash
docker compose up -d postgres redis
```

This uses the supplied PostgreSQL database, user, and password: `shortener`. Redis listens on port 6379.

### 2. Start Java

In a separate terminal, starting from the repository root:

```bash
cd shortener-service
mvn spring-boot:run
```

The default configuration connects to PostgreSQL and Redis on `localhost` and serves HTTP on port 8080. Flyway applies the database migrations at startup.

### 3. Start Python

In another terminal, starting from the repository root:

```bash
cd agent-orchestrator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

Local Python workflows default to `LIVE_SERVICE_VALIDATION=false`.

To exercise the running Java service, stop Uvicorn and restart it on macOS/Linux with:

```bash
LIVE_SERVICE_VALIDATION=true uvicorn app.main:app --reload --port 8000
```

The local demo can also run independently of a live Java server with the default validation settings:

```bash
python scripts/demo.py
```

## Run tests

### Java tests

From the repository root:

```bash
cd shortener-service
mvn test
```

The Java test configuration uses H2 rather than the production PostgreSQL database.

### Python tests

From the repository root, after creating and activating the Python virtual environment:

```bash
cd agent-orchestrator
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The Python suite covers workflow execution, approval and rejection, policy blocking, replanning, retry exhaustion, and workspace path protection. It disables live service and Maven validation for isolated workflow testing.

### Both suites

With Java/Maven and the Python dependencies available in your active environment, run both suites from the repository root:

```bash
make test
```

Docker runs the application but does not replace these test commands. The Python runtime image does not install pytest, so run the Python suite in the development environment described above.

## Configuration

| Variable | Default for local development | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `jdbc:postgresql://localhost:5432/shortener` | Java database connection |
| `DATABASE_USER` / `DATABASE_PASSWORD` | `shortener` / `shortener` | Database credentials |
| `REDIS_HOST` / `REDIS_PORT` | `localhost` / `6379` | Redis connection |
| `PUBLIC_BASE_URL` | `http://localhost:8080` | Returned short-link base URL |
| `SERVER_PORT` | `8080` | Java HTTP port |
| `CREATE_RATE_LIMIT_PER_MINUTE` | `60` | Create-request rate limit |
| `WORKSPACE_ROOT` | `artifacts` | Python artifact directory |
| `SHORTENER_REPO_ROOT` | `../shortener-service` | Repository inspected by agents |
| `SHORTENER_BASE_URL` | `http://localhost:8080` | Java URL used for live validation |
| `LIVE_SERVICE_VALIDATION` | `false` | Enable live API smoke testing |
| `LLM_ENABLED` | `false` | Enable advisory local-model calls |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Local model name |
| `MAX_AGENT_RETRIES` | `2` | Retry configuration |
| `RUN_MAVEN_VALIDATION` | `false` | Request Maven validation from the testing agent |

Compose supplies container hostnames and enables live service validation. Its Python container does not include Maven or a JDK; use a suitably provisioned local environment for Maven validation.

### Optional Ollama model

The default deterministic workflow needs no model.

For advisory model output, start Ollama and download the configured model:

```bash
docker compose --profile llm up -d ollama
docker compose exec ollama ollama pull qwen2.5-coder:7b
```

For a locally running Python service, launch from `agent-orchestrator/` with:

```bash
LLM_ENABLED=true uvicorn app.main:app --reload --port 8000
```

For the containerized orchestrator, change its `LLM_ENABLED` value in `docker-compose.yml` from `"false"` to `"true"`, then recreate it:

```bash
docker compose up -d --force-recreate agent-orchestrator
```

Starting the `llm` profile alone does not enable model calls. Model output is advisory; deterministic policy remains authoritative and fallback use is recorded.

Model downloads require disk space and suitable local compute.

## Troubleshooting

- **Port already in use:** stop the conflicting process or adjust Compose's host port mappings. Update examples and `PUBLIC_BASE_URL` when changing the Java host port.
- **Java cannot connect to PostgreSQL:** confirm `docker compose ps`, credentials, and that port 5432 is available. Inspect `docker compose logs postgres shortener-service`.
- **Orchestrator has not started:** it waits for Java health in Compose. Inspect `docker compose logs shortener-service agent-orchestrator`.
- **Python import/dependency errors:** activate the virtual environment and run Python commands from `agent-orchestrator/`.
- **Artifacts permission error on Linux:** ensure the bind-mounted `agent-orchestrator/artifacts/` directory is writable by the container's UID 10001.
- **Alias conflict:** choose a new custom alias or omit it to generate a code.

## Repository layout

| Path | Contents |
| --- | --- |
| `shortener-service/` | Java API, migrations, and tests |
| `agent-orchestrator/app/` | Workflow engine, agents, policy, state, and API |
| `agent-orchestrator/scenarios/` | Three bundled scenario inputs |
| `agent-orchestrator/tests/` | Python workflow tests |
| `agent-orchestrator/artifacts/` | Generated per-run evidence |
| `observability/` | Prometheus and Grafana configuration |
| `docs/` | Architecture, operations, verification, and demo guides |
| `docker-compose.yml` | Local stack definition |
| `Makefile` | Test, demo, and Docker shortcuts |

See [Architecture](docs/ARCHITECTURE.md), [Operations](docs/OPERATIONS.md), [Verification](docs/VERIFICATION.md), [Scenario guide](docs/SCENARIOS.md), [Assessment mapping](docs/ASSIGNMENT_MAPPING.md), and [Interview demo](docs/INTERVIEW_DEMO.md) for further details.

## Scope

This repository demonstrates a working URL API and governed engineering workflows. Staged code and generated evidence require human review before integration. It does not establish production readiness, high-scale performance, or achievement of proposed latency targets.

Demo credentials and exposed local services should be configured appropriately before deployment.

## License

See [LICENSE](LICENSE) for the included license text.
