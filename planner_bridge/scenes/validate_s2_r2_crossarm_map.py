from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from generate_s2_r2_crossarm_map import VARIANTS, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("docs/evidence/S2-R2/maps"))
    args = parser.parse_args()
    for variant in sorted(VARIANTS):
        expected = manifest(variant)
        actual = json.loads((args.output_dir / f"{variant}.json").read_text(encoding="utf-8"))
        assert actual == expected, variant
        assert actual["frame_id"] == "world"
        assert actual["resolution_m"] == 0.02
        assert actual["point_count"] >= 0
        if actual["aabb_m"] is not None:
            assert all(math.isfinite(float(v)) for side in ("min", "max") for v in actual["aabb_m"][side])
    print(json.dumps({"variants": sorted(VARIANTS), "errors": [], "warnings": []}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
