from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api_models import AgentRunRequest, ApprovalRequest, ReplanRequest
from app.engine import engine

app = FastAPI(
    title="Agentic SDLC Orchestrator",
    version="1.0.0",
    description="Python controlled-autonomy orchestration layer for a Java/Spring Boot URL shortener.",
)


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/agent/runs", status_code=201)
def create_run(payload: AgentRunRequest):
    try:
        return engine.create_run(payload.requirement, payload.scenario, payload.auto_approve).snapshot()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/agent/runs/{run_id}")
def get_run(run_id: str):
    state = engine.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="run not found")
    return state.snapshot()


@app.post("/agent/runs/{run_id}/approve")
def approve(run_id: str, payload: ApprovalRequest):
    try:
        return engine.approve(run_id, payload.approved, payload.comment).snapshot()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/agent/runs/{run_id}/replan")
def replan(run_id: str, payload: ReplanRequest):
    try:
        return engine.replan(run_id, payload.requirement).snapshot()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
