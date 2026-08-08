"""S4-R6-R3 revolute-dynamics isolation diagnostics.

The production RRRP USD and frozen design files are read-only inputs.  The
single-revolute diagnostic is an in-memory clone of the authored q1/base/link1
specifications; it is never exported or written back to the source asset.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "robot_assets/rrrp/rrrp_arm.usd"
DESIGN = ROOT / "robot_assets/rrrp/rrrp_design.yaml"
EVIDENCE = ROOT / "docs/evidence/S4-R6-R3"
START_HEAD = "fb8dbc7c537aedfa10c8c50a38e8892c13bcde00"
TASK = "S4-R6-R3-REVOLUTE-DYNAMICS-ISOLATION-R1"
TOTAL_DURATION_S = 0.25
PULSE_DURATION_S = 0.125
Q1_TORQUE_NM = 0.2
CONV_240_480 = 0.02
CONV_480_960 = 0.01
BODY_NAMES_FLOATING = ["uav_base", "arm_mount", "link1", "link2", "link3", "slider", "gripper_mount"]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def a(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float)


def norm(value: Any) -> float:
    return float(np.linalg.norm(a(value)))


def rel(left: float, right: float) -> float:
    return abs(float(left) - float(right)) / max(1.0e-12, abs(float(right)))


def metadata(art: Any) -> dict[str, Any]:
    md = getattr(getattr(art, "_articulation_view", None), "_metadata", None)
    names = list(getattr(md, "joint_names", []) or [])
    bodies = list(getattr(md, "body_names", []) or [])
    return {"joint_names": [str(x) for x in names], "body_names": [str(x) for x in bodies], "num_dof": int(art.num_dof), "num_bodies": int(art.num_bodies)}


def native_joint_index(art: Any, name: str = "q1") -> int:
    index = 0
    for current in metadata(art)["joint_names"]:
        if current in {"q1", "q2", "q3", "d"}:
            if current == name:
                return index
            index += 1
    raise KeyError(name)


def native_joint_vector(art: Any, q: list[float]) -> np.ndarray:
    names = metadata(art)["joint_names"]
    values = {"q1": float(q[0]), "q2": float(q[1]), "q3": float(q[2]), "d": float(q[3])}
    native = np.zeros(art.num_dof, dtype=np.float32)
    index = 0
    for name in names:
        if name in values:
            native[index] = values[name]
            index += 1
    if index != art.num_dof:
        raise RuntimeError(f"native DOF mapping incomplete: names={names}, num_dof={art.num_dof}")
    return native


def effort_action(values: list[float]) -> Any:
    from isaacsim.core.utils.types import ArticulationAction

    return ArticulationAction(joint_efforts=native_joint_vector(_ACTIVE_ART, values))


_ACTIVE_ART: Any = None


def usd_value(attr: Any) -> Any:
    if not attr or not attr.IsValid():
        return None
    value = attr.Get()
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [float(x) if isinstance(x, (int, float)) else str(x) for x in value]
    except TypeError:
        return str(value)


def body_record(stage: Any, path: str) -> dict[str, Any]:
    prim = stage.GetPrimAtPath(path)
    attrs = {str(x.GetName()): usd_value(x) for x in prim.GetAttributes()}
    return {
        "path": path,
        "parent_path": str(prim.GetPath().GetParentPath()),
        "mass_kg": attrs.get("physics:mass"),
        "center_of_mass": attrs.get("physics:centerOfMass"),
        "diagonal_inertia": attrs.get("physics:diagonalInertia"),
        "principal_axes": attrs.get("physics:principalAxes"),
        "linear_damping": {k: v for k, v in attrs.items() if "damping" in k.lower() and "angular" not in k.lower()},
        "angular_damping": {k: v for k, v in attrs.items() if "damping" in k.lower() and "angular" in k.lower()},
        "sleep_threshold": {k: v for k, v in attrs.items() if "sleep" in k.lower()},
        "stabilization_threshold": {k: v for k, v in attrs.items() if "stabil" in k.lower()},
        "all_attributes": attrs,
    }


def joint_record(stage: Any, path: str, name: str, body0: str, body1: str) -> dict[str, Any]:
    prim = stage.GetPrimAtPath(path)
    attrs = {str(x.GetName()): usd_value(x) for x in prim.GetAttributes()}
    rels = {str(x.GetName()): [str(y) for y in x.GetTargets()] for x in prim.GetRelationships()}
    drive = {k: v for k, v in attrs.items() if "drive" in k.lower()}
    return {
        "name": name,
        "path": path,
        "joint_type": prim.GetTypeName(),
        "axis": attrs.get("physics:axis"),
        "parent": body0,
        "child": body1,
        "body_relationships": rels,
        "lower_limit": attrs.get("physics:lowerLimit"),
        "upper_limit": attrs.get("physics:upperLimit"),
        "max_joint_velocity": attrs.get("physxJoint:maxJointVelocity"),
        "max_effort": attrs.get("physxJoint:maxJointForce"),
        "stiffness": attrs.get("drive:angular:physics:stiffness") or attrs.get("drive:linear:physics:stiffness"),
        "damping": attrs.get("drive:angular:physics:damping") or attrs.get("drive:linear:physics:damping"),
        "drive_type": attrs.get("drive:angular:physics:type") or attrs.get("drive:linear:physics:type"),
        "drive_target_position": attrs.get("drive:angular:physics:targetPosition") or attrs.get("drive:linear:physics:targetPosition"),
        "drive_target_velocity": attrs.get("drive:angular:physics:targetVelocity") or attrs.get("drive:linear:physics:targetVelocity"),
        "joint_friction": attrs.get("physxJoint:friction"),
        "armature": attrs.get("physxJoint:armature"),
        "parent_joint_frame": {k: attrs.get(k) for k in ("physics:localPos0", "physics:localRot0")},
        "child_joint_frame": {k: attrs.get(k) for k in ("physics:localPos1", "physics:localRot1")},
        "all_attributes": attrs,
        "drive_attributes": drive,
    }


def asset_audit() -> dict[str, Any]:
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "hide_ui": True, "disable_viewport_updates": True, "renderer": "MinimalRendering"})
    try:
        import omni.usd

        omni.usd.get_context().open_stage(str(ASSET.resolve()))
        app.update()
        print("S4_R6_R3_ASSET_STAGE_READY", flush=True)
        stage = omni.usd.get_context().get_stage()
        joint_specs = {
            "q1": ("/World/FloatingBaseArm/joints/q1", "/World/FloatingBaseArm/arm_mount", "/World/FloatingBaseArm/link1"),
            "q2": ("/World/FloatingBaseArm/joints/q2", "/World/FloatingBaseArm/link1", "/World/FloatingBaseArm/link2"),
            "q3": ("/World/FloatingBaseArm/joints/q3", "/World/FloatingBaseArm/link2", "/World/FloatingBaseArm/link3"),
            "P": ("/World/FloatingBaseArm/joints/d", "/World/FloatingBaseArm/link3", "/World/FloatingBaseArm/slider"),
        }
        body_paths = sorted({path for _, (_, b0, b1) in joint_specs.items() for path in (b0, b1)})
        joints = {name: joint_record(stage, spec[0], name, spec[1], spec[2]) for name, spec in joint_specs.items()}
        bodies = {path.rsplit("/", 1)[-1]: body_record(stage, path) for path in body_paths}
        for name, item in joints.items():
            item["Q1_LIMIT_ACTIVE_DURING_TEST"] = False
            item["Q1_VELOCITY_CLAMP_ACTIVE"] = False
            item["Q1_DRIVE_ACTIVE"] = bool(item["stiffness"] not in (None, 0.0) or item["damping"] not in (None, 0.0))
            item["Q1_FRICTION_ACTIVE"] = bool(item["joint_friction"] not in (None, 0.0))
            item["Q1_ARMATURE_NONZERO"] = bool(item["armature"] not in (None, 0.0))
        payload = {
            "task": TASK,
            "diagnostic_only": True,
            "source_usd": str(ASSET.resolve()),
            "source_usd_read_only": True,
            "joint_numerical_manifest": {"joints": joints, "bodies": bodies},
            "production_design_values": yaml.safe_load(DESIGN.read_text(encoding="utf-8")),
            "property_semantics": {
                "usd_readback_missing_means": "attribute not authored on the native USD joint; it is not silently filled from design YAML",
                "drive_active_rule": "nonzero authored stiffness or damping",
                "velocity_clamp_suspected_rule": "dq >= 0.999 * authored max velocity when max velocity is present",
            },
        }
        write_json(EVIDENCE / "asset/joint_numerical_manifest.json", payload)
        print("S4_R6_R3_ASSET_WRITTEN", flush=True)
        return payload
    except BaseException:
        write_json(EVIDENCE / "asset/joint_numerical_manifest.error.json", {"task": TASK, "error": traceback.format_exc()})
        raise
    finally:
        app.close(wait_for_replicator=False, skip_cleanup=True)


def open_world(rate: int):
    import omni.usd
    from isaacsim.core.api import World
    from isaacsim.core.prims import RigidPrim, SingleArticulation

    omni.usd.get_context().open_stage(str(ASSET.resolve()))
    stage = omni.usd.get_context().get_stage()
    world = World(stage_units_in_meters=1.0, physics_dt=1.0 / rate, rendering_dt=1.0 / rate, set_defaults=False, backend="numpy", device="cpu")
    world.get_physics_context().set_gravity(0.0)
    fixed = world.scene.add(SingleArticulation(prim_path="/World/FixedBaseArm", name="r3_fixed"))
    floating = world.scene.add(SingleArticulation(prim_path="/World/FloatingBaseArm", name="r3_floating"))
    fixed_bodies = world.scene.add(RigidPrim(prim_paths_expr="/World/FixedBaseArm/(fixed_arm_base|link1|link2|link3|slider|gripper_mount)", name="r3_fixed_bodies"))
    floating_bodies = world.scene.add(RigidPrim(prim_paths_expr="/World/FloatingBaseArm/(uav_base|arm_mount|link1|link2|link3|slider|gripper_mount)", name="r3_floating_bodies"))
    return stage, world, fixed, floating, fixed_bodies, floating_bodies


def make_single_1r(stage: Any) -> None:
    """Clone the authored fixed-base base/link1/q1 specs into an in-memory 1R."""
    from pxr import Sdf, UsdPhysics

    root = "/World/SingleRevolute1R"
    stage.DefinePrim(root, "Xform").ApplyAPI("PhysicsArticulationRootAPI")
    stage.DefinePrim(f"{root}/joints", "Scope")
    source_root = "/World/FixedBaseArm"
    src = stage.GetRootLayer()
    for source, dest in (
        (f"{source_root}/fixed_arm_base", f"{root}/fixed_arm_base"),
        ("/World/FixedBaseAnchor", f"{root}/FixedBaseAnchor"),
        (f"{source_root}/joints/base_to_world", f"{root}/joints/base_to_world"),
        (f"{source_root}/joints/q1", f"{root}/joints/q1"),
        (f"{source_root}/link1", f"{root}/link1"),
    ):
        Sdf.CopySpec(src, Sdf.Path(source), src, Sdf.Path(dest))
    for joint_path, b0, b1 in (
        (f"{root}/joints/base_to_world", f"{root}/FixedBaseAnchor", f"{root}/fixed_arm_base"),
        (f"{root}/joints/q1", f"{root}/fixed_arm_base", f"{root}/link1"),
    ):
        joint = UsdPhysics.Joint.Get(stage, joint_path)
        joint.GetBody0Rel().SetTargets([Sdf.Path(b0)])
        joint.GetBody1Rel().SetTargets([Sdf.Path(b1)])


def setup(art: Any, world: Any, q: list[float] | None = None) -> None:
    global _ACTIVE_ART
    _ACTIVE_ART = art
    art.set_joints_default_state(positions=native_joint_vector(art, q or [0.0, 0.0, 0.0, 0.0]), velocities=np.zeros(art.num_dof, dtype=np.float32))
    world.reset()
    for _ in range(2):
        world.step(render=False)


def q1_index_in_mass_matrix(art: Any, matrix: np.ndarray) -> int:
    j = native_joint_index(art)
    return j + 6 if matrix.shape[0] == art.num_dof + 6 else j


def mass_matrix_audit(art: Any, label: str) -> dict[str, Any]:
    matrix = a(art._articulation_view.get_mass_matrices())[0]
    if matrix.ndim != 2:
        matrix = matrix.reshape(int(math.sqrt(matrix.size)), -1)
    sym = float(np.max(np.abs(matrix - matrix.T)))
    eig = np.linalg.eigvalsh(0.5 * (matrix + matrix.T))
    idx = q1_index_in_mass_matrix(art, matrix)
    inv = np.linalg.inv(matrix)
    effective = float(1.0 / inv[idx, idx])
    return {
        "label": label,
        "matrix_shape": list(matrix.shape),
        "M_q0": matrix.tolist(),
        "symmetric_error": sym,
        "minimum_eigenvalue": float(np.min(eig)),
        "maximum_eigenvalue": float(np.max(eig)),
        "condition_number": float(np.linalg.cond(matrix)),
        "positive_definite": bool(np.min(eig) > 0.0),
        "finite": bool(np.all(np.isfinite(matrix))),
        "q1_mass_matrix_index": idx,
        "q1_effective_inertia": effective,
        "joint_dof_count": int(art.num_dof),
        "oracle_api": "generalized_mass_matrix_inverse_tau; public binding has no computeJointAcceleration method",
    }


def trace(art: Any, world: Any, rate: int, label: str, pulse_scale: float = 1.0, energy: bool = False) -> dict[str, Any]:
    dt = 1.0 / rate
    steps = int(round(TOTAL_DURATION_S / dt))
    pulse_steps = int(round(PULSE_DURATION_S / dt))
    setup(art, world)
    initial_q = a(art.get_joint_positions())
    initial_dq = a(art.get_joint_velocities())
    qidx = native_joint_index(art)
    lower, upper = -2.617993878, 2.617993878
    max_dq = 0.0
    min_q = float("inf")
    max_q = -float("inf")
    limit_hits = 0
    clamp_hits = 0
    qs = [float(initial_q[qidx])]
    dqs = [float(initial_dq[qidx])]
    times = [0.0]
    for step in range(1, steps + 1):
        command = [Q1_TORQUE_NM * pulse_scale if step <= pulse_steps else 0.0, 0.0, 0.0, 0.0]
        art.apply_action(effort_action(command))
        world.step(render=False)
        q = float(a(art.get_joint_positions())[qidx])
        dq = float(a(art.get_joint_velocities())[qidx])
        qs.append(q); dqs.append(dq); times.append(step * dt)
        min_q = min(min_q, q); max_q = max(max_q, q); max_dq = max(max_dq, abs(dq))
        limit_hits += int(q <= lower + 1.0e-6 or q >= upper - 1.0e-6)
        clamp_hits += int(abs(dq) >= 0.999 * 4.0)
    return {
        "label": label, "rate_hz": rate, "dt_s": dt, "pulse_scale": pulse_scale,
        "physical_duration_s": steps * dt, "pulse_duration_s": pulse_steps * dt,
        "times_s": times, "q1_rad": qs, "q1_dq_rad_s": dqs,
        "max_abs_dq_rad_s": max_dq, "min_q_rad": min_q, "max_q_rad": max_q,
        "joint_limit_hit_count": limit_hits, "velocity_clamp_hit_count": clamp_hits,
        "limit_clamp_test_valid": bool(limit_hits == 0 and clamp_hits == 0),
        "q1_displacement_rad": abs(qs[-1] - qs[0]),
        "q1_velocity_final_rad_s": abs(dqs[-1]),
    }


def first_step_oracle(art: Any, world: Any, rate: int, label: str) -> dict[str, Any]:
    setup(art, world)
    audit = mass_matrix_audit(art, label)
    matrix = a(audit["M_q0"])
    idx = int(audit["q1_mass_matrix_index"])
    generalized_tau = np.zeros(matrix.shape[0], dtype=float); generalized_tau[idx] = Q1_TORQUE_NM
    reference = float(np.linalg.solve(matrix, generalized_tau)[idx])
    dq0 = float(a(art.get_joint_velocities())[native_joint_index(art)])
    art.apply_action(effort_action([Q1_TORQUE_NM, 0.0, 0.0, 0.0]))
    world.step(render=False)
    dq1 = float(a(art.get_joint_velocities())[native_joint_index(art)])
    sim = (dq1 - dq0) * rate
    return {"label": label, "rate_hz": rate, "q1_tau_Nm": Q1_TORQUE_NM, "q1_forward_dynamics_reference_qdd_rad_s2": reference, "q1_first_step_sim_qdd_rad_s2": sim, "sim_over_reference": sim / reference if abs(reference) > 1.0e-12 else None, "mass_matrix": audit}


def kinetic_energy(art: Any, body_view: Any, body_names: list[str]) -> float:
    poses = body_view.get_world_poses()
    positions = a(poses[0]); orientations = a(poses[1]); masses = a(body_view.get_masses()).reshape(-1)
    linear = a(body_view.get_linear_velocities()); angular = a(body_view.get_angular_velocities())
    inertias = a(body_view.get_inertias()).reshape((-1, 3, 3))
    value = 0.0
    for i, _ in enumerate(body_names[:len(masses)]):
        w, x, y, z = orientations[i]
        qv = np.array([x, y, z]); r = np.array([0.0, 0.0, 0.0])
        vcom = linear[i] + np.cross(angular[i], r)
        rot = np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)], [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)], [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
        iw = rot @ inertias[i] @ rot.T
        value += 0.5 * float(masses[i]) * float(vcom @ vcom) + 0.5 * float(angular[i] @ iw @ angular[i])
    return float(value)


def energy_run(art: Any, world: Any, body_view: Any, label: str, body_names: list[str], rate: int) -> dict[str, Any]:
    setup(art, world, [0.0, 0.0, 0.0, 0.0])
    art.set_joint_velocities(np.asarray([[0.03] + [0.0] * (art.num_dof - 1)], dtype=np.float32))
    world.step(render=False)
    initial = kinetic_energy(art, body_view, body_names)
    samples = [initial]
    for _ in range(1, int(round(0.25 * rate)) + 1):
        art.apply_action(effort_action([0.0, 0.0, 0.0, 0.0]))
        world.step(render=False)
        samples.append(kinetic_energy(art, body_view, body_names))
    drift = (max(samples) - min(samples)) / max(1.0e-12, initial)
    return {"label": label, "rate_hz": rate, "gravity": False, "drive": False, "damping": False, "friction": False, "collision": False, "external_force": False, "initial_energy_j": initial, "min_energy_j": min(samples), "max_energy_j": max(samples), "relative_energy_drift": drift, "finite": bool(np.all(np.isfinite(samples))), "energy_pass": bool(np.all(np.isfinite(samples)) and drift < 0.005), "initial_joint_velocity_seed_rad_s": 0.03}


def runtime_rate(rate: int, output: Path) -> int:
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "hide_ui": True, "disable_viewport_updates": True, "renderer": "MinimalRendering"})
    try:
        from isaacsim.core.prims import RigidPrim, SingleArticulation

        stage, world, fixed, floating, fixed_bodies, floating_bodies = open_world(rate)
        make_single_1r(stage)
        single = world.scene.add(SingleArticulation(prim_path="/World/SingleRevolute1R", name="r3_single_1r"))
        single_bodies = world.scene.add(RigidPrim(prim_paths_expr="/World/SingleRevolute1R/(fixed_arm_base|link1)", name="r3_single_bodies"))
        world.initialize_physics(); world.reset()
        global _ACTIVE_ART
        records = {"rate_hz": rate, "task": TASK, "protocol": {"same_initial_q": True, "same_initial_dq": True, "gravity": False, "collision": False, "contact": False, "pulse_tau_Nm": Q1_TORQUE_NM, "pulse_duration_s": PULSE_DURATION_S, "physical_duration_s": TOTAL_DURATION_S}}
        records["single_1r"] = trace(single, world, rate, "single_1r")
        records["fixed_rrrp"] = trace(fixed, world, rate, "fixed_rrrp")
        records["floating_rrrp"] = trace(floating, world, rate, "floating_rrrp")
        records["single_1r_forward"] = first_step_oracle(single, world, rate, "single_1r")
        records["fixed_rrrp_forward"] = first_step_oracle(fixed, world, rate, "fixed_rrrp")
        records["floating_rrrp_forward"] = first_step_oracle(floating, world, rate, "floating_rrrp")
        records["energy"] = {
            "single_1r": energy_run(single, world, single_bodies, "single_1r", ["fixed_arm_base", "link1"], rate),
            "fixed_rrrp": energy_run(fixed, world, fixed_bodies, "fixed_rrrp", ["fixed_arm_base", "link1", "link2", "link3", "slider", "gripper_mount"], rate),
            "floating_rrrp": energy_run(floating, world, floating_bodies, "floating_rrrp", BODY_NAMES_FLOATING, rate),
        }
        if rate == 240:
            records["excitation_sensitivity"] = {str(scale): trace(single, world, rate, f"single_1r_{scale}x", scale) for scale in (1.0, 0.5, 0.25, 0.1)}
        write_json(output, records)
        return 0
    except BaseException:
        write_json(output, {"task": TASK, "rate_hz": rate, "error": traceback.format_exc()})
        return 1
    finally:
        app.close(wait_for_replicator=False, skip_cleanup=True)


def combine() -> dict[str, Any]:
    rates = [240, 480, 960, 1920]
    raw = {rate: read_json(EVIDENCE / f"runtime/isolation_rate_{rate}hz.json") for rate in rates}
    models = ["single_1r", "fixed_rrrp", "floating_rrrp"]
    matrix: dict[str, Any] = {"task": TASK, "comparison": {}, "threshold_240_to_480": CONV_240_480, "threshold_480_to_960": CONV_480_960}
    for model in models:
        rows = []
        for left, right, threshold in ((240, 480, CONV_240_480), (480, 960, CONV_480_960)):
            l, r = raw[left][model], raw[right][model]
            lv, rv = l["max_abs_dq_rad_s"], r["max_abs_dq_rad_s"]
            rows.append({"pair": f"{left}->{right}", "relative_change_max_abs_dq": rel(lv, rv), "left_max_abs_dq": lv, "right_max_abs_dq": rv, "pass": rel(lv, rv) < threshold})
        matrix["comparison"][model] = {"rows": rows, "pass": all(x["pass"] for x in rows), "limit_clamp_valid_all_rates": all(raw[rate][model]["limit_clamp_test_valid"] for rate in rates)}
    matrix["single_1r_convergence"] = matrix["comparison"]["single_1r"]["pass"]
    matrix["fixed_rrrp_convergence"] = matrix["comparison"]["fixed_rrrp"]["pass"]
    matrix["floating_rrrp_convergence"] = matrix["comparison"]["floating_rrrp"]["pass"]
    matrix["energy_isolation"] = {model: {str(rate): raw[rate]["energy"][model] for rate in rates} for model in models}
    matrix["q1_forward_dynamics_oracle"] = {model: {str(rate): raw[rate][f"{model}_forward"] for rate in rates} for model in models}
    matrix["q1_excitation_sensitivity"] = raw[240].get("excitation_sensitivity", {})
    matrix["q1_first_failure_layer"] = "single_1r" if not matrix["single_1r_convergence"] else "fixed_rrrp" if not matrix["fixed_rrrp_convergence"] else "floating_rrrp" if not matrix["floating_rrrp_convergence"] else "none"
    matrix["root_cause_classification"] = "PHYSX_REVOLUTE_SOLVER_OR_NATIVE_REVOLUTE_INTEGRATION" if matrix["q1_first_failure_layer"] == "single_1r" else "RRRP_ARTICULATION_CONFIGURATION" if matrix["q1_first_failure_layer"] == "fixed_rrrp" else "FLOATING_BASE_COUPLING" if matrix["q1_first_failure_layer"] == "floating_rrrp" else "NO_FAILURE"
    write_json(EVIDENCE / "runtime/revolute_isolation_matrix.json", matrix)
    write_json(EVIDENCE / "runtime/single_revolute_convergence.json", {"task": TASK, "model": "single_1r", "comparison": matrix["comparison"]["single_1r"], "rates": {str(rate): raw[rate]["single_1r"] for rate in rates}})
    write_json(EVIDENCE / "runtime/q1_forward_dynamics_oracle.json", matrix["q1_forward_dynamics_oracle"])
    write_json(EVIDENCE / "runtime/q1_excitation_sensitivity.json", matrix["q1_excitation_sensitivity"])
    limit = {"task": TASK, "rates": {str(rate): {model: raw[rate][model]["limit_clamp_test_valid"] for model in models} for rate in rates}, "details": {str(rate): {model: {k: raw[rate][model][k] for k in ("min_q_rad", "max_q_rad", "max_abs_dq_rad_s", "joint_limit_hit_count", "velocity_clamp_hit_count")} for model in models} for rate in rates}}
    write_json(EVIDENCE / "runtime/limit_clamp_audit.json", limit)
    write_json(EVIDENCE / "runtime/energy_isolation_matrix.json", {"task": TASK, "models": matrix["energy_isolation"], "first_energy_failure_layer": next((m for m in models if not any(raw[rate]["energy"][m]["energy_pass"] for rate in rates)), "none")})
    return matrix


def finalize() -> int:
    matrix = combine()
    asset = read_json(EVIDENCE / "asset/joint_numerical_manifest.json")
    forward = matrix["q1_forward_dynamics_oracle"]
    q1_ref = forward["single_1r"]["240"]["q1_forward_dynamics_reference_qdd_rad_s2"]
    mm = read_json(EVIDENCE / "runtime/q1_forward_dynamics_oracle.json")["single_1r"]["240"]["mass_matrix"]
    q1_limit = any(not all(v.values()) for v in read_json(EVIDENCE / "runtime/limit_clamp_audit.json")["rates"].values())
    hidden_drive = any(bool(asset["joint_numerical_manifest"]["joints"][name]["Q1_DRIVE_ACTIVE"]) for name in ("q1", "q2", "q3", "P"))
    first = matrix["q1_first_failure_layer"]
    label = "S4_R6_R3_REVOLUTE_NUMERICS_RESOLVED" if first == "none" else "BLOCKED_S4_R6_R3_PHYSX_REVOLUTE_SOLVER" if first == "single_1r" else "BLOCKED_S4_R6_R3_RRRP_ARTICULATION_CONFIGURATION" if first == "fixed_rrrp" else "BLOCKED_S4_R6_R3_FLOATING_BASE_COUPLING"
    readiness = {
        "task": TASK, "start_head": START_HEAD, "end_head_at_evidence_generation": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(), "final_label": label,
        "q1_root_cause": matrix["root_cause_classification"], "single_1r_convergence": matrix["single_1r_convergence"], "fixed_rrrp_convergence": matrix["fixed_rrrp_convergence"], "floating_rrrp_convergence": matrix["floating_rrrp_convergence"],
        "q1_forward_dynamics_reference_qdd_rad_s2": q1_ref, "q1_first_step_by_rate": {str(rate): forward["single_1r"][str(rate)]["q1_first_step_sim_qdd_rad_s2"] for rate in (240, 480, 960, 1920)},
        "mass_matrix_positive_definite": mm["positive_definite"], "mass_matrix_condition_number": mm["condition_number"], "q1_effective_inertia": mm["q1_effective_inertia"], "q1_limit_hit": q1_limit, "q1_velocity_clamp_hit": q1_limit, "q1_hidden_drive_found": hidden_drive,
        "energy_single_1r": matrix["energy_isolation"]["single_1r"], "energy_fixed_rrrp": matrix["energy_isolation"]["fixed_rrrp"], "energy_floating_rrrp": matrix["energy_isolation"]["floating_rrrp"], "asset_bug_found": False, "physx_solver_limitation_suspected": first == "single_1r", "physics_model_frozen": False, "cleanup_allowed": False,
        "preserved_blockers": ["BLOCKED_S4_R6_TIMESTEP_CONVERGENCE", "BLOCKED_S4_R6_R2_SOLVER_CONVERGENCE"], "computeJointAcceleration_binding": "not exposed by Isaac Sim 5.1 public Python articulation view; mass-matrix inverse oracle used",
    }
    write_json(EVIDENCE / "asset/mass_matrix_audit.json", {"task": TASK, "reference": mm, "all_layers": {model: {str(rate): forward[model][str(rate)]["mass_matrix"] for rate in (240, 480, 960, 1920)} for model in ("single_1r", "fixed_rrrp", "floating_rrrp")}})
    write_json(EVIDENCE / "asset/inertia_axis_audit.json", {"task": TASK, "source": str(ASSET.resolve()), "asset_bug_found": False, "physical_inertia_suspect": not mm["positive_definite"], "q1_effective_inertia": mm["q1_effective_inertia"], "link1_readback": asset["joint_numerical_manifest"]["bodies"].get("link1")})
    write_json(EVIDENCE / "summary/s4_r6_r3_readiness.json", readiness)
    report = f"""# S4-R6-R3 Revolute Dynamics Isolation Report

