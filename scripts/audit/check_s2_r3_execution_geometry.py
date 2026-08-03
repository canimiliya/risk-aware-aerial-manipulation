from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    errors: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(name)

    source_hashes = ROOT / "planner_bridge/execution/source_hashes.json"
    validation = ROOT / "docs/evidence/S2-R3/validation/s2_r3_execution_validation.json"
    require("source_hashes", source_hashes.exists())
    require("validation", validation.exists())
    if validation.exists():
        report = json.loads(validation.read_text(encoding="utf-8"))
        require("allowed_decision", report.get("decision") in {"S2_R3_FULL_BODY_PROXY_READY", "S2_R3_IK_FAILED", "S2_R3_ATTITUDE_FAILED", "S2_R3_FULL_BODY_CLEARANCE_FAILED", "S2_R3_GEOMETRY_INCONCLUSIVE"})
        require("official_commit", report.get("official_source_commit") == "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d")
        require("five_variants", set(report.get("variants", {})) == {"smoke_free", "loose", "nominal", "nominal_repeat", "narrow"})
        require("nominal_repeat", report.get("nominal_repeat", {}).get("joint_q_max_abs_delta_rad") == 0.0 and report.get("nominal_repeat", {}).get("clearance_min_delta_m") == 0.0)
        for variant in report.get("variants", {}):
            for hz in ("100", "200", "400", "800"):
                entry = report["variants"][variant]["rates"].get(hz, {})
                require(f"{variant}_{hz}_kinematics", entry.get("kinematics", {}).get("finite") is True)
                require(f"{variant}_{hz}_attitude", entry.get("attitude", {}).get("finite") is True and entry.get("attitude", {}).get("rotation_pass") is True)
                require(f"{variant}_{hz}_collision", entry.get("collision", {}).get("finite") is True)
                require(f"{variant}_{hz}_components", len(entry.get("collision", {}).get("component_clearance_m", {})) == 16)

    contract_files = [
        "ik_contract.md", "joint_convention.md", "joint_points_contract.md", "flatness_attitude_contract.md",
        "trajectory_playback_contract.md", "body_rotor_geometry_contract.md", "unavailable_geometry.md"
    ]
    for name in contract_files:
        require(f"contract_{name}", (ROOT / "docs/evidence/S2-R3/execution_contract" / name).exists())
    require("kinematics_summary", (ROOT / "docs/evidence/S2-R3/kinematics/s2_r3_kinematics_summary.json").exists())
    require("geometry_manifest", (ROOT / "docs/evidence/S2-R3/geometry/geometry_manifest.json").exists())
    require("ros_playback_status", (ROOT / "docs/evidence/S2-R3/ros_playback/ros_playback_status.json").exists())
    visual_dir = ROOT / "docs/evidence/S2-R3/visuals"
    pngs = list(visual_dir.glob("*.png"))
    gifs = list(visual_dir.glob("*.gif"))
    require("eight_pngs", len(pngs) >= 8)
    require("two_local_gifs", len(gifs) >= 2)
    require("video_manifest", (visual_dir / "visual_manifest.json").exists())
    require("no_algorithm_source_in_project_wrapper", not any(ROOT.glob("planner_bridge/execution/*cpp")))
    result = {"decision": "PASS" if not errors else "FAIL", "errors": errors, "warnings": [], "checks": checks, "s2_r3_submitted_status": "SUBMITTED_FOR_REVIEW", "s2_status": "IN_PROGRESS", "s3_to_s8_status": "FROZEN"}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
