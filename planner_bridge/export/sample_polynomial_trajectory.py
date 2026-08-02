"""CLI for sampling a saved PolynomialTrajectory message."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from planner_bridge.export.sampling import load_captured_message, sample_message, write_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--sample-dt", type=float, default=0.01)
    args = parser.parse_args()
    sampled = sample_message(load_captured_message(args.input), args.sample_dt)
    write_csv(args.csv, sampled)
    args.npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.npz, **sampled)
    print(json.dumps({"rows": len(sampled["time"]), "sample_dt": args.sample_dt}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
