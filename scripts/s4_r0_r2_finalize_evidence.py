"""Finalize honest R2 evidence semantics after the native visual failure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R2_DIR = ROOT / "docs/evidence/S4-R0/visuals/r2"
OLD_MANIFEST = ROOT / "docs/evidence/S4-R0/visuals/s4_r0_visual_manifest.json"
SOURCE = Path(r"D:/i3/a/aerial_manipulator_v2.usd")
SOURCE_SHA256 = "74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    R2_DIR.mkdir(parents=True, exist_ok=True)
    old = json.loads(OLD_MANIFEST.read_text(encoding="utf-8")) if OLD_MANIFEST.is_file() else {}
    crash = json.loads((R2_DIR / "visual_crash_matrix.json").read_text(encoding="utf-8"))
    cache = json.loads((R2_DIR / "visual_cache_manifest.json").read_text(encoding="utf-8"))
    payload = {
        "decision": "BLOCKED_S4_R0_R2_NATIVE_VISUAL_PIPELINE_UNRESOLVED",
        "available": False,
        "pass": False,
        "runtime_stable": False,
        "live_gui_dynamics_capture_pass": False,
        "visual_evidence_pass": False,
        "source_usd": str(SOURCE.resolve()),
        "source_sha256": SOURCE_SHA256,
        "dynamic_base_prim": "/World/QuadrotorBase",
        "visual_root_prim": "/World/RobotVisual",
        "root_teleport": False,
        "r2_png_count": 0,
        "r2_video_count": 0,
        "r2_curve_count": 0,
        "r2_png": [],
        "r2_video": [],
        "r2_curves": [],
        "crash_matrix": str((R2_DIR / "visual_crash_matrix.json").resolve()),
        "visual_cache_manifest": str((R2_DIR / "visual_cache_manifest.json").resolve()),
        "visual_link_binding": {"available": False, "pass": False, "reason": "live visual link update/capture route exits natively before an auditable R2 manifest can be produced"},
        "legacy_preserved_evidence": {"manifest": str(OLD_MANIFEST.resolve()), "manifest_sha256": sha256(OLD_MANIFEST) if OLD_MANIFEST.is_file() else None, "png_count": int(old.get("png_count", 0)), "video_count": int(old.get("video_count", 0)), "curve_count": len(old.get("curves", [])), "classification": "legacy_S4-R0_preserved_not_promoted_to_R2"},
        "reason": "P0-P3 independent probes do not produce a stable, auditable R2 live viewport capture; route-B flattened cache fails Mesh and physics-schema hard gates. Existing R0 visual artifacts remain historical evidence only.",
    }
    (R2_DIR / "s4_r0_r2_visual_manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (R2_DIR / "visual_link_binding.json").write_text(json.dumps({"available": False, "pass": False, "source_usd": str(SOURCE.resolve()), "source_sha256": SOURCE_SHA256, "stage_prim": "/World/RobotVisual", "dynamic_base_prim": "/World/QuadrotorBase", "required_links": ["body", "end_effector", "AA_1", "AA_2", "AA_3", "TA_1l", "TA_1r", "TA_2l", "TA_2r", "TA_3l", "TA_3r"], "reason": "P0-P3 native capture/link-update failure prevented a stable runtime binding audit; no residuals are promoted."}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    readiness = {
        "decision": payload["decision"],
        "errors": ["native_visual_pipeline_unresolved", "visual_cache_build_failed", "visual_evidence_incomplete"],
        "warnings": ["route-B analytic COM surrogate; no full closed-chain articulation dynamics", "full nominal AM-Planner trajectory closed loop is not in scope", "physics contact unavailable because dynamic proxy collision is intentionally disabled; sampled-proxy clearance is the safety evidence", "R2 does not change the accepted S4-R0 dynamics/control results", "S5-S8 remain frozen"],
        "dynamic_model_mode": "BASE_DYNAMIC_ARM_REACTION_SURROGATE_V1",
        "physics_integrated_root": True,
        "reaction_acceleration_contract_pass": True,
        "arm_mass_provenance_pass": True,
        "real_robot_visual_binding_pass": False,
        "visual_runtime_stable": False,
        "live_gui_dynamics_capture_pass": False,
        "hover_hold_pass": True,
        "initial_offset_recovery_pass": True,
        "arm_motion_hold_pass": True,
        "visual_evidence_pass": False,
        "automated_metrics_pass": True,
        "full_closed_chain_dynamics": False,
        "full_nominal_trajectory_closed_loop": False,
        "s4_final_ready": False,
        "s5_ready": False,
        "formal_progress": "4/9≈44%",
        "s4_status": "IN_PROGRESS",
        "s4_r0_status": "SUBMITTED_FOR_REVIEW",
        "s5_s8_status": "FROZEN",
        "r2_visual_manifest": str((R2_DIR / "s4_r0_r2_visual_manifest.json").resolve()),
    }
    (ROOT / "docs/evidence/S4-R0/summary/s4_r0_r2_readiness.json").write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": payload["decision"], "legacy_png_count": payload["legacy_preserved_evidence"]["png_count"], "r2_png_count": payload["r2_png_count"]}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
