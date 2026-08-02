#!/usr/bin/env python3
"""Blackwell/CUDA hard-gate probe for the isolated GPU environment."""
from __future__ import annotations

import argparse
import json
import time
import warnings
from pathlib import Path

import torch


def timed(fn, repeat=100):
    for _ in range(10):
        torch.cuda.synchronize()
        fn()
        torch.cuda.synchronize()
    samples = []
    for _ in range(repeat):
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        value = fn()
        torch.cuda.synchronize()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return {"median_ms": sorted(samples)[len(samples) // 2], "min_ms": min(samples), "max_ms": max(samples), "samples": samples}


def finite_tensor(x):
    return bool(torch.isfinite(x).all().item())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-json", required=True)
    args = ap.parse_args()
    result = {
        "python_version": __import__("sys").version,
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "cuda_available": bool(torch.cuda.is_available()),
        "device_count": torch.cuda.device_count(),
        "arch_list": list(torch.cuda.get_arch_list()) if torch.cuda.is_available() else [],
        "warnings": [],
        "steps": {},
    }
    if not torch.cuda.is_available() or torch.cuda.device_count() < 1:
        result["error"] = "CUDA unavailable"
    else:
        dev = torch.device("cuda:0")
        props = torch.cuda.get_device_properties(dev)
        result.update({
            "device_name": torch.cuda.get_device_name(dev),
            "capability": list(torch.cuda.get_device_capability(dev)),
            "cudnn_version": torch.backends.cudnn.version(),
            "total_memory_bytes": props.total_memory,
            "free_memory_bytes_before": torch.cuda.mem_get_info(dev)[0],
            "device_properties": {"major": props.major, "minor": props.minor, "multi_processor_count": props.multi_processor_count},
        })
        x = torch.randn((1024, 1024), device=dev, dtype=torch.float32)
        y = torch.randn((1024, 1024), device=dev, dtype=torch.float32)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            z = x @ y
        result["steps"]["tensor"] = {"success": True, "finite": finite_tensor(x), "device": str(x.device)}
        result["steps"]["matmul"] = {"success": True, "finite": finite_tensor(z), "timing": timed(lambda: x @ y)}
        model = torch.nn.Linear(64, 32, device=dev, dtype=torch.float32)
        inp = torch.randn((96, 64), device=dev, dtype=torch.float32, requires_grad=True)
        out = model(inp)
        result["steps"]["nn"] = {"success": True, "finite": finite_tensor(out), "device": str(out.device)}
        def backward():
            model.zero_grad(set_to_none=True)
            inp.grad = None
            value = model(inp).square().mean()
            value.backward()
            return value
        loss = backward()
        result["steps"]["autograd"] = {"success": True, "finite_loss": finite_tensor(loss), "finite_grad": all(p.grad is not None and finite_tensor(p.grad) for p in model.parameters()), "timing": timed(backward)}
        result["peak_memory_bytes"] = torch.cuda.max_memory_allocated(dev)
        result["warnings"] = [str(w.message) for w in caught]
        del x, y, z, model, inp
        torch.cuda.empty_cache()
    result["hard_gate_pass"] = bool(
        result.get("torch_version", "").startswith("2.7.1")
        and str(result.get("torch_cuda_version")) == "12.8"
        and result.get("cuda_available") is True
        and result.get("device_name") == "NVIDIA GeForce RTX 5060 Ti"
        and result.get("capability") == [12, 0]
        and all(v.get("success") and all(v.get(k, True) for k in ("finite", "finite_loss", "finite_grad")) for v in result.get("steps", {}).values())
    )
    out = Path(args.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
