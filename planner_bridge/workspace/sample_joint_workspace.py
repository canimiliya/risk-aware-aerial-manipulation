from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .delta_arm_model import DeltaArmModel
from .jacobian_metrics import batch_jacobian_metrics


def sample_joint_workspace(model: DeltaArmModel, count: int = 100_000, seed: int = 20260803) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if count < 16:
        raise ValueError("count must be at least 16 so boundary samples are included")
    rng = np.random.default_rng(seed)
    random_q = rng.uniform(model.joint_lower, model.joint_upper, size=(count - 8, 3))
    corners = np.array(np.meshgrid(*zip(model.joint_lower, model.joint_upper))).T.reshape(-1, 3)
    qs = np.vstack([random_q, corners])
    positions, valid = model.fk_batch(qs)
    return qs, positions, valid


def summarize(model: DeltaArmModel, qs: np.ndarray, positions: np.ndarray, valid: np.ndarray) -> dict:
    finite_positions = positions[valid]
    metrics = batch_jacobian_metrics(model, qs[valid])
    return {
        "sample_count": int(len(qs)),
        "valid_fk_count": int(np.count_nonzero(valid)),
        "invalid_fk_count": int(np.count_nonzero(~valid)),
        "random_seed": 20260803,
        "boundary_samples_included": True,
        "position_min_m": finite_positions.min(axis=0).tolist(),
        "position_max_m": finite_positions.max(axis=0).tolist(),
        "jacobian_min_singular_value": float(np.nanmin(metrics["min_singular_value"])),
        "jacobian_condition_p99": float(np.nanpercentile(metrics["condition_number"], 99)),
        "official_geometry": model.params.__dict__,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=100_000)
    args = parser.parse_args()
    model = DeltaArmModel()
    qs, positions, valid = sample_joint_workspace(model, args.count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, q=qs, position=positions, valid=valid)
    summary_path = args.output.with_suffix(".json")
    summary_path.write_text(json.dumps(summarize(model, qs, positions, valid), indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"npz": str(args.output), "summary": str(summary_path), "valid_fk": int(valid.sum())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
