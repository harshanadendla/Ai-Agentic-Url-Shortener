# Verification

## Automated checks included

### Python orchestrator

```bash
cd agent-orchestrator
pytest
python scripts/demo.py
```

The suite covers the full graph, Java brownfield inspection, human approval, rejection/safe-stop, blocked policy, replanning, retry exhaustion and workspace path-jail behavior. The demo executes all three required scenarios and syntax-compiles staged Java artifacts with `javac` when it is available.

### Java product service

```bash
cd shortener-service
mvn test
```

The Maven suite includes URL policy, service behavior/collision boundaries and MVC contract tests. The Docker build also runs `mvn test package`; therefore `docker compose up --build` acts as a clean build gate before the Java container can start.

### Full-stack contract

With Docker Compose running, `LIVE_SERVICE_VALIDATION=true` in the Python container. Every workflow that reaches the testing stage performs a live cross-language contract check against Spring Boot:

`health -> create -> redirect(307) -> analytics(click >= 1) -> deactivate`.

## Environment note

A development environment without Maven or Docker can still run all Python orchestration tests and `javac` validation of staged pure-Java artifacts. Full Spring dependency resolution requires Maven/Docker access to Maven Central.
