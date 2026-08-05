"""Materialize the official AM-Planner Delta xacro as a local import input.

The source xacro and meshes remain read-only. This produces a temporary URDF
under the external S3 asset root for Isaac Sim's official URDF importer.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


EXPR_RE = re.compile(r"\$\{([^{}]+)\}")


def _eval_expr(match: re.Match[str]) -> str:
    expression = match.group(1).replace("scale", "1.0")
    value = eval(expression, {"__builtins__": {}}, {})  # noqa: S307 - source expressions are numeric only
    return f"{float(value):.17g}"


def materialize(source: Path, output: Path, mesh_root: Path) -> dict[str, object]:
    text = source.read_text(encoding="utf-8")
    text = re.sub(r"\s*<xacro:property[^>]*/>", "", text)
    text = text.replace(' xmlns:xacro="http://www.ros.org/wiki/xacro"', "")
    # Correct the source's scientific-notation formatting typo before numeric expansion.
    text = text.replace("1${.57437354819656E-10 * scale}", "${1.57437354819656E-10 * scale}")
    text = text.replace("$(arg scale)", "1.0")
    text = EXPR_RE.sub(_eval_expr, text)
    mesh_uri = mesh_root.resolve().as_posix()
    # Isaac Sim's Windows URDF importer accepts an absolute forward-slash path
    # here; the file:// URI form is rejected by the Kit asset resolver.
    text = text.replace("package://delta_display/meshes/", f"{mesh_uri}/")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return {
        "source_xacro": str(source.resolve()),
        "materialized_urdf": str(output.resolve()),
        "mesh_root": str(mesh_root.resolve()),
        "scale": 1.0,
        "source_is_read_only_input": True,
        "active_joints": ["m1_1", "m2_1", "m3_1"],
        "passive_trailing_joints": ["m1_2", "m1_3", "m2_2", "m2_3", "m3_2", "m3_3"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-root", type=Path, required=True)
    args = parser.parse_args()
    print(materialize(args.source, args.output, args.mesh_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
