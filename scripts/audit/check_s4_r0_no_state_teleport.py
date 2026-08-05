"""Audit that S4-R0 only writes root state during episode reset."""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/s4_r0_nominal_dynamics_demo.py"


def main() -> int:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    writes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"set_world_pose", "set_linear_velocity", "set_angular_velocity", "set_world_poses", "set_velocities", "set_joint_positions", "set_joint_velocities"}:
            writes.append((node.func.attr, node.lineno))
    reset_lines = {node.lineno for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_reset_episode"}
    source = SCRIPT.read_text(encoding="utf-8").splitlines()
    illegal = [(name, line) for name, line in writes if not any(start <= line <= start + 30 for start in reset_lines)]
    records = []
    for path in (ROOT / "outputs/S4-R0").glob("**/state.jsonl"):
        records.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    assert records, "no S4-R0 state records"
    assert not illegal, f"post-reset state writes found: {illegal}"
    assert max(item["post_reset_state_write_count"] for item in records) == 0
    assert max(item["post_reset_active_joint_state_write_count"] for item in records) == 0
    assert all(item["physics_integrated_state"] for item in records)
    payload = {"pass": True, "state_write_calls": writes, "records": len(records), "max_post_reset_root_writes": 0, "max_post_reset_joint_writes": 0}
    out = ROOT / "docs/evidence/S4-R0/preflight/no_state_teleport_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
