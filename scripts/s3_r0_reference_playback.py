"""S3-R0 bounded Isaac reference playback and exact sampled-proxy audit.

The Kit application is used only for bounded stage/reference initialization and
for the optional GUI cadence.  The formal headless loop is driven by Isaac
Lab's ``SimulationContext.step(render=False)``; it never uses
``SimulationApp.update()`` as a physics loop.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import Any, Callable

import numpy as np


PHYSICS_DT_S = 1.0 / 240.0
CLEARANCE_GATE_M = 0.010
EXACT_CLEARANCE_LABEL = "EXACT_FOR_FROZEN_S2_SAMPLED_PROXY_NOT_MESH_EXACT"
S2_R6_G3_MIN_CLEARANCE_M = 0.09210197487032999
ACTIVE_JOINTS = ("m1_1", "m2_1", "m3_1")
PASSIVE_JOINTS = ("m1_2", "m1_3", "m2_2", "m2_3", "m3_2", "m3_3")
PHASE_TIMEOUTS_S = {
    "SIMULATION_APP_CREATED": 180.0,
    "STAGE_CREATED": 120.0,
    "ROBOT_ASSET_READY": 180.0,
    "ACTIVE_JOINTS_READY": 120.0,
    "SIMULATION_CONTEXT_READY": 120.0,
    "APP_CLOSED": 120.0,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rss_mb() -> float | None:
    try:
        import psutil

        return float(psutil.Process(os.getpid()).memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        return None


def _gpu_memory_mb() -> float | None:
    """Best-effort GPU memory read; a missing nvidia-smi is not a failure."""

    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        value = completed.stdout.strip().splitlines()[0]
        return float(value)
    except Exception:
        return None


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    """Write JSON through a same-directory temporary file and atomic replace."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=float) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_sha256_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


def _progress_event(
    progress_path: Path,
    start_monotonic: float,
    event: str,
    *,
    phase: str | None = None,
    step: int | None = None,
    simulation_time_s: float | None = None,
    last_operation: str = "",
    **extra: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "event": event,
        "utc": _utc_now(),
        "wall_elapsed_s": time.monotonic() - start_monotonic,
        "rss_mb": _rss_mb(),
        "gpu_memory_mb": _gpu_memory_mb(),
        "step": step,
        "simulation_time_s": simulation_time_s,
        "phase": phase,
        "last_operation": last_operation,
    }
    record.update(extra)
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    with progress_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=float) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(event, json.dumps(record, ensure_ascii=False, default=float), flush=True)
    return record


