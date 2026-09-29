from __future__ import annotations

import json
from pathlib import Path

from app.config import settings


class SafeWorkspace:
    """Per-run write jail. Agent output can never mutate the source repository."""

    def __init__(self, run_id: str):
        self.root = (settings.workspace_root / run_id).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if self.root != candidate and self.root not in candidate.parents:
            raise ValueError("workspace path escape blocked")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    def write_text(self, relative: str, content: str) -> str:
        target = self.path(relative)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def write_json(self, relative: str, value: object) -> str:
        return self.write_text(relative, json.dumps(value, indent=2, default=str) + "\n")

    def append_jsonl(self, relative: str, value: object) -> str:
        target = self.path(relative)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, default=str) + "\n")
        return str(target)
