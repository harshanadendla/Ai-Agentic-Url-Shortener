from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.state import WorkflowState


class RunStore:
    """Durable JSON state for restart-safe interview demos without another infrastructure dependency."""

    def _path(self, run_id: str) -> Path:
        return settings.workspace_root / run_id / "state.json"

    def save(self, state: WorkflowState) -> None:
        path = self._path(state.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(state.snapshot(), indent=2, default=str), encoding="utf-8")
        temp.replace(path)

    def load(self, run_id: str) -> WorkflowState | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        return WorkflowState.from_snapshot(json.loads(path.read_text(encoding="utf-8")))