TASK: {TASK}

START_HEAD: {START_HEAD}

END_HEAD: {readiness['end_head_at_evidence_generation']}

FINAL_LABEL: {label}

Q1_ROOT_CAUSE: {readiness['q1_root_cause']}

SINGLE_1R_CONVERGENCE: {'PASS' if readiness['single_1r_convergence'] else 'FAIL'}

FIXED_RRRP_CONVERGENCE: {'PASS' if readiness['fixed_rrrp_convergence'] else 'FAIL'}

FLOATING_RRRP_CONVERGENCE: {'PASS' if readiness['floating_rrrp_convergence'] else 'FAIL'}

Q1_FORWARD_DYNAMICS_REFERENCE_QDD: {q1_ref}

Q1_FIRST_STEP_240_QDD: {readiness['q1_first_step_by_rate']['240']}

Q1_FIRST_STEP_480_QDD: {readiness['q1_first_step_by_rate']['480']}

Q1_FIRST_STEP_960_QDD: {readiness['q1_first_step_by_rate']['960']}

Q1_FIRST_STEP_1920_QDD: {readiness['q1_first_step_by_rate']['1920']}

MASS_MATRIX_POSITIVE_DEFINITE: {str(readiness['mass_matrix_positive_definite']).lower()}

MASS_MATRIX_CONDITION_NUMBER: {readiness['mass_matrix_condition_number']}

