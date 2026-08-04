from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.audit.check_s3_s2_baseline import run as run_baseline
from planner_bridge.protocol.load_trajectory import load_bundle
from planner_bridge.protocol.validation import validate_bundle


def run(root: Path = ROOT) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}

    def check(name: str, value: bool, hard: bool = True) -> None:
        checks[name] = value
        if not value:
            (errors if hard else warnings).append(name)

    baseline = run_baseline(root)
    check("authoritative_s2_baseline", baseline["decision"] == "PASS")
    for variant in ("nominal_100w0", "nominal_repeat_100w0"):
        bundle = load_bundle(root / "data/trajectories/S3-R0" / variant)
        check(f"{variant}_protocol", not validate_bundle(bundle))
        check(f"{variant}_raw_polynomials", all((root / "data/trajectories/S3-R0" / variant / name).is_file() for name in ("raw_base_polynomial.json", "raw_arm_polynomial.json")))
    scene = json.loads((root / "docs/evidence/S3-R0/scene_contract.json").read_text(encoding="utf-8"))
    check("scene_contract", scene.get("playback_mode") == "REFERENCE_STATE_PLAYBACK")
    gate_path = root / "docs/evidence/S3-R0/environment/environment_gate.json"
    if gate_path.is_file():
        environment = json.loads(gate_path.read_text(encoding="utf-8"))
        check("python_311_environment", environment.get("python", "").startswith("3.11"))
        check("isaaclab_import", bool(environment.get("isaaclab_import")), hard=False)
        check("isaacsim_import", bool(environment.get("isaacsim_import")), hard=False)
        check("physx_smoke", bool(environment.get("physx_smoke")), hard=False)
    else:
        env = root / "docs/evidence/S3-R0/environment_install_attempt.json"
        environment = json.loads(env.read_text(encoding="utf-8"))
        check("python_311_environment", environment.get("python", "").startswith("3.11"))
        check("isaaclab_import", importlib.util.find_spec("isaaclab") is not None, hard=False)
        check("isaacsim_import", importlib.util.find_spec("isaacsim") is not None, hard=False)
        check("physx_smoke", environment.get("physx_smoke") == "PASS", hard=False)
    playback_path = root / "docs/evidence/S3-R0/isaac_playback_nominal_v14.json"
    if not playback_path.is_file():
        playback_path = root / "docs/evidence/S3-R0/isaac_playback_nominal_v3.json"
    playback = json.loads(playback_path.read_text(encoding="utf-8")) if playback_path.is_file() else {}
    if playback:
        check("playback_runs", playback.get("frames", 0) > 0 and playback.get("finite") is True and playback.get("monotonic_time") is True)
        check("joint_mapping_error", playback.get("max_joint_state_write_readback_error_rad", float("inf")) <= 1e-8)
        check("arm_fk_error", playback.get("max_arm_fk_error_m", float("inf")) <= 1e-5)
        check("world_ee_error", playback.get("max_world_ee_error_m", float("inf")) <= 1e-4)
        check("contact_query", playback.get("contact_query") == "PASS")
        check("clearance_gate", playback.get("clearance_gate") == "PASS")
    if not errors and not warnings:
        decision = "SUBMITTED_S3_R0_BASIC_ENVIRONMENT_READY"
    elif playback and any(name in errors for name in ("joint_mapping_error", "arm_fk_error", "world_ee_error")):
        decision = "SUBMITTED_S3_R0_FK_FAILED"
    elif playback and any(name in errors for name in ("contact_query", "clearance_gate")):
        decision = "SUBMITTED_S3_R0_PLAYBACK_FAILED"
    elif not errors:
        decision = "SUBMITTED_S3_R0_PROTOCOL_READY_DEPENDENCY_INSTALL_BLOCKED"
    else:
        decision = "REVISION_REQUIRED"
    protocol_checks = [name for name in checks if name.endswith("_protocol") or name.endswith("_raw_polynomials") or name == "authoritative_s2_baseline" or name == "scene_contract"]
    environment_checks = ["python_311_environment", "isaaclab_import", "isaacsim_import", "physx_smoke"]
    return {
        "decision": decision,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "protocol_ready": all(checks.get(name, False) for name in protocol_checks),
        "isaac_ready": all(checks.get(name, False) for name in environment_checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(payload, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
