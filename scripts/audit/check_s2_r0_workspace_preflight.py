from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAIN_HEAD = "685086a4b0ed11487313d8f8b069616ddcbc155b"
AM_PLANNER_COMMIT = "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d"


def run(root: Path = ROOT) -> dict:
    errors: list[str] = []
    checks: dict[str, object] = {}

    def require(label: str, ok: bool, detail: object = None) -> None:
        checks[label] = detail if detail is not None else ok
        if not ok:
            errors.append(label)

    required = [
        root / "docs/evidence/S2-R0/robot_model/source_inventory.md",
        root / "docs/evidence/S2-R0/robot_model/model_files.json",
        root / "docs/evidence/S2-R0/robot_model/frame_tree.md",
        root / "docs/evidence/S2-R0/robot_model/joint_contract.json",
        root / "docs/evidence/S2-R0/robot_model/geometry_contract.json",
        root / "docs/evidence/S2-R0/robot_model/collision_proxy_contract.json",
        root / "docs/evidence/S2-R0/robot_model/unavailable_parameters.md",
        root / "docs/coordinate_frame_contract.md",
        root / "configs/scene/s2_crossarm_nominal.yaml",
        root / "configs/robot/s2_delta_arm.yaml",
        root / "configs/planner/s2_workspace_gate.yaml",
        root / "docs/evidence/S2-R0/workspace_sampling_manifest.json",
        root / "docs/evidence/S2-R0/g_arm_preflight.json",
        root / "docs/reports/S2-R0_delta_workspace_preflight_report.md",
        root / "docs/milestones/S2_R0_status.md",
    ]
    require("required_artifacts", all(path.is_file() and path.stat().st_size > 0 for path in required), [str(path.relative_to(root)) for path in required if not path.is_file()])
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True, check=False).stdout.strip()
    require("s2_branch", branch in {
        "agent/s2-r0-delta-workspace-scene-contract",
        "main",
        "agent/s2-r2-am-planner-crossarm-planning",
    }, branch)
    require("base_main", subprocess.run(["git", "merge-base", "HEAD", "main"], cwd=root, capture_output=True, text=True, check=False).stdout.strip() == MAIN_HEAD)
    require("algorithm_boundary", not subprocess.run(["git", "diff", "--name-only", f"{MAIN_HEAD}..HEAD", "--", "src"], cwd=root, capture_output=True, text=True, check=False).stdout.strip())

    model = json.loads((root / "docs/evidence/S2-R0/robot_model/model_files.json").read_text(encoding="utf-8-sig"))
    joints = json.loads((root / "docs/evidence/S2-R0/robot_model/joint_contract.json").read_text(encoding="utf-8-sig"))
    geometry = json.loads((root / "docs/evidence/S2-R0/robot_model/geometry_contract.json").read_text(encoding="utf-8-sig"))
    require("official_model_commit", model.get("am_planner_commit") == AM_PLANNER_COMMIT and joints.get("am_planner_commit") == AM_PLANNER_COMMIT)
    require("official_joint_contract", joints.get("active_joint_order") == ["m1_1", "m2_1", "m3_1"] and all(item.get("lower_rad") == -1.57 and item.get("upper_rad") == 1.57 for item in joints.get("active_joints", [])))
    require("official_geometry_contract", geometry.get("official_launch_values") == {"static_radius": 0.08, "moving_radius": 0.025, "upper_arm": 0.1, "lower_arm": 0.16, "scale": 1.0})
    config_text = (root / "configs/scene/s2_crossarm_nominal.yaml").read_text(encoding="utf-8-sig")
    require("provisional_scene_marked", "PROVISIONAL_S2_ASSUMPTION" in config_text)
    require("target_fake_declared", "target_fake:" in config_text and "target placeholder" in config_text)
    require("provisional_tool_marked", "PROVISIONAL_S2_ASSUMPTION" in (root / "configs/robot/s2_delta_arm.yaml").read_text(encoding="utf-8-sig"))

    manifest = json.loads((root / "docs/evidence/S2-R0/workspace_sampling_manifest.json").read_text(encoding="utf-8-sig"))
    npz = root / "outputs/workspace/S2-R0/delta_workspace_100k.npz"
    actual_hash = hashlib.sha256(npz.read_bytes()).hexdigest().upper() if npz.is_file() else ""
    require("workspace_manifest", manifest.get("sample_count") == 100000 and manifest.get("random_seed") == 20260803 and manifest.get("boundary_samples_included") is True and actual_hash == manifest.get("local_npz_sha256"), manifest)
    summary = json.loads((root / "outputs/workspace/S2-R0/delta_workspace_100k.json").read_text(encoding="utf-8-sig"))
    require("workspace_summary", summary.get("sample_count") == 100000 and summary.get("valid_fk_count") == 90205 and summary.get("invalid_fk_count") == 9795 and summary.get("boundary_samples_included") is True, summary)
    pose_results = json.loads((root / "outputs/workspace/S2-R0/task_pose_evaluation.json").read_text(encoding="utf-8-sig"))
    require("pose_sensitivity", pose_results.get("loose", {}).get("feasible_count") == 7 and pose_results.get("nominal", {}).get("feasible_count") == 7 and pose_results.get("narrow", {}).get("feasible_count") == 0)
    require("p0_p6", all(len(result.get("poses", [])) == 7 and [item.get("pose") for item in result.get("poses", [])] == ["P0", "P1", "P2", "P3", "P4", "P5", "P6"] for result in pose_results.values()))
    require("workspace_figure", (root / "outputs/figures/S2-R0/delta_workspace.png").is_file() and (root / "outputs/figures/S2-R0/delta_workspace.png").stat().st_size < 2 * 1024 * 1024)

    garm = json.loads((root / "docs/evidence/S2-R0/g_arm_preflight.json").read_text(encoding="utf-8-sig"))
    require("g_arm_decision", garm.get("decision") in {"G_ARM_READY_FOR_FULL_PLANNING", "G_ARM_GEOMETRY_INCONCLUSIVE", "G_ARM_NOT_FEASIBLE_IN_TESTED_GEOMETRY"}, garm.get("decision"))
    require("g_arm_errors", garm.get("errors") == [])
    require("state_gate", garm.get("state") == {"s2_r0": "SUBMITTED_FOR_REVIEW", "s2": "IN_PROGRESS", "s3_s8": "FROZEN"})
    status_text = (root / "docs/milestones/S2_R0_status.md").read_text(encoding="utf-8-sig")
    require("status_document", ("S2-R0：`SUBMITTED_FOR_REVIEW`" in status_text or "S2-R0：`PASS_WITH_LIMITATIONS`" in status_text) and "S2：`IN_PROGRESS`" in status_text and "S3–S8：`FROZEN`" in status_text)

    s0 = subprocess.run([sys.executable, "scripts/audit/check_s0_structure.py"], cwd=root, capture_output=True, text=True, check=False)
    require("s0_audit", s0.returncode == 0, s0.stdout[-1000:])
    s1 = subprocess.run([sys.executable, "scripts/audit/check_s1_final_acceptance.py", "--output", "docs/evidence/S1/final_acceptance/s1_final_acceptance.json"], cwd=root, capture_output=True, text=True, check=False)
    require("s1_audit", s1.returncode == 0, s1.stdout[-1000:])
    credential = re.compile(r"ghp_|github_pat_|AKIA|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY", re.I)
    scoped = [root / "configs", root / "planner_bridge/workspace", root / "docs/evidence/S2-R0", root / "docs/reports/S2-R0_delta_workspace_preflight_report.md"]
    hits = [str(path.relative_to(root)) for base in scoped for path in ([base] if base.is_file() else base.rglob("*")) if path.is_file() and path.stat().st_size < 2 * 1024 * 1024 and credential.search(path.read_text(encoding="utf-8", errors="ignore"))]
    require("credential_scan", not hits, hits)
    large = [str(path.relative_to(root)) for base in scoped for path in ([base] if base.is_file() else base.rglob("*")) if path.is_file() and path.stat().st_size > 10 * 1024 * 1024]
    require("large_file_scan", not large, large)
    result = {"decision": "SUBMITTED_S2_R0_G_ARM_READY" if not errors and garm.get("decision") == "G_ARM_READY_FOR_FULL_PLANNING" else ("SUBMITTED_S2_R0_GEOMETRY_INCONCLUSIVE" if not errors else "REVISION_REQUIRED"), "errors": errors, "warnings": [], "checks": checks, "g_arm_decision": garm.get("decision")}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/evidence/S2-R0/final_acceptance/s2_r0_workspace_preflight_audit.json"))
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "errors": result["errors"], "warnings": result["warnings"]}, ensure_ascii=False))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
