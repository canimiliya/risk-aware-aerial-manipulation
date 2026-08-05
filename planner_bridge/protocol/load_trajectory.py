from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from planner_bridge.protocol.polynomial import evaluate_message


def load_bundle(path: str | Path) -> dict[str, Any]:
    bundle_path = Path(path)
    if bundle_path.is_dir():
        bundle_path = bundle_path / "trajectory.json"
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    if payload.get("protocol") != "S3-R0-trajectory-protocol-v1":
        raise ValueError("unsupported trajectory protocol")
    payload["_bundle_path"] = str(bundle_path.resolve())
    return payload


def load_raw_polynomials(bundle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle_path = Path(bundle.get("_bundle_path", ""))
    if not bundle_path:
        raise ValueError("bundle loaded without a source path")
    root = bundle_path.parent
    source = bundle.get("source", {})
    base_name = source.get("raw_base_polynomial", "raw_base_polynomial.json")
    arm_name = source.get("raw_arm_polynomial", "raw_arm_polynomial.json")
    return (
        json.loads((root / base_name).read_text(encoding="utf-8")),
        json.loads((root / arm_name).read_text(encoding="utf-8")),
    )


def evaluate_raw_polynomials(bundle: dict[str, Any], times: Any) -> dict[str, Any]:
    base_payload, arm_payload = load_raw_polynomials(bundle)
    base = evaluate_message(base_payload, times)
    arm = evaluate_message(arm_payload, times)
    return {"base": base, "arm": arm}
