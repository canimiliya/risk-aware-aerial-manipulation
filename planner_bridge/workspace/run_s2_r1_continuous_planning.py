from __future__ import annotations

import argparse
from pathlib import Path

from .continuous_full_body_planner import plan_from_p0_p6


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples-per-segment", type=int, default=101)
    parser.add_argument("--variant", default="nominal")
    args = parser.parse_args()
    result = plan_from_p0_p6(args.scene, args.output, args.samples_per_segment, args.variant)
    print({"sample_count": result["sample_count"], "metrics": result["metrics"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
