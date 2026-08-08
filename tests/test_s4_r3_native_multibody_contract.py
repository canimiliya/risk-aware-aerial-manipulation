"""Fail-safe contract tests for the S4-R3 asset blocker.

These tests ensure an unresolved source topology cannot be promoted to a
native-physics or S4 readiness claim.  They are not a substitute for the
runtime qualification that remains intentionally unrun.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "docs/evidence/S4-R3/asset/native_asset_manifest.json"
TOPOLOGY = ROOT / "docs/evidence/S4-R3/asset/delta_topology_manifest.json"
RUNTIME = ROOT / "docs/evidence/S4-R3/runtime/native_runtime_manifest.json"
STATE_AUDIT = ROOT / "docs/evidence/S4-R3/runtime/state_write_audit.json"
READY = ROOT / "docs/evidence/S4-R3/summary/s4_r3_readiness.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_native_mode_does_not_use_python_joint_integrator() -> None:
    readiness = _read(READY)
    audit = _read(STATE_AUDIT)
    assert readiness["native_multibody_mode_implemented"] is False
    assert audit["native_execution_path_present"] is False
    assert audit["legacy_python_joint_integrator_present"] is True


def test_native_mode_does_not_apply_surrogate_reaction() -> None:
    readiness = _read(READY)
    reaction = _read(ROOT / "docs/evidence/S4-R3/runtime/internal_reaction_metrics.json")
    assert readiness["manual_arm_reaction_disabled_native"] is False
    assert reaction["native_solver_generated_coupling"] is False


def test_native_mode_does_not_apply_manual_arm_gravity() -> None:
    readiness = _read(READY)
    assert readiness["manual_arm_gravity_disabled_native"] is False
    assert _read(STATE_AUDIT)["legacy_mode_required"] is True


def test_native_mode_reads_joint_state_from_physx() -> None:
    assert _read(READY)["physx_joint_state_readback"] is False
    assert _read(RUNTIME)["native_execution_started"] is False


def test_native_mode_has_floating_base() -> None:
    asset = _read(ASSET)
    assert asset["uav_base_rigid_body_found"] is False
    assert asset["floating_base_articulation_candidate"] is False


def test_native_delta_loop_exists() -> None:
    topology = _read(TOPOLOGY)
    assert topology["closed_chain_expected"] is True
    assert topology["reconstructable"] is False
    assert topology["loop_edges"] == []


def test_passive_joints_are_not_position_driven() -> None:
    asset = _read(ASSET)
    audit = _read(STATE_AUDIT)
    assert asset["passive_joint_count_candidate"] == 6
    assert audit["joint_position_written_during_simulation"] is False


def test_native_simulation_has_no_runtime_state_write() -> None:
    audit = _read(STATE_AUDIT)
    assert audit["root_state_written_after_reset"] is False
    assert audit["joint_position_written_during_simulation"] is False
    assert audit["joint_velocity_written_during_simulation"] is False


def test_native_simulation_1000_steps_finite() -> None:
    runtime = _read(RUNTIME)
    assert runtime["status"] == "NOT_RUN_ASSET_BLOCKER"
    assert runtime["headless_1000_step_stable"] is False
    assert runtime["nan_count"] is None
    assert runtime["inf_count"] is None
