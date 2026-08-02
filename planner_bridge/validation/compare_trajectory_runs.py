"""Compare two exported base trajectories using the contract fields."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np


def load(directory: Path) -> tuple[dict, dict]:
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    npz = np.load(directory / "sampled_trajectory.npz")
    return metadata, {key: npz[key] for key in npz.files}


def planning_time_ms(metadata: dict) -> float | None:
    source = Path(metadata["source_evidence_path"])
    log = source / "roslaunch.log"
    if not log.is_file():
        return None
    match = re.search(r"Optimization time usage:\s*([0-9.]+)\s*ms", log.read_text(encoding="utf-8", errors="replace"))
    return float(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("variant", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base_meta, base = load(args.baseline)
    var_meta, variant = load(args.variant)
    common = np.linspace(0.0, 1.0, 1001)
    base_fraction = base["time"] / float(base["time"][-1])
    variant_fraction = variant["time"] / float(variant["time"][-1])
    base_position = np.column_stack([np.interp(common, base_fraction, base["position"][:, axis]) for axis in range(3)])
    variant_position = np.column_stack([np.interp(common, variant_fraction, variant["position"][:, axis]) for axis in range(3)])
    displacement = np.linalg.norm(base_position - variant_position, axis=1)
    result = {
        "baseline": str(args.baseline).replace("\\", "/"),
        "variant": str(args.variant).replace("\\", "/"),
        "baseline_segment_count": base_meta["segment_count"],
        "variant_segment_count": var_meta["segment_count"],
        "baseline_total_duration": base_meta["total_duration"],
        "variant_total_duration": var_meta["total_duration"],
        "endpoint_delta": (base_position[-1] - variant_position[-1]).tolist(),
        "min_position_difference": float(displacement.min()),
        "max_position_difference": float(displacement.max()),
        "planning_time": {
            "baseline_ms": planning_time_ms(base_meta),
            "variant_ms": planning_time_ms(var_meta),
            "note": "derived from preserved roslaunch.log, not from PolynomialTrajectory fields",
        },
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
