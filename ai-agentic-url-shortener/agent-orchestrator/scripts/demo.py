from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine import WorkflowEngine


def main():
    engine = WorkflowEngine()
    for path in sorted((ROOT / "scenarios").glob("*.json")):
        spec = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n=== {spec['scenario'].upper()} ===")
        state = engine.create_run(spec["requirement"], spec["scenario"])
        print(f"run_id={state.run_id} status={state.status} risk={state.risk_level}")
        if state.status == "awaiting_approval":
            comment = "Demo approval: additive change only; for ambiguity define analytics p95 <= 200ms."
            print("human approval gate reached -> approving with clarification")
            state = engine.approve(state.run_id, True, comment)
        print(f"final_status={state.status}")
        print("nodes:", " -> ".join(record.node for record in state.node_records))
        print("workspace:", (ROOT / "artifacts" / state.run_id).resolve())


if __name__ == "__main__":
    main()
