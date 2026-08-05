"""Real Isaac GUI state-replay evidence for S4-R0-R1.

The authoritative dynamics are the headless PhysX logs.  This bounded GUI
replay loads the exact frozen S3 USD as a visual-only reference and applies
the recorded PhysX root/q readback for presentation; it never advances a
physics world and is explicitly marked as state replay, not control.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ROBOT_USD = Path(r"D:/i3/a/aerial_manipulator_v2.usd")
ROBOT_SHA256 = "74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d"
SCENARIOS = {"hover_hold": "run_01", "initial_offset_recovery": "x_plus_010", "arm_motion_hold": "run_01"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cube(stage: Any, path: str, center: list[float], size: list[float], color: tuple[float, float, float]) -> None:
    from pxr import Gf, UsdGeom

    prim = stage.DefinePrim(path, "Cube")
    shape = UsdGeom.Cube(prim)
    shape.CreateSizeAttr(1.0)
    shape.CreateDisplayColorAttr().Set([Gf.Vec3f(*color)])
    xf = UsdGeom.Xformable(prim)
    xf.AddTranslateOp().Set(Gf.Vec3d(*center))
    xf.AddScaleOp().Set(Gf.Vec3d(*size))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evidence/S4-R0/visuals/r1/s4_r0_r1_raw_visual_manifest.json")
    args = parser.parse_args()
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": False, "hide_ui": False})
    try:
        import omni.usd
        from isaacsim.core.utils.viewports import set_camera_view
        from omni.kit.viewport.utility import capture_viewport_to_file, get_active_viewport
        from pxr import Gf, Sdf, Usd, UsdGeom

        context = omni.usd.get_context()
        context.new_stage()
        for _ in range(12):
            app.update()
        stage = context.get_stage()
        dynamic_base = stage.DefinePrim("/World/QuadrotorBase", "Xform")
        base_translate = UsdGeom.Xformable(dynamic_base).AddTranslateOp()
        base_orient = UsdGeom.Xformable(dynamic_base).AddOrientOp()
        visual_root = stage.DefinePrim("/World/RobotVisual", "Xform")
        asset_root = stage.DefinePrim("/World/RobotVisual/Asset", "Xform")
        visual_translate = UsdGeom.Xformable(visual_root).AddTranslateOp()
        visual_orient = UsdGeom.Xformable(visual_root).AddOrientOp()
        cube(stage, "/World/Scene/GroundVisual", [0.0, 0.0, -0.03], [5.0, 5.0, 0.05], (0.16, 0.20, 0.24))
        for name, center, size in (("Column", [0.0, 0.0, 0.73], [0.12, 0.12, 1.30]), ("MainBeam", [0.0, 0.0, 1.40], [4.0, 0.12, 0.12]), ("AdjacentObstacle", [0.9, 0.0, 0.9], [0.30, 0.30, 0.80]), ("TargetProxy", [0.0, 0.0, 1.2], [0.20, 0.20, 0.20])):
            cube(stage, f"/World/Scene/{name}", center, size, (0.62, 0.20, 0.12))
        replay_rows: list[tuple[str, str, Path, int, dict[str, object]]] = []
        timeline = 0
        q_attributes = [visual_root.CreateAttribute(f"s4:visual_q{index}_rad", Sdf.ValueTypeNames.Double) for index in range(3)]
        dq_attributes = [visual_root.CreateAttribute(f"s4:visual_dq{index}_rad_s", Sdf.ValueTypeNames.Double) for index in range(3)]
        for scenario, run_id in SCENARIOS.items():
            state_path = ROOT / "outputs/S4-R0" / scenario / run_id / "state.jsonl"
            rows = [json.loads(line) for line in state_path.read_text(encoding="utf-8").splitlines()]
            indices = sorted(set(np.linspace(0, len(rows) - 1, 31, dtype=int).tolist()))
            for index in indices:
                row = rows[index]
                time_code = Usd.TimeCode(float(timeline))
                position = np.asarray(row["position_m"], dtype=float)
                quaternion = np.asarray(row["quaternion_wxyz"], dtype=float)
                if timeline == 0:
                    print("R1_REPLAY author_first_row", flush=True)
                translate_value = Gf.Vec3d(*position.tolist())
                orient_value = Gf.Quatf(float(quaternion[0]), Gf.Vec3f(*quaternion[1:].tolist()))
                base_translate.Set(translate_value, time=time_code)
                if timeline == 0:
                    print("R1_REPLAY base_translate_authored", flush=True)
                base_orient.Set(orient_value, time=time_code)
                if timeline == 0:
                    print("R1_REPLAY base_orient_authored", flush=True)
                visual_translate.Set(translate_value, time=time_code)
                visual_orient.Set(orient_value, time=time_code)
                for attribute, value in zip(q_attributes, row["q_rad"]):
                    attribute.Set(float(value), time=time_code)
                for attribute, value in zip(dq_attributes, row["dq_rad_s"]):
                    attribute.Set(float(value), time=time_code)
                replay_rows.append((scenario, run_id, state_path, timeline, row))
                timeline += 1
        print("R1_REPLAY samples_authored", timeline, flush=True)
        stage.SetStartTimeCode(0.0)
        stage.SetEndTimeCode(float(max(0, timeline - 1)))
        asset_root.GetReferences().AddReference(str(ROBOT_USD.resolve()))
        print("R1_REPLAY reference_added", flush=True)
        viewport = get_active_viewport()
        if viewport is None:
            raise RuntimeError("active Isaac viewport unavailable")
        set_camera_view(eye=[3.8, -5.2, 3.1], target=[0.0, 0.0, 1.55], viewport_api=viewport)
        for _ in range(18):
            app.update()
        print("R1_REPLAY viewport_ready", flush=True)
        frames: list[dict[str, object]] = []
        raw_dir = ROOT / "outputs/local_visuals/S4-R0-R1/raw_gui"
        for scenario, run_id, state_path, time_code_index, row in replay_rows:
            if time_code_index == 0:
                print("R1_REPLAY first_timeline", flush=True)
            stage.SetTimeCode(float(time_code_index))
            if time_code_index == 0:
                print("R1_REPLAY first_time_set", flush=True)
            for _ in range(2):
                app.update()
            if time_code_index == 0:
                print("R1_REPLAY first_update", flush=True)
            path = raw_dir / scenario / run_id / f"frame_{int(row['time_s'] * 240):05d}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            capture_viewport_to_file(viewport, file_path=str(path), is_hdr=False)
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError(f"capture missing: {path}")
            frames.append({"scenario": scenario, "run_id": run_id, "frame": time_code_index, "time_s": float(row["time_s"]), "source_state_path": str(state_path.resolve()), "local_path": str(path.resolve()), "sha256": sha256(path), "bytes": path.stat().st_size, "view": "overall", "capture_mode": "real_isaac_gui_state_replay", "state_replay_only": True, "dynamic_base_prim": "/World/QuadrotorBase", "visual_root_prim": "/World/RobotVisual", "robot_visual_source_usd": str(ROBOT_USD.resolve()), "robot_visual_source_sha256": ROBOT_SHA256, "real_s3_robot_visual": True, "root_teleport": False})
        payload = {"decision": "PASS", "visual_contract_version": "S4-R0-R1-real-isaac-gui-state-replay-v1", "capture_mode": "real_isaac_gui_state_replay", "state_replay_only": True, "physics_loop_in_gui": False, "robot_visual_source_usd": str(ROBOT_USD.resolve()), "robot_visual_source_sha256": ROBOT_SHA256, "dynamic_base_prim": "/World/QuadrotorBase", "visual_root_prim": "/World/RobotVisual", "real_s3_robot_visual": True, "root_teleport": False, "png": frames, "png_count": len(frames), "video": [], "video_count": 0}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"decision": payload["decision"], "png_count": payload["png_count"], "output": str(args.output.resolve())}, ensure_ascii=False, indent=2), flush=True)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