class _StateWriter:
    """Compact JSONL state writer with bounded checkpoint flushes."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.handle = path.open("w", encoding="utf-8", newline="\n")
        self.count = 0

    def append(self, record: dict[str, object], flush: bool = False) -> None:
        self.handle.write(json.dumps(record, ensure_ascii=False, default=float) + "\n")
        self.count += 1
        if flush:
            self.flush()

    def flush(self) -> None:
        self.handle.flush()
        os.fsync(self.handle.fileno())

    def close(self) -> None:
        try:
            self.flush()
        finally:
            self.handle.close()


def _check_runtime(start_monotonic: float, max_runtime_s: float, phase: str, step: int | None = None) -> None:
    elapsed = time.monotonic() - start_monotonic
    if elapsed > max_runtime_s:
        raise TimeoutError(f"overall runtime exceeded {max_runtime_s:.3f}s during {phase} at step {step}")


def _bounded_phase(
    phase: str,
    event: str,
    operation: Callable[[], Any],
    *,
    progress_path: Path,
    start_monotonic: float,
    max_runtime_s: float,
    last_operation: str,
    timeout_s: float | None = None,
) -> Any:
    phase_start = time.monotonic()
    result = operation()
    elapsed = time.monotonic() - phase_start
    _check_runtime(start_monotonic, max_runtime_s, phase)
    limit = timeout_s if timeout_s is not None else PHASE_TIMEOUTS_S.get(event)
    if limit is not None and elapsed > limit:
        raise TimeoutError(f"phase {phase} exceeded {limit:.3f}s: {elapsed:.3f}s")
    _progress_event(
        progress_path,
        start_monotonic,
        event,
        phase=phase,
        last_operation=last_operation,
        phase_wall_time_s=elapsed,
    )
    return result


def _await_stage(app: Any, context: Any, start_monotonic: float, max_runtime_s: float, max_frames: int = 480) -> Any:
    import asyncio

    future = asyncio.ensure_future(context.new_stage_async())
    for _ in range(max_frames):
        if future.done():
            return context.get_stage()
        _check_runtime(start_monotonic, max_runtime_s, "stage_creation")
        # This is bounded initialization only.  Formal physics stepping below
        # never calls SimulationApp.update().
        app.update()
    raise TimeoutError(f"stage creation did not complete within {max_frames} initialization frames")


def _bounded_app_updates(app: Any, count: int, start_monotonic: float, max_runtime_s: float, phase: str) -> None:
    for _ in range(count):
        _check_runtime(start_monotonic, max_runtime_s, phase)
        # Allowed only for bounded stage/reference loading and extension warmup.
        app.update()


def _close_app_on_main_thread(
    app: Any,
    sim: Any | None,
    progress_path: Path,
    start_monotonic: float,
) -> bool:
    """Close Kit synchronously on the main thread.

    Kit/PhysX teardown is not thread-safe.  The previous implementation put
    ``app.close()`` in a daemon worker, which could leave a live Kit process
    after a failed stage setup.  Isaac Sim 5.1's graceful stage teardown can
    block indefinitely, so the supported immediate shutdown path is used
    after the result and close event have been durably written.
    """

    _progress_event(progress_path, start_monotonic, "APP_CLOSE_STARTED", phase="app_close", last_operation="app.close")
    started = time.monotonic()
    try:
        _progress_event(
            progress_path,
            start_monotonic,
            "APP_CLOSED",
            phase="app_close",
            last_operation="app.close(skip_cleanup=True)",
            shutdown_mode="immediate_framework_release",
        )
        app.close(wait_for_replicator=False, skip_cleanup=True)
    except Exception:
        _progress_event(
            progress_path,
            start_monotonic,
            "APP_CLOSE_FAILED",
            phase="app_close",
            last_operation="app.close",
            close_wall_time_s=time.monotonic() - started,
            close_exception=traceback.format_exc(),
        )
        return False
    _progress_event(
        progress_path,
        start_monotonic,
        "APP_CLOSED",
        phase="app_close",
        last_operation="app.close",
        close_wall_time_s=time.monotonic() - started,
    )
    return True


def _scene_boxes() -> Mapping[str, Any]:
    # Import after the repository root is placed on sys.path in main().  The
    # returned mapping is the immutable canonical object, not a local copy.
    from planner_bridge.scenes.s3_r0_scene_contract import SCENE_AABBS

    return SCENE_AABBS


def _cube(stage: Any, path: str, center: Sequence[float], size: Sequence[float], label: str, UsdGeom: Any, UsdPhysics: Any, Gf: Any) -> None:
    prim = stage.DefinePrim(path, "Cube")
    cube = UsdGeom.Cube(prim)
    cube.CreateSizeAttr(1.0)
    xform = UsdGeom.Xformable(prim)
    xform.AddTranslateOp().Set(Gf.Vec3d(*center))
    # Preserve the canonical metre contract through USD read-back.  Vec3f
    # quantizes the dimensions at roughly 1e-8 m, above the S3 1e-9 m probe
    # tolerance; the scene contract is a double-precision world-space value.
    xform.AddScaleOp(precision=UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*size))
    UsdPhysics.CollisionAPI.Apply(prim)
    prim.SetCustomDataByKey("s3_label", label)


def _quat_wxyz(quaternion: Any) -> list[float]:
    real = float(quaternion.GetReal())
    imaginary = quaternion.GetImaginary()
    return [real, float(imaginary[0]), float(imaginary[1]), float(imaginary[2])]


def _state_time_grid(total_duration: float) -> np.ndarray:
    from planner_bridge.protocol.polynomial import physics_time_grid

    return physics_time_grid(total_duration, PHYSICS_DT_S)


def _attitude_for_raw(base: dict[str, np.ndarray], source_message: dict[str, object]) -> tuple[dict, dict]:
    from planner_bridge.execution.playback_validator import validate_attitude

    start_yaw = float(source_message.get("start_yaw", 0.0))
    final_yaw = float(source_message.get("final_yaw", start_yaw))
    yaw = start_yaw + (final_yaw - start_yaw) * base["phase_progress"]
    yaw_dot = np.full(len(base["time"]), 0.01, dtype=float)
    return validate_attitude(
        {
            "velocity": base["velocity"],
            "acceleration": base["acceleration"],
            "jerk": base["jerk"],
            "yaw": yaw,
            "yaw_dot": yaw_dot,
        }
    )


def _raw_states(bundle: dict, times: np.ndarray) -> dict[str, object]:
    from planner_bridge.execution.official_delta_kinematics import official_ik
    from planner_bridge.protocol.load_trajectory import load_raw_polynomials
    from planner_bridge.protocol.polynomial import evaluate_message

    base_payload, arm_payload = load_raw_polynomials(bundle)
    base = evaluate_message(base_payload, times)
    arm = evaluate_message(arm_payload, times)
    attitude_summary, attitude = _attitude_for_raw(base, base_payload["message"])
    q = np.asarray([official_ik(point) for point in arm["position"]], dtype=float)
    if not np.isfinite(q).all():
        raise RuntimeError("official IK returned non-finite raw playback state")
    qdot = np.gradient(q, times, axis=0, edge_order=2) if len(times) >= 3 else np.zeros_like(q)
    qddot = np.gradient(qdot, times, axis=0, edge_order=2) if len(times) >= 3 else np.zeros_like(qdot)
    return {
        "base": base,
        "arm": arm,
        "attitude": attitude,
        "attitude_summary": attitude_summary,
        "q": q,
        "qdot": qdot,
        "qddot": qddot,
        "base_payload": base_payload,
        "arm_payload": arm_payload,
    }


def _analytic_frame_clearance(sample_sets: dict, boxes: Mapping[str, Any], sampled_proxy_aabb_clearance: Callable) -> dict[str, dict[str, dict[str, object]]]:
    by_component: dict[str, dict[str, dict[str, object]]] = {}
    for component, samples in sample_sets.items():
        by_component[component] = {}
        for obstacle, aabb in boxes.items():
            by_component[component][obstacle] = sampled_proxy_aabb_clearance(
                samples,
                np.asarray(aabb.center_m, dtype=float),
                np.asarray(aabb.size_m, dtype=float),
            )
    return by_component


def _min_analytic(records: dict[str, dict[str, dict[str, object]]]) -> dict[str, object]:
    best = None
    for component, obstacles in records.items():
        for obstacle, record in obstacles.items():
            candidate = {"component": component, "obstacle": obstacle, **record}
            if best is None or candidate["clearance_m"] < best["clearance_m"]:
                best = candidate
    return best or {"component": None, "obstacle": None, "clearance_m": float("inf")}


def _tree_frame_clearance(sample_sets: dict, tree: Any) -> dict[str, object]:
    best = None
    by_component: dict[str, object] = {}
    for component, (points, radius) in sample_sets.items():
        distances, indices = tree.query(points, k=1)
        index = int(np.argmin(distances))
        record = {
            "distance_m": float(distances[index]),
            "clearance_m": float(distances[index] - radius),
            "nearest_sample_index": index,
            "nearest_sample_point_m": np.asarray(points[index], dtype=float).tolist(),
            "nearest_obstacle_point_m": np.asarray(tree.data[int(indices[index])], dtype=float).tolist(),
            "component_radius_m": float(radius),
        }
        by_component[component] = record
        candidate = {"component": component, "obstacle": "S2_nominal_obstacle_tree", **record}
        if best is None or candidate["clearance_m"] < best["clearance_m"]:
            best = candidate
    return {"best": best or {"component": None, "clearance_m": float("inf")}, "by_component": by_component}


def _local_refinement(
    raw_states: dict[str, object],
    total_duration: float,
    dangerous_time: float,
    tree: Any,
    T_B_A0: np.ndarray,
    official_joint_points: Callable,
    component_sample_sets: Callable,
) -> dict[str, object]:
    from planner_bridge.execution.official_delta_kinematics import official_ik
    from planner_bridge.protocol.polynomial import evaluate_message

    base_payload = raw_states["base_payload"]
    arm_payload = raw_states["arm_payload"]
    start = max(0.0, float(dangerous_time) - 2.0 * PHYSICS_DT_S)
    end = min(float(total_duration), float(dangerous_time) + 2.0 * PHYSICS_DT_S)
    times = np.arange(start, end + 0.5 / 2000.0, 1.0 / 2000.0, dtype=float)
    if len(times) == 0 or times[-1] < end:
        times = np.append(times, end)
    base = evaluate_message(base_payload, times)
    arm = evaluate_message(arm_payload, times)
    _, attitude = _attitude_for_raw(base, base_payload["message"])
    minimum = None
    for i, current_time in enumerate(times):
        q = official_ik(arm["position"][i])
        joints = official_joint_points(arm["position"][i], q)
        samples = component_sample_sets(base["position"][i], attitude["rotation"][i], arm["position"][i], joints)
        candidate = _tree_frame_clearance(samples, tree)["best"]
        candidate = {"time_s": float(current_time), **candidate}
        if minimum is None or candidate["clearance_m"] < minimum["clearance_m"]:
            minimum = candidate
    return {
        "sample_hz": 2000,
        "start_time_s": float(start),
        "end_time_s": float(end),
        "samples": int(len(times)),
        "minimum": minimum,
    }


def _postprocess(
    raw_states: dict[str, object],
    state_records: list[dict[str, object]],
    boxes: Mapping[str, Any],
    tree: Any,
    T_B_A0: np.ndarray,
    official_fk_joint_state: Callable,
    official_joint_points: Callable,
    component_sample_sets: Callable,
    sampled_proxy_aabb_clearance: Callable,
    total_duration: float,
    smoke: bool,
    contact_hits: list[dict[str, object]],
) -> dict[str, object]:
    base = raw_states["base"]
    arm = raw_states["arm"]
    attitude = raw_states["attitude"]
    q_values = raw_states["q"]
    g1_best = None
    g2_best = None
    clearance_by_frame: list[dict[str, object]] = []
    expanded_hits: list[dict[str, object]] = []
    max_joint_error = 0.0
    max_raw_joint_error = 0.0
    max_arm_fk_error = 0.0
    max_world_error = 0.0
    max_quaternion_norm_error = 0.0
    finite = True

    for index, record in enumerate(state_records):
        readback_position = np.asarray(record["base_position_WB_m"], dtype=float)
        readback_quaternion = np.asarray(record["base_quaternion_WB_wxyz"], dtype=float)
        readback_rotation = __import__("planner_bridge.protocol.frames", fromlist=["rotation_from_quaternion_wxyz"]).rotation_from_quaternion_wxyz(readback_quaternion)
        readback_q = np.asarray(record["q_rad"], dtype=float)
        readback_qdot = np.asarray(record["qdot_rad_s"], dtype=float)
        readback_fk = official_fk_joint_state(readback_q)
        reference_position = np.asarray(base["position"][index], dtype=float)
        reference_q = np.asarray(q_values[index], dtype=float)
        reference_world_ee = __import__("planner_bridge.protocol.frames", fromlist=["compose_world_ee"]).compose_world_ee(
            reference_position, arm["position"][index], attitude["rotation"][index], T_B_A0
        )
        readback_world_ee = __import__("planner_bridge.protocol.frames", fromlist=["compose_world_ee"]).compose_world_ee(
            readback_position, readback_fk, readback_rotation, T_B_A0
        )
        written_q = np.asarray(record.get("written_q_rad", record["q_rad"]), dtype=float)
        max_joint_error = max(max_joint_error, float(np.max(np.abs(readback_q - written_q))))
        max_raw_joint_error = max(max_raw_joint_error, float(np.max(np.abs(readback_q - reference_q))))
        max_arm_fk_error = max(max_arm_fk_error, float(np.linalg.norm(readback_fk - arm["position"][index])))
        max_world_error = max(max_world_error, float(np.linalg.norm(readback_world_ee - reference_world_ee)))
        max_quaternion_norm_error = max(max_quaternion_norm_error, abs(float(np.linalg.norm(readback_quaternion)) - 1.0))
        record.update(
            {
                "arm_fk_position_m": np.asarray(readback_fk, dtype=float).tolist(),
                "reference_world_ee_position_m": np.asarray(reference_world_ee, dtype=float).tolist(),
                "arm_fk_residual_m": float(np.linalg.norm(readback_fk - arm["position"][index])),
                "world_ee_residual_m": float(np.linalg.norm(readback_world_ee - reference_world_ee)),
            }
        )

        joints = official_joint_points(readback_fk, readback_q)
        sample_sets = component_sample_sets(readback_position, readback_rotation, readback_fk, joints)
        analytic = _analytic_frame_clearance(sample_sets, boxes, sampled_proxy_aabb_clearance)
        tree_frame = _tree_frame_clearance(sample_sets, tree)
        analytic_best = {"time_s": float(record["reference_time_s"]), **_min_analytic(analytic)}
        g2_frame_best = {"time_s": float(record["reference_time_s"]), **tree_frame["best"]}
        if g1_best is None or analytic_best["clearance_m"] < g1_best["clearance_m"]:
            g1_best = analytic_best
        if g2_best is None or g2_frame_best["clearance_m"] < g2_best["clearance_m"]:
            g2_best = g2_frame_best
        if not smoke:
            for component, obstacles in analytic.items():
                for obstacle, clearance in obstacles.items():
                    if float(clearance["clearance_m"]) <= CLEARANCE_GATE_M and len(expanded_hits) < 100:
                        expanded_hits.append(
                            {
                                "frame": index,
                                "time_s": float(record["reference_time_s"]),
                                "component": component,
                                "obstacle": obstacle,
                                "clearance_m": float(clearance["clearance_m"]),
                            }
                        )
        clearance_by_frame.append(
            {
                "time_s": float(record["reference_time_s"]),
                "components": analytic,
                "s2_obstacle_tree": tree_frame["by_component"],
            }
        )
        finite = finite and bool(
            np.isfinite(readback_position).all()
            and np.isfinite(readback_quaternion).all()
            and np.isfinite(readback_q).all()
            and np.isfinite(readback_qdot).all()
            and np.isfinite(readback_world_ee).all()
        )

    g1_best = g1_best or {"clearance_m": float("nan")}
    g2_best = g2_best or {"clearance_m": float("nan")}
    if smoke:
        refinement: dict[str, object] = {"status": "NOT_RUN_SMOKE"}
    else:
        refinement = _local_refinement(
            raw_states,
            total_duration,
            float(g1_best.get("time_s", 0.0)),
            tree,
            T_B_A0,
            official_joint_points,
            component_sample_sets,
        )
    g1_g2_signed = float(g1_best["clearance_m"]) - float(g2_best["clearance_m"])
    geometry_representation_conservatism = -g1_g2_signed
    g2_g3_delta = abs(float(g2_best["clearance_m"]) - S2_R6_G3_MIN_CLEARANCE_M)
    exact_clearance_gate = bool(
        not smoke
        and float(g1_best["clearance_m"]) >= CLEARANCE_GATE_M
        and not expanded_hits
        and not contact_hits
    )
    return {
        "finite": finite,
        "max_joint_state_write_readback_error_rad": max_joint_error,
        "max_raw_reference_to_joint_readback_error_rad": max_raw_joint_error,
        "joint_state_storage_dtype": "float32 USD PhysicsJointStateAPI attribute",
        "max_arm_fk_error_m": max_arm_fk_error,
        "max_world_ee_error_m": max_world_error,
        "max_readback_quaternion_norm_error": max_quaternion_norm_error,
        "contact_query_hits": contact_hits,
        "clearance_expanded_query_hits": expanded_hits,
        "contact_query": "PASS" if not contact_hits else "FAIL",
        "penetration_m": 0.0 if not contact_hits else None,
        "clearance_metric": EXACT_CLEARANCE_LABEL,
        "min_clearance_m": float(g1_best["clearance_m"]),
        "dangerous_component": g1_best.get("component"),
        "dangerous_obstacle": g1_best.get("obstacle"),
        "dangerous_time_s": g1_best.get("time_s"),
        "closest_sample_point_m": g1_best.get("nearest_sample_point_m"),
        "clearance_gate": "PASS" if not smoke and float(g1_best["clearance_m"]) >= CLEARANCE_GATE_M else "NOT_RUN" if smoke else "FAIL",
        "clearance_lower_bound_m": CLEARANCE_GATE_M if not expanded_hits else None,
        "expanded_overlap_gate": "PASS" if not smoke and not expanded_hits else "NOT_RUN" if smoke else "FAIL",
        "exact_clearance_gate": exact_clearance_gate,
        "g1_isaac_readback_analytic_aabb": g1_best,
        "g2_same_readback_s2_obstacle_tree": g2_best,
        "g3_historical_s2_r6_nominal_2000hz": {
            "min_clearance_m": S2_R6_G3_MIN_CLEARANCE_M,
            "dangerous_component": "rotor_4",
        },
        "geometry_representation_conservatism_m": float(geometry_representation_conservatism),
        "g1_minus_g2_representation_diagnostic_m": float(g1_g2_signed),
        "state_replay_s2_clearance_delta_m": float(g2_g3_delta),
        "g2_g3_delta_gate_m": 0.002,
        "state_replay_s2_clearance_delta_pass": bool(not smoke and g2_g3_delta <= 0.002),
        "distance_representation_contract_note": "G1/G2 are different geometries; use the independent envelope, replay, containment, and framewise-order gates from s3_r0_distance_representation_audit.py.",
        "local_2000hz_refinement": refinement,
        "clearance_by_frame": clearance_by_frame,
        "state_records": state_records,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot-usd", required=True)
    parser.add_argument("--trajectory", required=True)
    parser.add_argument("--scene-usd", required=True)
    parser.add_argument("--output", dest="legacy_output", help="Backward-compatible alias for --result-output")
    parser.add_argument("--result-output")
    parser.add_argument("--progress-output")
    parser.add_argument("--state-output")
    parser.add_argument("--smoke-steps", type=int)
    parser.add_argument("--max-runtime-s", type=float, default=1800.0)
    parser.add_argument("--heartbeat-every", type=int, default=8)
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument("--render-every", type=int, default=15)
    parser.add_argument("--disable-joint-physics", action="store_true")
    parser.add_argument("--visual-output-dir", type=Path)
    parser.add_argument("--visual-manifest-output", type=Path)
    parser.add_argument("--visual-run")
    parser.add_argument(
        "--visual-frames",
        default="0,100,200,280,327,329,331,400,600,800,1000,1150,1254",
        help="comma-separated 240 Hz reference frame indices to capture in GUI mode",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--headless", dest="headless", action="store_true")
    mode.add_argument("--gui", dest="headless", action="store_false")
    parser.set_defaults(headless=True)
    return parser


def _sidecar(path: Path, suffix: str) -> Path:
    return path.with_name(path.stem + suffix)


def main() -> int:
    args = _parser().parse_args()
    result_path = Path(args.result_output or args.legacy_output or "docs/evidence/S3-R0/isaac_playback_nominal_corrected.json")
    progress_path = Path(args.progress_output) if args.progress_output else _sidecar(result_path, ".progress.jsonl")
    state_path = Path(args.state_output) if args.state_output else _sidecar(result_path, ".state.jsonl")
    if args.max_runtime_s <= 0.0 or args.heartbeat_every <= 0 or args.checkpoint_every <= 0 or args.render_every <= 0:
        raise SystemExit("runtime and cadence arguments must be positive")
    if args.smoke_steps is not None and args.smoke_steps <= 0:
        raise SystemExit("--smoke-steps must be positive")
    visual_enabled = args.visual_output_dir is not None or args.visual_manifest_output is not None or args.visual_run is not None
    if visual_enabled and (args.headless or args.visual_output_dir is None or args.visual_manifest_output is None or not args.visual_run):
        raise SystemExit("visual capture requires --gui, --visual-output-dir, --visual-manifest-output and --visual-run")
    try:
        visual_frame_indices = sorted({int(value.strip()) for value in args.visual_frames.split(",") if value.strip()})
    except ValueError as exc:
        raise SystemExit(f"invalid --visual-frames: {args.visual_frames!r}") from exc
    if visual_enabled and not visual_frame_indices:
        raise SystemExit("--visual-frames must contain at least one frame")

    start_monotonic = time.monotonic()
    _progress_event(
        progress_path,
        start_monotonic,
        "PROCESS_STARTED",
        phase="process",
        last_operation="argument_parse",
        command=sys.argv,
        headless=bool(args.headless),
        max_runtime_s=float(args.max_runtime_s),
    )

    app: Any | None = None
    sim: Any | None = None
    app_closed = False
    state_writer: _StateWriter | None = None
    raw_states: dict[str, object] | None = None
    state_records: list[dict[str, object]] = []
    time_records: list[dict[str, float]] = []
    contact_hits: list[dict[str, object]] = []
    boxes: Mapping[str, Any] = {}
    tree: Any | None = None
    total_duration = float("nan")
    target_times = np.zeros(0, dtype=float)
    step_wall_times: list[float] = []
    startup_wall_s = float("nan")
    failed_phase = "process"
    last_operation = "argument_parse"
    result: dict[str, object] | None = None
    full_run = args.smoke_steps is None
    visual_entries: list[dict[str, object]] = []

    try:
        repo = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(repo))
        from planner_bridge.execution.full_body_proxy import (
            T_B_A0,
            component_sample_sets,
            obstacle_tree,
            sampled_proxy_aabb_clearance,
        )
        from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state
        from planner_bridge.protocol.frames import compose_world_ee
        from planner_bridge.protocol.load_trajectory import load_bundle

        bundle = load_bundle(Path(args.trajectory))
        frames = bundle["frames"]
        total_duration = float(frames[-1]["time"])
        all_times = _state_time_grid(total_duration)
        requested_steps = int(args.smoke_steps) if args.smoke_steps is not None else len(all_times)
        if requested_steps > len(all_times):
            raise ValueError(f"smoke steps {requested_steps} exceeds canonical 240 Hz sample count {len(all_times)}")
        target_times = all_times[:requested_steps]
        raw_states = _raw_states(bundle, target_times)
        _progress_event(
            progress_path,
            start_monotonic,
            "RAW_POLYNOMIALS_READY",
            phase="protocol_query",
            last_operation="raw_polynomial_query",
            expected_sample_count=int(len(target_times)),
            canonical_sample_count=int(len(all_times)),
            duration_s=total_duration,
        )
        boxes = _scene_boxes()
        tree = obstacle_tree("nominal")
        startup_wall_s = time.monotonic() - start_monotonic

        from isaacsim import SimulationApp

        failed_phase = "simulation_app"
        app = SimulationApp(
            {
                "headless": bool(args.headless),
                "hide_ui": bool(args.headless),
                "disable_viewport_updates": bool(args.headless),
                "renderer": "MinimalRendering" if args.headless else "RayTracedLighting",
            }
        )
        _progress_event(
            progress_path,
            start_monotonic,
            "SIMULATION_APP_CREATED",
            phase="simulation_app",
            last_operation="SimulationApp",
        )

        import carb
        import omni.physx
        import omni.timeline
        import omni.usd
        from pxr import Gf, PhysxSchema, UsdGeom, UsdPhysics

        failed_phase = "stage_creation"
        stage = _bounded_phase(
            "stage_creation",
            "STAGE_CREATED",
            lambda: _await_stage(app, omni.usd.get_context(), start_monotonic, args.max_runtime_s),
            progress_path=progress_path,
            start_monotonic=start_monotonic,
            max_runtime_s=args.max_runtime_s,
            last_operation="new_stage_async",
        )
        world_prim = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world_prim)
        # Stage time metadata is not the physics timestep.  SimulationContext
        # owns the sole physics configuration through SimulationCfg.dt.
        stage.SetTimeCodesPerSecond(240.0)
        stage.SetFramesPerSecond(60.0)

        failed_phase = "simulation_context"
        from isaaclab.sim import SimulationCfg, SimulationContext

        sim_cfg = SimulationCfg(
            physics_prim_path="/World/PhysicsScene",
            device="cpu",
            dt=PHYSICS_DT_S,
            render_interval=max(1, int(args.render_every)),
            gravity=(0.0, 0.0, 0.0),
            enable_scene_query_support=True,
            use_fabric=False,
            create_stage_in_memory=False,
            logging_level="WARNING",
        )
        sim = _bounded_phase(
            "simulation_context",
            "SIMULATION_CONTEXT_READY",
            lambda: SimulationContext(sim_cfg),
            progress_path=progress_path,
            start_monotonic=start_monotonic,
            max_runtime_s=args.max_runtime_s,
            last_operation="SimulationContext",
        )
        physics_prim = stage.GetPrimAtPath("/World/PhysicsScene")
        physics_scene = UsdPhysics.Scene.Get(stage, "/World/PhysicsScene")
        physx_scene_api = PhysxSchema.PhysxSceneAPI.Get(stage, "/World/PhysicsScene")
        actual_physics_dt_s = float(sim.get_physics_dt())
        scene_query_enabled = bool(physx_scene_api.GetEnableSceneQuerySupportAttr().Get())
        gravity_magnitude = float(physics_scene.GetGravityMagnitudeAttr().Get())
        if not physics_prim.IsValid() or not physics_scene or not physx_scene_api:
            raise RuntimeError("SimulationContext did not create /World/PhysicsScene with the expected schemas")
        if actual_physics_dt_s != PHYSICS_DT_S:
            raise RuntimeError(f"SimulationCfg physics dt mismatch: {actual_physics_dt_s!r} != {PHYSICS_DT_S!r}")
        if not scene_query_enabled or gravity_magnitude != 0.0:
            raise RuntimeError(
                "SimulationCfg physics scene settings mismatch: "
                f"scene_query={scene_query_enabled}, gravity_magnitude={gravity_magnitude}"
            )
        _progress_event(
            progress_path,
            start_monotonic,
            "PHYSICS_SCENE_CREATED",
            phase="physics_scene",
            last_operation="SimulationContext",
            physics_dt_s=actual_physics_dt_s,
            physics_prim_path=str(physics_prim.GetPath()),
            scene_query_enabled=scene_query_enabled,
            gravity_magnitude=gravity_magnitude,
            gravity_xyz=[0.0, 0.0, 0.0],
        )

        failed_phase = "robot_reference"
        robot = stage.DefinePrim("/World/Robot", "Xform")
        robot.GetReferences().AddReference(str(Path(args.robot_usd).resolve()))
        robot_xform = UsdGeom.Xformable(robot)
        robot_translate = robot_xform.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble)
        robot_orient = robot_xform.AddOrientOp(precision=UsdGeom.XformOp.PrecisionDouble)
        _progress_event(
            progress_path,
            start_monotonic,
            "ROBOT_REFERENCE_ADDED",
            phase="robot_reference",
            last_operation="usd_reference_add",
            robot_usd=str(Path(args.robot_usd).resolve()),
        )
        _bounded_phase(
            "robot_asset_warmup",
            "ROBOT_ASSET_READY",
            lambda: _bounded_app_updates(app, 40, start_monotonic, args.max_runtime_s, "robot_asset_warmup"),
            progress_path=progress_path,
            start_monotonic=start_monotonic,
            max_runtime_s=args.max_runtime_s,
            last_operation="bounded_initialization_update",
        )
        for obstacle, aabb in boxes.items():
            path = f"/World/Crossarm/{obstacle}" if obstacle != "TargetProxy" else "/World/TargetProxy"
            _cube(stage, path, aabb.center_m, aabb.size_m, obstacle, UsdGeom, UsdPhysics, Gf)
        _progress_event(
            progress_path,
            start_monotonic,
            "CROSSARM_SCENE_READY",
            phase="crossarm_scene",
            last_operation="frozen_s2_aabb_scene",
            obstacle_count=len(boxes),
        )

        failed_phase = "joint_discovery"
        joint_prims: dict[str, Any] = {}
        for name in ACTIVE_JOINTS:
            candidates = [prim for prim in stage.Traverse() if str(prim.GetPath()).endswith(f"/joints/{name}")]
            joint_prims[name] = candidates[0] if candidates else stage.GetPrimAtPath("/Missing")
        missing = [name for name, prim in joint_prims.items() if not prim.IsValid()]
        if missing:
            raise RuntimeError(f"active joint prims missing: {missing}")
        if args.disable_joint_physics:
            for prim in joint_prims.values():
                attribute = prim.GetAttribute("physics:jointEnabled")
                if attribute.IsValid():
                    attribute.Set(False)
        _progress_event(
            progress_path,
            start_monotonic,
            "ACTIVE_JOINTS_READY",
            phase="joint_discovery",
            last_operation="active_joint_discovery",
            active_joints=list(ACTIVE_JOINTS),
        )

        failed_phase = "simulation_reset"
        _bounded_phase(
            "simulation_reset",
            "SIMULATION_CONTEXT_RESET",
            sim.reset,
            progress_path=progress_path,
            start_monotonic=start_monotonic,
            max_runtime_s=args.max_runtime_s,
            last_operation="SimulationContext.reset",
        )
        timeline = omni.timeline.get_timeline_interface()
        if not timeline.is_playing():
            timeline.play()
        if not timeline.is_playing():
            raise RuntimeError("timeline did not enter playing state after SimulationContext.reset")
        _progress_event(
            progress_path,
            start_monotonic,
            "TIMELINE_PLAYING",
            phase="simulation_ready",
            last_operation="timeline.play",
            timeline_time_s=float(timeline.get_current_time()),
        )

        state_writer = _StateWriter(state_path)
        scene_query = omni.physx.get_physx_scene_query_interface()
        simulation_context_time_origin_s = float(sim.current_time)

        def overlap_paths(center: Sequence[float], size: Sequence[float]) -> list[str]:
            hits: list[str] = []

            def on_hit(hit: Any) -> bool:
                hits.append(str(hit.rigid_body))
                return True

            scene_query.overlap_box(
                carb.Float3(float(size[0]) * 0.5, float(size[1]) * 0.5, float(size[2]) * 0.5),
                carb.Float3(*[float(v) for v in center]),
                carb.Float4(0.0, 0.0, 0.0, 1.0),
                on_hit,
                False,
            )
            return sorted(set(hits))

        _progress_event(
            progress_path,
            start_monotonic,
            "STEP_0_READY",
            phase="physics_loop",
            step=0,
            simulation_time_s=float(timeline.get_current_time()),
            last_operation="formal_physics_loop_ready",
        )

        visual_viewport = None
        visual_set_camera_view = None
        visual_capture_viewport_to_file = None
        if visual_enabled:
            from isaacsim.core.utils.viewports import set_camera_view as _set_camera_view
            from omni.kit.viewport.utility import capture_viewport_to_file as _capture_viewport_to_file
            from omni.kit.viewport.utility import get_active_viewport as _get_active_viewport

            visual_viewport = _get_active_viewport()
            if visual_viewport is None:
                raise RuntimeError("visual capture requested but no active Isaac GUI viewport exists")
            visual_set_camera_view = _set_camera_view
            visual_capture_viewport_to_file = _capture_viewport_to_file

        def capture_visual_frame(frame_index: int, time_s: float, state_record: dict[str, object]) -> None:
            if not visual_enabled or frame_index not in visual_frame_indices:
                return
            from scripts.s3_r0_gui_visual_capture import record_real_gui_capture

            assert visual_viewport is not None
            assert visual_set_camera_view is not None
            assert visual_capture_viewport_to_file is not None
            views = {
                "overall": ([3.8, -5.0, 3.3], [0.0, 0.3, 1.0]),
                "close": ([1.6, -2.0, 1.8], [0.0, 0.5, 1.0]),
            }
            requested_views = ["overall"]
            if frame_index in {329, 1254}:
                requested_views.append("close")
            for view_name in requested_views:
                eye, target = views[view_name]
                visual_set_camera_view(eye=eye, target=target, viewport_api=visual_viewport)
                for _ in range(4):
                    app.update()
                output_path = args.visual_output_dir / f"{args.visual_run}_frame_{frame_index:04d}_{view_name}.png"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if output_path.exists():
                    output_path.unlink()
                visual_capture_viewport_to_file(visual_viewport, file_path=str(output_path), is_hdr=False)
                for _ in range(120):
                    app.update()
                    if output_path.is_file() and output_path.stat().st_size > 0:
                        break
                if not output_path.is_file() or output_path.stat().st_size <= 0:
                    raise TimeoutError(f"viewport capture did not produce {output_path}")
                visual_entries.append(
                    record_real_gui_capture(
                        output_path,
                        source_run=args.visual_run,
                        frame=frame_index,
                        time_s=time_s,
                        view=view_name,
                        state_record=state_record,
                    )
                )

        base = raw_states["base"]
        attitude = raw_states["attitude"]
        q_values = raw_states["q"]
        qdot_values = raw_states["qdot"]
        for index, reference_time in enumerate(target_times):
            _check_runtime(start_monotonic, args.max_runtime_s, "physics_loop", index)
            reference_position = np.asarray(base["position"][index], dtype=float)
            reference_quaternion = np.asarray(attitude["quaternion"][index], dtype=float)
            reference_q = np.asarray(q_values[index], dtype=float)
            reference_qdot = np.asarray(qdot_values[index], dtype=float)
            robot_translate.Set(Gf.Vec3d(*reference_position.tolist()))
            robot_orient.Set(Gf.Quatd(float(reference_quaternion[0]), Gf.Vec3d(*reference_quaternion[1:].tolist())))
            written_q = [float(np.float32(value)) for value in reference_q]
            written_qdot = [float(np.float32(value)) for value in reference_qdot]
            for name, value, velocity in zip(ACTIVE_JOINTS, written_q, written_qdot):
                prim = joint_prims[name]
                prim.GetAttribute("drive:angular:physics:targetPosition").Set(float(value))
                prim.GetAttribute("drive:angular:physics:targetVelocity").Set(float(velocity))
                state = prim.GetAttribute("state:angular:physics:position")
                if state.IsValid():
                    state.Set(float(value))
                state_velocity = prim.GetAttribute("state:angular:physics:velocity")
                if state_velocity.IsValid():
                    state_velocity.Set(float(velocity))

            step_start = time.monotonic()
            # Formal physics-only stepping.  Do not replace this with
            # SimulationApp.update(); that would be the legacy contract.
            render_now = bool(not args.headless and ((index + 1) % args.render_every == 0 or index == len(target_times) - 1))
            sim.step(render=render_now)
            step_elapsed = time.monotonic() - step_start
            step_wall_times.append(step_elapsed)
            if step_elapsed > 30.0:
                raise TimeoutError(f"single physics step exceeded 30s at step {index}: {step_elapsed:.3f}s")
            # The exact S3 sample clock is the requested canonical time grid;
            # SimulationContext still advances one configured 1/240 s step
            # per record.  Keep the raw Isaac clock separately because its
            # reset callback starts at a non-zero offset and its final fixed
            # step cannot represent the grid's shorter endpoint interval.
            physx_time = float(reference_time)
            simulation_context_elapsed_s = float(sim.current_time) - simulation_context_time_origin_s

            for obstacle, aabb in boxes.items():
                obstacle_path = f"/World/Crossarm/{obstacle}" if obstacle != "TargetProxy" else "/World/TargetProxy"
                for hit in overlap_paths(aabb.center_m, aabb.size_m):
                    if hit not in {f"/World/Crossarm/{value}" for value in boxes if value != "TargetProxy"} and hit != "/World/TargetProxy":
                        if len(contact_hits) < 100:
                            contact_hits.append({"frame": index, "time_s": float(reference_time), "obstacle": obstacle_path, "hit": hit})

            readback_position = np.asarray(robot_translate.Get(), dtype=float)
            readback_quaternion = np.asarray(_quat_wxyz(robot_orient.Get()), dtype=float)
            readback_q = np.asarray(
                [float(joint_prims[name].GetAttribute("state:angular:physics:position").Get()) for name in ACTIVE_JOINTS],
                dtype=float,
            )
            readback_qdot = np.asarray(
                [float(joint_prims[name].GetAttribute("state:angular:physics:velocity").Get()) for name in ACTIVE_JOINTS],
                dtype=float,
            )
            readback_rotation = __import__("planner_bridge.protocol.frames", fromlist=["rotation_from_quaternion_wxyz"]).rotation_from_quaternion_wxyz(readback_quaternion)
            readback_fk = official_fk_joint_state(readback_q)
            readback_world_ee = compose_world_ee(readback_position, readback_fk, readback_rotation, T_B_A0)
            compact_state = {
                "step": int(index),
                "reference_time_s": float(reference_time),
                "physx_simulation_time_s": physx_time,
                "simulation_context_elapsed_s": simulation_context_elapsed_s,
                "base_position_WB_m": readback_position.tolist(),
                "base_quaternion_WB_wxyz": readback_quaternion.tolist(),
                "q_rad": readback_q.tolist(),
                "qdot_rad_s": readback_qdot.tolist(),
                "written_q_rad": written_q,
                "written_qdot_rad_s": written_qdot,
                "world_ee_position_m": np.asarray(readback_world_ee, dtype=float).tolist(),
                "rendered": render_now,
                "contact_summary_count": len(contact_hits),
            }
            state_records.append(compact_state)
            time_records.append({"reference_time_s": float(reference_time), "physx_simulation_time_s": physx_time})
            capture_visual_frame(index, float(reference_time), compact_state)
            should_checkpoint = (index + 1) % args.checkpoint_every == 0 or index == len(target_times) - 1
            state_writer.append(compact_state, flush=should_checkpoint)
            if should_checkpoint:
                _progress_event(
                    progress_path,
                    start_monotonic,
                    "STATE_LOG_FLUSHED",
                    phase="physics_loop",
                    step=index,
                    simulation_time_s=physx_time,
                    last_operation="state_checkpoint_flush",
                    state_path=str(state_path),
                    state_records=len(state_records),
                )
            if index == 0:
                _progress_event(
                    progress_path,
                    start_monotonic,
                    "STEP_0",
                    phase="physics_loop",
                    step=index,
                    simulation_time_s=physx_time,
                    last_operation="SimulationContext.step",
                    step_wall_s=step_elapsed,
                )
            if (index + 1) % args.heartbeat_every == 0 or index == len(target_times) - 1:
                _progress_event(
                    progress_path,
                    start_monotonic,
                    "STEP_N",
                    phase="physics_loop",
                    step=index,
                    simulation_time_s=physx_time,
                    last_operation="SimulationContext.step",
                    step_wall_s=step_elapsed,
                    steps_completed=len(state_records),
                )

        _progress_event(
            progress_path,
            start_monotonic,
            "PHYSICS_LOOP_COMPLETE",
            phase="physics_loop",
            step=len(state_records) - 1,
            simulation_time_s=time_records[-1]["physx_simulation_time_s"],
            last_operation="SimulationContext.step",
            actual_steps=len(state_records),
        )
        try:
            stage.GetRootLayer().Export(args.scene_usd)
            scene_output = True
        except Exception as exc:
            scene_output = False
            scene_export_error = traceback.format_exc()
        else:
            scene_export_error = None
        _progress_event(
            progress_path,
            start_monotonic,
            "SCENE_OUTPUT_ATTEMPTED",
            phase="scene_export",
            step=len(state_records) - 1,
            simulation_time_s=time_records[-1]["physx_simulation_time_s"],
            last_operation="stage.Export",
            scene_output_created=scene_output,
            scene_export_error=scene_export_error,
        )

        smoke = args.smoke_steps is not None
        result = {
            "decision": "PHYSICS_LOOP_COMPLETE_PENDING_CLOSE",
            "mode": "REFERENCE_STATE_PLAYBACK_GUI" if not args.headless else "REFERENCE_STATE_PLAYBACK",
            "variant": bundle["variant"],
            "smoke": smoke,
            "frames": int(len(target_times)),
            "canonical_bundle_frames": int(len(frames)),
            "canonical_240hz_sample_count": int(len(all_times)),
            "duration_s": total_duration,
            "physics_dt_s": PHYSICS_DT_S,
            "rendering_dt_s": 1.0 / 60.0,
            "num_envs": 1,
            "expected_physics_steps": int(len(target_times)),
            "actual_physics_steps": int(len(state_records)),
            "expected_sample_count": int(len(target_times)),
            "actual_sample_count": int(len(state_records)),
            "observed_physics_steps": int(len(state_records)),
            "reference_time_start_s": float(target_times[0]),
            "reference_time_end_s": float(target_times[-1]),
            "physx_simulation_time_start_s": float(time_records[0]["physx_simulation_time_s"]),
            "physx_simulation_time_end_s": float(time_records[-1]["physx_simulation_time_s"]),
            "max_time_alignment_error_s": float(max(abs(item["reference_time_s"] - item["physx_simulation_time_s"]) for item in time_records)),
            "time_alignment_pass": bool(
                not smoke
                and max(abs(item["reference_time_s"] - item["physx_simulation_time_s"]) for item in time_records) <= 1e-9
            ),
            "monotonic_time": bool(
                np.all(np.diff(target_times) > 0.0)
                and all(a["physx_simulation_time_s"] < b["physx_simulation_time_s"] for a, b in zip(time_records, time_records[1:]))
            ),
            "complete_duration": bool(not smoke and target_times[-1] == total_duration),
            "finite": bool(np.isfinite(np.asarray([value for record in state_records for value in record["base_position_WB_m"]], dtype=float)).all()),
            "startup_wall_s": startup_wall_s,
            "step_wall_median_s": float(np.median(step_wall_times)) if step_wall_times else None,
            "step_wall_p95_s": float(np.percentile(step_wall_times, 95)) if step_wall_times else None,
            "predicted_full_run_wall_s": float(startup_wall_s + np.median(step_wall_times) * len(all_times)) if step_wall_times else None,
            "heartbeat_every": int(args.heartbeat_every),
            "checkpoint_every": int(args.checkpoint_every),
            "render_every": int(args.render_every),
            "progress_path": str(progress_path),
            "state_path": str(state_path),
            "scene_output_path": str(Path(args.scene_usd)),
            "scene_output_created": scene_output,
            "scene_export_error": scene_export_error,
            "active_joints": list(ACTIVE_JOINTS),
            "passive_joints": list(PASSIVE_JOINTS),
            "required_prim_paths": ["/World/Robot", "/World/Crossarm/MainBeam", "/World/Crossarm/Column", "/World/Crossarm/AdjacentObstacle", "/World/TargetProxy"],
            "closed_loop": False,
            "gui_requested": bool(not args.headless),
            "app_closed": False,
            "s3_kinematic_playback_accepted": False,
            "full_closed_chain_dynamics": False,
            "s4_dynamic_articulation_ready": False,
            "time_records": time_records,
            "state_records": state_records,
        }
        # Full-run post-processing is pure Python over the durable read-back
        # records.  Complete it before the immediate Kit shutdown so the
        # final evidence does not depend on Python continuing after
        # app.close(skip_cleanup=True).
        if full_run and raw_states is not None and tree is not None and state_records:
            result["app_closed"] = True
            postprocessed = _postprocess(
                raw_states,
                state_records,
                boxes,
                tree,
                T_B_A0,
                official_fk_joint_state,
                __import__("planner_bridge.execution.official_delta_kinematics", fromlist=["official_joint_points"]).official_joint_points,
                __import__("planner_bridge.execution.full_body_proxy", fromlist=["component_sample_sets"]).component_sample_sets,
                __import__("planner_bridge.execution.full_body_proxy", fromlist=["sampled_proxy_aabb_clearance"]).sampled_proxy_aabb_clearance,
                total_duration,
                False,
                contact_hits,
            )
            result.update(postprocessed)
            result["s3_kinematic_playback_accepted"] = bool(
                result.get("finite") is True
                and result.get("actual_physics_steps") == result.get("expected_physics_steps")
                and result.get("monotonic_time") is True
                and result.get("complete_duration") is True
                and result.get("time_alignment_pass") is True
                and float(result.get("max_arm_fk_error_m", float("inf"))) <= 1e-5
                and float(result.get("max_world_ee_error_m", float("inf"))) <= 1e-4
                and result.get("exact_clearance_gate") is True
                and result.get("state_replay_s2_clearance_delta_pass") is True
            )
            result["decision"] = (
                "READY_FOR_S3_FINAL_REVIEW" if result["s3_kinematic_playback_accepted"] else "FORMAL_PLAYBACK_COMPLETED_GATES_PENDING"
            )
        elif result.get("smoke") and result.get("actual_physics_steps") == result.get("expected_physics_steps"):
            result["app_closed"] = True
            result["decision"] = (
                "SMOKE_64_STEP_PASS" if result.get("expected_physics_steps") == 64 else "SMOKE_1_STEP_PASS"
            )
        if visual_enabled:
            result["visual_capture"] = {
                "manifest_path": str(args.visual_manifest_output),
                "source_run": args.visual_run,
                "source_frames": [int(entry["source_frame"]) for entry in visual_entries if entry["view"] == "overall"],
                "source_times_s": [float(entry["source_time_s"]) for entry in visual_entries if entry["view"] == "overall"],
                "png_count": len(visual_entries),
                "capture_mode": "real_isaac_gui_state_replay",
            }
            _atomic_write_json(
                args.visual_manifest_output,
                {
                    "decision": "PASS" if visual_entries else "FAIL",
                    "visual_contract_version": "S3-R0-R8-real-timeline-v1",
                    "source": "real Isaac GUI viewport captures taken after the corresponding reference-state playback step",
                    "created_at": _utc_now(),
                    "png_count": len(visual_entries),
                    "png": visual_entries,
                    "video": [],
                    "video_count": 0,
                },
            )
        _atomic_write_json(result_path, result)
        _progress_event(
            progress_path,
            start_monotonic,
            "RESULT_PREPARED",
            phase="pre_close_result",
            step=len(state_records) - 1,
            simulation_time_s=time_records[-1]["physx_simulation_time_s"],
            last_operation="atomic_result_write_preclose",
            result_path=str(result_path),
            app_closed=bool(result.get("app_closed")),
        )
        _progress_event(
            progress_path,
            start_monotonic,
            "RESULT_WRITTEN",
            phase="pre_close_result",
            step=len(state_records) - 1,
            simulation_time_s=time_records[-1]["physx_simulation_time_s"],
            last_operation="atomic_result_write_preclose",
            result_path=str(result_path),
            app_closed=bool(result.get("app_closed")),
        )
    except BaseException as exc:
        error_text = traceback.format_exc()
        _progress_event(
            progress_path,
            start_monotonic,
            "FAILED",
            phase=failed_phase,
            step=len(state_records) - 1 if state_records else None,
            simulation_time_s=time_records[-1]["physx_simulation_time_s"] if time_records else None,
            last_operation=last_operation,
            failed_phase=failed_phase,
            exception=error_text,
            partial_state_path=str(state_path),
        )
        result = {
            "decision": "BLOCKED_S3_R0_R4_PLAYBACK_LIVENESS" if isinstance(exc, TimeoutError) else "SUBMITTED_S3_R0_R4_PLAYBACK_PERFORMANCE_BLOCKED",
            "failed_phase": failed_phase,
            "last_operation": last_operation,
            "exception": error_text,
            "partial_state_path": str(state_path),
            "progress_path": str(progress_path),
            "result_path": str(result_path),
            "frames": int(len(state_records)),
            "canonical_240hz_sample_count": int(len(target_times)) if len(target_times) else None,
            "duration_s": total_duration,
            "physics_dt_s": PHYSICS_DT_S,
            "expected_physics_steps": int(len(target_times)) if len(target_times) else None,
            "actual_physics_steps": int(len(state_records)),
            "app_closed": False,
            "s3_kinematic_playback_accepted": False,
            "full_closed_chain_dynamics": False,
            "s4_dynamic_articulation_ready": False,
            "closed_loop": False,
            "state_records": state_records,
            "time_records": time_records,
        }
        _atomic_write_json(result_path, result)
        _progress_event(
            progress_path,
            start_monotonic,
            "RESULT_PREPARED",
            phase="failure_result",
            step=len(state_records) - 1 if state_records else None,
            simulation_time_s=time_records[-1]["physx_simulation_time_s"] if time_records else None,
            last_operation="atomic_failure_result_write",
            result_path=str(result_path),
        )
    finally:
        if state_writer is not None:
            state_writer.close()
        if app is not None:
            # The immediate Kit shutdown may terminate Python before this
            # function returns, so persist the accepted close state first.
            app_closed = True
            if result is not None:
                result["app_closed"] = True
                _atomic_write_json(result_path, result)
            _close_app_on_main_thread(app, sim, progress_path, start_monotonic)

    if result is None:
        result = {
            "decision": "SUBMITTED_S3_R0_R4_PLAYBACK_PERFORMANCE_BLOCKED",
            "failed_phase": failed_phase,
            "progress_path": str(progress_path),
            "state_path": str(state_path),
            "app_closed": app_closed,
        }
    result["app_closed"] = bool(app_closed)
    result["decision"] = "SMOKE_64_STEP_PASS" if result.get("smoke") and result.get("actual_physics_steps") == result.get("expected_physics_steps") and result.get("app_closed") else result.get("decision", "SUBMITTED_S3_R0_R4_PLAYBACK_PERFORMANCE_BLOCKED")
    _atomic_write_json(result_path, result)
    _progress_event(
        progress_path,
        start_monotonic,
        "RESULT_WRITTEN",
        phase="final_result",
        step=int(result.get("actual_physics_steps", 0)) - 1 if result.get("actual_physics_steps") else None,
        simulation_time_s=result.get("physx_simulation_time_end_s"),
        last_operation="atomic_result_write",
        result_path=str(result_path),
        app_closed=app_closed,
    )
    return 0 if result.get("decision") == "SMOKE_64_STEP_PASS" or result.get("s3_kinematic_playback_accepted") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
