#!/usr/bin/env python3
"""Probe official checkpoint loading and the verified WorkspaceMLP on CUDA."""
from __future__ import annotations

import argparse
import json
import traceback
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


def inspect(obj, label):
    rows = {"label": label, "success": True, "type": type(obj).__name__}
    if isinstance(obj, dict):
        rows["key_count"] = len(obj)
        tensors = [v for v in obj.values() if isinstance(v, torch.Tensor)]
        rows["tensor_count"] = len(tensors)
        rows["devices"] = sorted({str(v.device) for v in tensors})
        rows["all_finite"] = all(bool(torch.isfinite(v).all().item()) for v in tensors if v.numel())
        rows["nonzero_count"] = int(sum(int(torch.count_nonzero(v).item()) for v in tensors))
    return rows


def attempt(label, fn):
    try:
        return inspect(fn(), label)
    except Exception as exc:  # intentional evidence capture
        return {"label": label, "success": False, "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(limit=3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weight", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--model-output-json", required=True)
    args = ap.parse_args()
    path = Path(args.weight)
    result = {"torch_version": torch.__version__, "cuda_available": bool(torch.cuda.is_available()), "weight": str(path), "load_attempts": []}
    result["load_attempts"].append(attempt("official_error_positional_dict", lambda: torch.load(str(path), {"map_location": "cuda"})))
    result["load_attempts"].append(attempt("default_load", lambda: torch.load(str(path))))
    result["load_attempts"].append(attempt("correct_map_location_cuda", lambda: torch.load(str(path), map_location="cuda")))
    model_result = {"strict_load": False, "forward": False, "autograd": False}
    try:
        state = torch.load(str(path), map_location="cuda")
        model = WorkspaceModel().to("cuda").eval()
        model.load_state_dict(state, strict=True)
        model_result["strict_load"] = True
        x = torch.linspace(-1, 1, 960 * 3, device="cuda", dtype=torch.float32).reshape(960, 3).requires_grad_(True)
        y = model(x)
        model_result.update({"forward": True, "forward_device": str(y.device), "forward_finite": bool(torch.isfinite(y).all().item())})
        y.sum().backward()
        model_result.update({"autograd": True, "autograd_finite": all(p.grad is not None and bool(torch.isfinite(p.grad).all().item()) for p in model.parameters()), "parameter_count": sum(p.numel() for p in model.parameters())})
        model_result["peak_memory_bytes"] = torch.cuda.max_memory_allocated()
    except Exception as exc:
        model_result.update({"error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(limit=5)})
    result["hard_gate_pass"] = bool(result["load_attempts"][-1].get("success") and model_result["strict_load"] and model_result["forward"] and model_result["autograd"])
    result["model"] = model_result
    out = Path(args.output_json); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path(args.model_output_json).write_text(json.dumps(model_result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
