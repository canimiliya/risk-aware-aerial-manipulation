#!/usr/bin/env python3
"""Float32 CUDA benchmark matching the existing CPU benchmark definition."""
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
        self.network = torch.nn.Sequential(torch.nn.Linear(3, 64), torch.nn.LeakyReLU(), torch.nn.Linear(64, 256), torch.nn.LeakyReLU(), torch.nn.Linear(256, 128), torch.nn.LeakyReLU(), torch.nn.Linear(128, 64), torch.nn.LeakyReLU(), torch.nn.Linear(64, 1), torch.nn.Sigmoid())
    def forward(self, x): return self.network(x)


def stats(fn, warmup=20, iterations=100):
    for _ in range(warmup):
        torch.cuda.synchronize(); fn(); torch.cuda.synchronize()
    samples = []
    for _ in range(iterations):
        torch.cuda.synchronize(); t0 = time.perf_counter(); fn(); torch.cuda.synchronize(); samples.append((time.perf_counter() - t0) * 1000)
    ordered = sorted(samples)
    return {"median_ms": statistics.median(samples), "p90_ms": ordered[int(.90 * (len(ordered)-1))], "p99_ms": ordered[int(.99 * (len(ordered)-1))], "samples": len(samples)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--weight", required=True); ap.add_argument("--output-json", required=True); ap.add_argument("--output-md", required=True); args = ap.parse_args()
    torch.manual_seed(1234); model = WorkspaceModel().cuda().eval(); state = torch.load(args.weight, map_location="cuda"); model.load_state_dict(state, strict=True)
    rows = []
    for batch in [1, 96, 192, 576, 960]:
        x = torch.linspace(-1, 1, batch*3, device="cuda", dtype=torch.float32).reshape(batch, 3)
        x_grad = x.clone().requires_grad_(True)
        with torch.no_grad(): forward = stats(lambda: model(x))
        def backward():
            model.zero_grad(set_to_none=True); x_grad.grad = None; out = model(x_grad); out.sum().backward()
        autograd = stats(backward)
        rows.append({"batch": batch, "forward": forward, "forward_autograd": autograd, "peak_memory_bytes": torch.cuda.max_memory_allocated()})
    data = {"torch_version": torch.__version__, "torch_cuda_version": torch.version.cuda, "device": torch.cuda.get_device_name(), "capability": list(torch.cuda.get_device_capability()), "dtype": "float32", "warmup": 20, "iterations": 100, "rows": rows}
    Path(args.output_json).write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = ["# Workspace 模型 GPU 微基准", "", f"Torch `{torch.__version__}` / CUDA `{torch.version.cuda}` / `{torch.cuda.get_device_name()}` / capability `{torch.cuda.get_device_capability()}`。float32，预热20次，正式100次，同 CPU 定义。", "", "|batch|forward median/p90/p99 ms|forward+autograd median/p90/p99 ms|peak memory MB|", "|---:|---|---|---:|"]
    for row in rows:
        f,a=row["forward"],row["forward_autograd"]; lines.append(f"|{row['batch']}|{f['median_ms']:.3f}/{f['p90_ms']:.3f}/{f['p99_ms']:.3f}|{a['median_ms']:.3f}/{a['p90_ms']:.3f}/{a['p99_ms']:.3f}|{row['peak_memory_bytes']/1024/1024:.2f}|")
    Path(args.output_md).write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(data, indent=2))


if __name__ == "__main__": main()
