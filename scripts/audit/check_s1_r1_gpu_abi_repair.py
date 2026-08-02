#!/usr/bin/env python3
"""Small read-only audit for the S1-R1 GPU39 ABI evidence graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph", type=Path)
    args = parser.parse_args()
    data = json.loads(args.graph.read_text(encoding="utf-8"))
    direct = data["direct_vs_transitive"]["se3_node_direct_needed"]
    planner = data["direct_vs_transitive"]["libse3_planner_direct_needed"]
    checks = {
        "se3_node_direct_python39": "libpython3.9.so.1.0" in direct,
        "se3_node_direct_no_python38": "libpython3.8.so.1.0" not in direct,
        "libse3_planner_still_python38": "libpython3.8.so.1.0" in planner,
    }
    for name, passed in checks.items():
        print(f"{name}={'PASS' if passed else 'FAIL'}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
