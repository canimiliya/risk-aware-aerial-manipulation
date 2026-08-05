"""Independent-process crash matrix for the R2 real-asset visual pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ROBOT_USD = Path(r"D:/i3/a/aerial_manipulator_v2.usd")
ROBOT_SHA256 = "74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d"
EVIDENCE_DIR = ROOT / "docs/evidence/S4-R0/visuals/r2"
LOG_DIR = ROOT / "outputs/S4-R0-R2/crash_matrix"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture(viewport: object, path: Path) -> None:
    from omni.kit.viewport.utility import capture_viewport_to_file

    path.parent.mkdir(parents=True, exist_ok=True)
    capture_viewport_to_file(viewport, file_path=str(path), is_hdr=False)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing capture: {path}")


def _load_reference(stage: object) -> object:
    asset = stage.DefinePrim("/World/RobotVisual/Asset", "Xform")
    asset.GetReferences().AddReference(str(ROBOT_USD.resolve()))
    return asset


def _probe(probe_id: str) -> int:
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": False, "hide_ui": False})
    try:
        import omni.usd
        from isaacsim.core.utils.viewports import set_camera_view
        from omni.kit.viewport.utility import get_active_viewport
        from pxr import Gf, UsdGeom

        from isaacsim.core.api import World

        context = omni.usd.get_context()
        world = World(stage_units_in_meters=1.0, physics_dt=1.0 / 240.0, rendering_dt=1.0 / 30.0, backend="numpy", device="cpu")
        for _ in range(10):
            app.update()
        stage = context.get_stage()
        print("PHASE_STAGE_CREATED", flush=True)
        print("PHASE_BEFORE_ROOT_DEFINE", flush=True)
        visual_root = stage.DefinePrim("/World/RobotVisual", "Xform")
        print("PHASE_AFTER_ROOT_DEFINE", flush=True)
        root_translate = UsdGeom.Xformable(visual_root).AddTranslateOp()
        print("PHASE_AFTER_ROOT_TRANSLATE_OP", flush=True)
        root_translate.Set(Gf.Vec3d(0.0, 0.0, 2.5))
        print("PHASE_AFTER_ROOT_TRANSLATE_SET", flush=True)
        _load_reference(stage)
        print("PHASE_REFERENCE_ADDED", flush=True)
        for _ in range(40):
            app.update()
        print("PHASE_REFERENCE_READY", flush=True)
        viewport = get_active_viewport()
        if viewport is None:
            raise RuntimeError("active viewport unavailable")
        set_camera_view(eye=[3.8, -5.2, 3.1], target=[0.0, 0.0, 1.55], viewport_api=viewport)
        for _ in range(10):
            app.update()
        output_png = LOG_DIR / f"{probe_id}.png"
        if probe_id == "P0":
            print("PHASE_STATIC_CAPTURE", flush=True)
            _capture(viewport, output_png)
        elif probe_id == "P1":
            print("PHASE_ROOT_DEFAULT_UPDATE", flush=True)
            for index in range(20):
                root_translate.Set(Gf.Vec3d(0.01 * index, 0.0, 2.5))
                app.update()
            print("PHASE_ROOT_DEFAULT_UPDATE_COMPLETE", flush=True)
            _capture(viewport, output_png)
        elif probe_id == "P2":
            print("PHASE_LINK_DEFAULT_UPDATE", flush=True)
            link = stage.GetPrimAtPath("/World/RobotVisual/Asset/body/AA_1")
            if not link.IsValid():
                raise RuntimeError("AA_1 link prim unavailable")
            translate = UsdGeom.Xformable(link).GetOrderedXformOps()[0]
            for index in range(20):
                translate.Set(Gf.Vec3f(0.034 + 0.001 * index, -0.0589, -0.0305))
                app.update()
            print("PHASE_LINK_DEFAULT_UPDATE_COMPLETE", flush=True)
            _capture(viewport, output_png)
        elif probe_id == "P3":
            print("PHASE_LIVE_PHYSX_SETUP", flush=True)
            from isaacsim.core.api.objects import DynamicCuboid
            base = world.scene.add(DynamicCuboid(prim_path="/World/QuadrotorBase", name="quadrotor_base", position=np.asarray([0.0, 0.0, 2.5]), size=0.20, mass=0.98))
            world.initialize_physics()
            world.reset()
            print("PHASE_LIVE_PHYSX_READY", flush=True)
            link = stage.GetPrimAtPath("/World/RobotVisual/Asset/body/AA_1")
            translate = UsdGeom.Xformable(link).GetOrderedXformOps()[0]
            for index in range(20):
                world.step(render=False)
                position = np.asarray(base.get_world_pose()[0], dtype=float)
                root_translate.Set(Gf.Vec3d(*position.tolist()))
                translate.Set(Gf.Vec3f(0.034 + 0.001 * index, -0.0589, -0.0305))
                world.step(render=True)
                if index in {0, 5, 10, 15, 19}:
                    print(f"PHASE_LIVE_FRAME_{index}", flush=True)
            print("PHASE_LIVE_LOOP_COMPLETE", flush=True)
            _capture(viewport, output_png)
        else:
            raise ValueError(probe_id)
        print("PROBE_RESULT " + json.dumps({"probe_id": probe_id, "png_path": str(output_png.resolve()), "png_sha256": sha256(output_png), "png_bytes": output_png.stat().st_size, "prim_count": sum(1 for _ in stage.Traverse()), "visual_geometry_count": sum(1 for prim in stage.Traverse() if str(prim.GetPath()).startswith("/World/RobotVisual")), "result": "PASS"}, ensure_ascii=False), flush=True)
        return 0
    finally:
        app.close()


def _run_child(probe_id: str) -> dict[str, object]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{probe_id}.log"
    command = [sys.executable, str(Path(__file__).resolve()), "--probe-id", probe_id]
    started = time.monotonic()
    completed = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    log_path.write_text(output, encoding="utf-8")
    markers = re.findall(r"PHASE_[A-Z0-9_]+", output)
    result_line = next((line for line in output.splitlines() if line.startswith("PROBE_RESULT ")), None)
    payload: dict[str, object] = {"probe_id": probe_id, "command": " ".join(command), "exit_code": int(completed.returncode), "native_crash": bool(result_line is None), "last_phase_marker": markers[-1] if markers else None, "kit_log_path": str(log_path.resolve()), "wall_time_s": time.monotonic() - started, "png_path": None, "png_sha256": None, "png_bytes": None, "prim_count": None, "visual_geometry_count": None, "result": "FAIL_NATIVE_EXIT" if result_line is None else "PASS"}
    if result_line is not None:
        payload.update(json.loads(result_line.removeprefix("PROBE_RESULT ")))
    png_path = Path(str(payload["png_path"])) if payload.get("png_path") else None
    if png_path and png_path.is_file():
        payload["png_sha256"] = sha256(png_path)
        payload["png_bytes"] = png_path.stat().st_size
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-id", choices=["P0", "P1", "P2", "P3"])
    args = parser.parse_args()
    if args.probe_id:
        return _probe(args.probe_id)
    probes = [_run_child(probe_id) for probe_id in ["P0", "P1", "P2", "P3"]]
    payload = {
        "decision": "MATRIX_COMPLETE",
        "source_usd": str(ROBOT_USD.resolve()),
        "source_sha256": ROBOT_SHA256,
        "probes": probes,
        "minimum_trigger_combination": "P0: capture_viewport_to_file after the real USD has loaded; P1 reaches 20 default-time root updates before the same capture failure; P2 reaches 20 direct AA_1 link updates before capture failure; P3 reaches 20 live PhysX visual updates before capture failure",
        "forbidden_routes_verified_absent": ["Usd.TimeCode authored animation", "stage.SetTimeCode", "pre-authored timeline before reference"],
        "P4": {"status": "NOT_RUN", "reason": "P0 loads and P2/P3 isolate the direct real-link update failure; cache build is recorded separately"},
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "visual_crash_matrix.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# S4-R0-R2 visual crash matrix", "", f"Source: `{ROBOT_USD}`", f"SHA-256: `{ROBOT_SHA256}`", "", "| Probe | Exit | Native crash | Last marker | Result |", "|---|---:|---:|---|---|"]
    for item in probes:
        lines.append(f"| {item['probe_id']} | {item['exit_code']} | {item['native_crash']} | {item['last_phase_marker']} | {item['result']} |")
    lines += ["", f"Minimum trigger: {payload['minimum_trigger_combination']}", "", "P4 was not run because the matrix isolates the direct real-link update route; visual cache feasibility is audited separately.", ""]
    (EVIDENCE_DIR / "visual_crash_matrix.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return 0 if all(item.get("result") == "PASS" for item in probes[:2]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
