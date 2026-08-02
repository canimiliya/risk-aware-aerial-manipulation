from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def plot_workspace(npz_path: Path, output: Path) -> None:
    import matplotlib.pyplot as plt

    data = np.load(npz_path)
    positions = data["position"]
    valid = data["valid"]
    points = positions[valid]
    if len(points) > 20_000:
        points = points[:: max(1, len(points) // 20_000)]
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=1, alpha=0.12, c=points[:, 2], cmap="viridis")
    ax.set_xlabel("E x [m]")
    ax.set_ylabel("E y [m]")
    ax.set_zlabel("E z [m]")
    ax.set_title("S2-R0 official Delta FK workspace preflight")
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot_workspace(args.npz, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
