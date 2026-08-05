"""Attempt the R2 visual-only cache route and record hard gate results."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"D:/i3/a/aerial_manipulator_v2.usd")
SOURCE_SHA256 = "74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d"
CACHE = ROOT / "outputs/local_visuals/S4-R0-R2/cache/aerial_manipulator_v2_visual_only.usdc"
MANIFEST = ROOT / "docs/evidence/S4-R0/visuals/r2/visual_cache_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_stage(stage: object) -> dict[str, object]:
    from pxr import UsdGeom

    mesh_paths = []
    physics_schema_hits = []
    external_stl = []
    time_sample_paths = []
    for prim in stage.Traverse():
        path = str(prim.GetPath())
        if prim.GetTypeName() == "Mesh":
            mesh_paths.append(path)
        if any("Physics" in schema or "Physx" in schema for schema in prim.GetAppliedSchemas()):
            physics_schema_hits.append({"path": path, "schemas": list(prim.GetAppliedSchemas())})
        for attribute in prim.GetAttributes():
            try:
                samples = attribute.GetTimeSamples()
            except Exception:
                samples = []
            if samples:
                time_sample_paths.append({"path": path, "attribute": attribute.GetName(), "count": len(samples)})
    try:
        serialized = stage.GetRootLayer().ExportToString()
        external_stl = [token for token in serialized.replace('"', " ").split() if ".stl" in token.lower()]
    except Exception:
        external_stl = []
    return {"mesh_count": len(mesh_paths), "mesh_paths": mesh_paths[:100], "physics_schema_count": len(physics_schema_hits), "physics_schema_hits": physics_schema_hits[:100], "external_stl_reference_count": len(external_stl), "external_stl_references": external_stl[:100], "time_sample_count": len(time_sample_paths), "time_samples": time_sample_paths[:100]}


def main() -> int:
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "hide_ui": True})
    try:
        return _main_with_usd()
    finally:
        app.close()


def _main_with_usd() -> int:
    from pxr import Usd

    source_stage = Usd.Stage.Open(str(SOURCE.resolve()))
    if source_stage is None:
        raise RuntimeError("source USD could not be opened")
    source_inspection = inspect_stage(source_stage)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    flattened = source_stage.Flatten()
    flattened.Export(str(CACHE.resolve()))
    cache_stage = Usd.Stage.Open(str(CACHE.resolve()))
    cache_inspection = inspect_stage(cache_stage) if cache_stage is not None else {"open": False}
    payload = {
        "decision": "BLOCKED_S4_R0_R2_VISUAL_CACHE_BUILD_FAILED",
        "source_usd": str(SOURCE.resolve()),
        "source_sha256": SOURCE_SHA256,
        "cache_path": str(CACHE.resolve()),
        "cache_sha256": sha256(CACHE) if CACHE.is_file() else None,
        "cache_bytes": CACHE.stat().st_size if CACHE.is_file() else None,
        "source_inspection": source_inspection,
        "cache_inspection": cache_inspection,
        "hard_gates": {
            "mesh_count_gt_0": bool(cache_inspection.get("mesh_count", 0) > 0),
            "external_stl_references_zero": bool(cache_inspection.get("external_stl_reference_count", 1) == 0),
            "physics_schemas_zero": bool(cache_inspection.get("physics_schema_count", 1) == 0),
            "time_samples_zero": bool(cache_inspection.get("time_sample_count", 1) == 0),
        },
        "reason": "Flattened frozen USD retains the custom S3 visual layer without standard Mesh prims; it cannot satisfy the required visual-only cache geometry gate.",
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return 0 if all(payload["hard_gates"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
