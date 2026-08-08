"""Promote or block the S4-R4 readiness label from machine evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S4-R4"


def read(relative: str) -> dict:
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))


def main() -> int:
    design = read("design/rrrp_design_manifest.json")
    runtime = read("summary/s4_r4_runtime_result.json")
    audit = read("runtime/state_write_audit.json")
    momentum = read("runtime/momentum_validation.json")
    prismatic = read("runtime/prismatic_validation.json")
    tests = read("tests/base_vs_head_pytest.json") if (EVIDENCE / "tests/base_vs_head_pytest.json").is_file() else {"head_only_failures": None}
    native = bool(runtime.get("fixed_articulation_present") and runtime.get("floating_articulation_present"))
    stability = bool(runtime.get("fixed_base_2000_step_stable") and runtime.get("floating_base_2000_step_stable"))
    responses = all(bool(runtime.get(key)) for key in ("q1_native_response", "q2_native_response", "q3_native_response", "p_native_response", "base_dynamic_response_from_arm"))
    hard_pass = bool(native and stability and responses and design.get("all_dynamic_links_positive_mass") and design.get("all_inertias_physically_valid") and audit.get("audit_pass") and not audit.get("python_arm_integrator_present") and not audit.get("manual_reaction_present") and not audit.get("manual_arm_gravity_present") and not audit.get("root_runtime_state_write") and not audit.get("joint_runtime_position_write") and not audit.get("joint_runtime_velocity_write") and momentum.get("pass") and prismatic.get("all_cases_within_limit") and tests.get("head_only_failures") == [])
    label = "S4_R4_RRRP_NATIVE_DYNAMICS_READY" if hard_pass else "BLOCKED_S4_R4_RRRP_NATIVE_DYNAMICS_GATE"
    readiness = {"task": "S4-R4-RRRP-NATIVE-DYNAMICS-R1", "final_label": label, "active_manipulator": "RRRP", "legacy_delta_asset": True, "active_manipulator_is_delta": False, "rrrp_asset_created": True, "articulation_present": native, "revolute_dof": 3, "prismatic_dof": 1, "dof_count": 4, "total_arm_mass_kg": design.get("total_arm_mass_kg"), "max_geometric_reach_m": design.get("max_geometric_reach_m"), "p_stroke_m": design.get("p_stroke_m"), "parameter_provenance": design.get("parameter_provenance"), "provisional": design.get("provisional"), "all_link_inertia_valid": bool(design.get("all_inertias_physically_valid")), "python_arm_integrator_disabled": not bool(audit.get("python_arm_integrator_present")), "manual_reaction_disabled": not bool(audit.get("manual_reaction_present")), "manual_arm_gravity_disabled_native": not bool(audit.get("manual_arm_gravity_present")), "physx_joint_state_readback": True, "fixed_base_2000_step": "PASS" if runtime.get("fixed_base_2000_step_stable") else "FAIL", "floating_base_2000_step": "PASS" if runtime.get("floating_base_2000_step_stable") else "FAIL", "base_response_q1": bool(runtime.get("q1_native_response")), "base_response_p": bool(runtime.get("p_native_response")), "base_dynamic_response_from_arm": bool(runtime.get("base_dynamic_response_from_arm")), "linear_momentum_relative_drift": runtime.get("linear_momentum_relative_drift"), "linear_momentum_gate": bool(momentum.get("pass")), "root_runtime_state_write": bool(audit.get("root_runtime_state_write")), "joint_runtime_position_write": bool(audit.get("joint_runtime_position_write")), "joint_runtime_velocity_write": bool(audit.get("joint_runtime_velocity_write")), "head_only_failures": tests.get("head_only_failures"), "full_rotor_actuation": False, "hardware_parameter_validated": False, "contact_dynamics_validated": False, "s4_ready": False, "hard_pass": hard_pass, "block_reasons": []}
    if not momentum.get("pass"):
        readiness["block_reasons"].append("linear momentum relative drift is above 1 percent")
    if tests.get("head_only_failures") != []:
        readiness["block_reasons"].append("head-only regression comparison is not clean")
    (EVIDENCE / "summary/s4_r4_readiness.json").write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"final_label": label, "hard_pass": hard_pass, "momentum": readiness["linear_momentum_relative_drift"], "head_only_failures": readiness["head_only_failures"]}, ensure_ascii=False))
    return 0 if hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
