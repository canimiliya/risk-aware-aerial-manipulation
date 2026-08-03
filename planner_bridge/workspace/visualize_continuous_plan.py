from __future__ import annotations

import argparse
import json
from pathlib import Path


def plot_plan(input_path: Path, output_path: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    data = json.loads(input_path.read_text(encoding="utf-8"))
    samples = data["samples"]
    positions = np.asarray([item["position_A0_m"] for item in samples], dtype=float)
    q = np.asarray([item["q_rad"] for item in samples], dtype=float)
    clearance = np.asarray([item["clearance_m"] for item in samples], dtype=float)
    fig = plt.figure(figsize=(10, 6))
    ax3d = fig.add_subplot(121, projection="3d")
    ax3d.plot(positions[:, 0], positions[:, 1], positions[:, 2], color="#1565c0", linewidth=1.5)
    ax3d.scatter(positions[[0, -1], 0], positions[[0, -1], 1], positions[[0, -1], 2], c=["#2e7d32", "#c62828"], s=24)
    ax3d.set_xlabel("E x [m]")
    ax3d.set_ylabel("E y [m]")
    ax3d.set_zlabel("E z [m]")
    ax3d.set_title("S2-R1 continuous end-effector path")
    ax = fig.add_subplot(122)
    ax.plot(q, linewidth=1.0)
    ax.set_xlabel("sample")
    ax.set_ylabel("joint angle [rad]")
    ax2 = ax.twinx()
    ax2.plot(clearance, color="#d84315", linewidth=1.0, alpha=0.8)
    ax2.axhline(0.010, color="#d84315", linestyle="--", linewidth=0.8)
    ax2.set_ylabel("minimum proxy clearance [m]")
    ax.set_title("whole-body state contract: fixed W→B + Delta q")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot_plan(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
