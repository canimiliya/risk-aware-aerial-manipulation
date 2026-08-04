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
    env = root / "docs/evidence/S3-R0/environment_install_attempt.json"
    environment = json.loads(env.read_text(encoding="utf-8"))
    check("python_311_environment", environment.get("python", "").startswith("3.11"))
    check("isaaclab_import", importlib.util.find_spec("isaaclab") is not None, hard=False)
    check("isaacsim_import", importlib.util.find_spec("isaacsim") is not None, hard=False)
    check("physx_smoke", environment.get("physx_smoke") == "PASS", hard=False)
    decision = "SUBMITTED_S3_R0_BASIC_ENVIRONMENT_READY" if not errors and not warnings else "SUBMITTED_S3_R0_PROTOCOL_READY_PLATFORM_BLOCKED" if not errors else "REVISION_REQUIRED"
    return {"decision": decision, "errors": errors, "warnings": warnings, "checks": checks, "protocol_ready": not errors, "isaac_ready": not warnings and not errors}


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