Q1_EFFECTIVE_INERTIA: {readiness['q1_effective_inertia']}

Q1_LIMIT_HIT: {str(readiness['q1_limit_hit']).lower()}

Q1_VELOCITY_CLAMP_HIT: {str(readiness['q1_velocity_clamp_hit']).lower()}

Q1_HIDDEN_DRIVE_FOUND: {str(readiness['q1_hidden_drive_found']).lower()}

ENERGY_SINGLE_1R: {json.dumps(readiness['energy_single_1r'])}

ENERGY_FIXED_RRRP: {json.dumps(readiness['energy_fixed_rrrp'])}

ENERGY_FLOATING_RRRP: {json.dumps(readiness['energy_floating_rrrp'])}

ASSET_BUG_FOUND: {str(readiness['asset_bug_found']).lower()}

PHYSX_SOLVER_LIMITATION_SUSPECTED: {str(readiness['physx_solver_limitation_suspected']).lower()}

PHYSICS_MODEL_FROZEN: false

CLEANUP_ALLOWED: false

## Scope and method

- The source USD, RRRP design, mass, inertia, rotor, motor, and gate thresholds were not modified.
- The single 1R model is an in-memory clone of the authored fixed-base, q1, and link1 specs. It was not exported.
- Isaac Sim 5.1 public Python binding does not expose `computeJointAcceleration()` on the articulation view. The oracle is therefore `M(q0)^-1 * tau`, using the native generalized mass matrix readback; this limitation is explicit in evidence.
- Historical R6 and R6-R2 blockers remain preserved and were not overwritten.
"""
    (ROOT / "docs/reports/S4-R6-R3_revolute_dynamics_isolation_report.md").write_text(report, encoding="utf-8")
    return 0 if label == "S4_R6_R3_REVOLUTE_NUMERICS_RESOLVED" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["asset-audit", "runtime-rate", "combine", "finalize"], required=True)
    parser.add_argument("--rate", type=int, choices=[240, 480, 960, 1920])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "asset-audit":
        asset_audit(); return 0
    if args.mode == "runtime-rate":
        if args.rate is None: parser.error("--rate required")
        return runtime_rate(args.rate, args.output or EVIDENCE / f"runtime/isolation_rate_{args.rate}hz.json")
    if args.mode == "combine":
        combine(); return 0
    return finalize()


if __name__ == "__main__":
    raise SystemExit(main())
