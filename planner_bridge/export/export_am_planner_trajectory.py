"""Export preserved AM-Planner captures into the S1-R2 data contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from planner_bridge.export.sampling import EXPORTER_VERSION, load_captured_message, message_contract, sample_message, write_csv


RUNS = {
    "write_official": ("write", "write_r7r3_r1_gpu_run_02"),
    "grasp_official": ("grasp", "grasp_r7r3_r1_gpu_run_02"),
    "lift_official": ("lift", "lift_r7r3_r1_gpu_run_01"),
    "grasp_repeat": ("grasp", "grasp_r7r3_r1_gpu_run_03"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_commit(root: Path) -> str:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return result.stdout.strip() or "UNKNOWN"


def export_run(root: Path, output_root: Path, label: str, task: str, run_id: str, sample_dt: float, source_override: Path | None = None) -> Path:
    source = source_override if source_override is not None else root / "docs/evidence/S1-R1/r7r3_r1_runtime" / run_id
    destination = output_root / label
    destination.mkdir(parents=True, exist_ok=True)
    base_payload = load_captured_message(source / "trajectory.json")
    arm_payload = load_captured_message(source / "trajectory_arm.json")
    (destination / "raw_trajectory.json").write_text(json.dumps(base_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destination / "raw_trajectory_arm.json").write_text(json.dumps(arm_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    base_sampled = sample_message(base_payload, sample_dt)
    arm_sampled = sample_message(arm_payload, sample_dt)
    write_csv(destination / "sampled_trajectory.csv", base_sampled)
    write_csv(destination / "sampled_trajectory_arm.csv", arm_sampled)
    np.savez_compressed(destination / "sampled_trajectory.npz", **base_sampled)
    np.savez_compressed(destination / "sampled_trajectory_arm.npz", **arm_sampled)
    contract = message_contract(base_payload)
    metadata = {
        "task": task,
        "run_id": run_id,
        "git_commit": project_commit(root),
        "am_planner_commit": "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d",
        "message_type": base_payload["message_type"],
        "source_evidence_path": str(source).replace("\\", "/"),
        "coordinate_frame": contract["frame_id"],
        "units": {
            "time": "s (source uses ros::Duration/toSec)",
            "position": "not encoded in PolynomialTrajectory; source convention is not re-invented here",
            "yaw": "scalar with no unit annotation in message",
        },
        "sample_dt": sample_dt,
        "sample_frequency_hz": 1.0 / sample_dt,
        "segment_count": contract["num_segment"],
        "total_duration": contract["total_duration"],
        "export_time_utc": datetime.now(timezone.utc).isoformat(),
        "exporter_version": EXPORTER_VERSION,
        "base_vs_arm": "same message type and fields; topic-specific captures are preserved separately",
    }
    (destination / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destination / "validation.json").write_text(json.dumps({"status": "pending", "validator": "planner_bridge.validation.validate_exported_trajectory"}, indent=2) + "\n", encoding="utf-8")
    # validation.json is generated after the manifest and records the manifest
    # result; excluding it avoids an impossible self-referential hash.
    files = sorted(path for path in destination.iterdir() if path.is_file() and path.name not in {"sha256_manifest.txt", "validation.json"})
    manifest = "\n".join(f"{sha256(path)}  {path.name}" for path in files) + "\n"
    (destination / "sha256_manifest.txt").write_text(manifest, encoding="utf-8")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, default=Path("data/trajectories/S1-R2"))
    parser.add_argument("--sample-dt", type=float, default=0.01)
    parser.add_argument("--only", choices=sorted(RUNS), action="append")
    parser.add_argument("--variant-source", type=Path)
    parser.add_argument("--variant-label")
    parser.add_argument("--variant-task")
    parser.add_argument("--variant-run-id")
    args = parser.parse_args()
    root = args.repo.resolve()
    output_root = (root / args.output_root).resolve() if not args.output_root.is_absolute() else args.output_root
    selected = args.only or ([] if args.variant_source else list(RUNS))
    if args.variant_source:
        if not (args.variant_label and args.variant_task and args.variant_run_id):
            parser.error("--variant-source requires --variant-label, --variant-task, and --variant-run-id")
        export_run(root, output_root, args.variant_label, args.variant_task, args.variant_run_id, args.sample_dt, args.variant_source.resolve())
    outputs = []
    for label in selected:
        task, run_id = RUNS[label]
        outputs.append(str(export_run(root, output_root, label, task, run_id, args.sample_dt)))
    print(json.dumps({"exported": outputs, "sample_frequency_hz": 1.0 / args.sample_dt}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
