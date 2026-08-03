from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load_audit(name: str):
    path = ROOT / "scripts/audit" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", [
    "check_s2_r0_workspace_preflight",
    "check_s2_r0_final_acceptance",
    "check_s2_r1_continuous_planning",
])
def test_stage_audits_allow_named_main_and_future_stage_branches(name: str) -> None:
    audit = load_audit(name)
    assert audit.branch_is_allowed("main")
    assert audit.branch_is_allowed("agent/s2-r3-execution-kinematics-collision")
    assert audit.branch_is_allowed("agent/s2-r4-execution-feasible-replanning")
    assert audit.branch_is_allowed("agent/other-named-branch")
    assert not audit.branch_is_allowed("")
    assert not audit.branch_is_allowed("main", "agent/s2-r4-execution-feasible-replanning")
    assert audit.branch_is_allowed("agent/s2-r4-execution-feasible-replanning", "agent/s2-r4-execution-feasible-replanning")

