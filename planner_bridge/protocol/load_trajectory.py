from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_bundle(path: str | Path) -> dict[str, Any]:
    bundle_path = Path(path)
    if bundle_path.is_dir():
        bundle_path = bundle_path / "trajectory.json"
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    if payload.get("protocol") != "S3-R0-trajectory-protocol-v1":
        raise ValueError("unsupported trajectory protocol")
    return payload
