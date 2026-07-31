#!/usr/bin/env python3
"""CPU-only microbenchmark of the verified workspace model architecture."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import torch


class WorkspaceModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.network = torch.nn.Sequential(
            torch.nn.Linear(3, 64), torch.nn.LeakyReLU(),
            torch.nn.Linear(64, 256), torch.nn.LeakyReLU(),
            torch.nn.Linear(256, 128), torch.nn.LeakyReLU(),
            torch.nn.Linear(128, 64), torch.nn.LeakyReLU(),
            torch.nn.Linear(64, 1), torch.nn.Sigmoid(),
        )

    def forward(self, x):
        return self.network(x)


def measure(fn, warmup=20, iterations=100):
    for _ in range(warmup):
        result = fn()
        if isinstance(result, torch.Tensor) and result.requires_grad:
            result.sum().backward()
    samples = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = fn()
        if isinstance(result, torch.Tensor) and result.requires_grad:
            result.sum().backward()
        samples.append((time.perf_counter() - start) * 1000.0)
    ordered = sorted(samples)
    return {"median_ms": statistics.median(samples), "p90_ms": ordered[int(0.90 * (len(ordered) - 1))], "p99_ms": ordered[int(0.99 * (len(ordered) - 1))], "samples": len(samples)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    torch.set_num_threads(max(1, torch.get_num_threads()))
    model = WorkspaceModel().cpu().eval()
    state = torch.load(args.weight, map_location="cpu")
    model.load_state_dict(state, strict=True)
    rows = []
    for batch in [1, 96, 192, 576, 960]:
        x = torch.linspace(-1.0, 1.0, batch * 3, dtype=torch.float32).reshape(batch, 3)
        x_grad = x.clone().requires_grad_(True)
        with torch.no_grad():
            forward = measure(lambda: model(x))
        autograd = measure(lambda: model(x_grad))
        rows.append({"batch": batch, "forward": forward, "forward_autograd": autograd})
    data = {"torch_version": torch.__version__, "cuda_available": bool(torch.cuda.is_available()), "torch_num_threads": torch.get_num_threads(), "architecture": "3-64-256-128-64-1 LeakyReLU Sigmoid", "rows": rows}
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "workspace_model_cpu_benchmark.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = ["# workspace 模型 CPU 微基准", "", f"Torch `{torch.__version__}`，CUDA={torch.cuda.is_available()}，线程数={torch.get_num_threads()}。预热20次，正式100次。", "", "|batch|forward median/p90/p99 ms|forward+autograd median/p90/p99 ms|", "|---:|---|---|"]
    for row in rows:
        f, a = row["forward"], row["forward_autograd"]
        lines.append(f"|{row['batch']}|{f['median_ms']:.3f}/{f['p90_ms']:.3f}/{f['p99_ms']:.3f}|{a['median_ms']:.3f}/{a['p90_ms']:.3f}/{a['p99_ms']:.3f}|")
    (out / "workspace_model_cpu_benchmark.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
