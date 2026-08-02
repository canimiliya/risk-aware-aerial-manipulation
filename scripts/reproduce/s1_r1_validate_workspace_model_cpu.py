#!/usr/bin/env python3
"""Strict CPU validation for the model architecture embedded in AM-Planner."""
import argparse
import json
from pathlib import Path
import torch
import torch.nn as nn

class WorkspaceMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(nn.Linear(3, 64), nn.LeakyReLU(0.01), nn.Linear(64, 256), nn.LeakyReLU(0.01), nn.Linear(256, 128), nn.LeakyReLU(0.01), nn.Linear(128, 64), nn.LeakyReLU(0.01), nn.Linear(64, 1), nn.Sigmoid())
    def forward(self, value): return self.network(value)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--weight", required=True, type=Path); parser.add_argument("--json-out", required=True, type=Path); args = parser.parse_args()
    torch.manual_seed(20260731)
    model = WorkspaceMLP().cpu(); model.load_state_dict(torch.load(args.weight, map_location="cpu"), strict=True); model.eval()
    value = torch.randn(8, 3, requires_grad=True); first = model(value); first.sum().backward(); gradient = value.grad
    with torch.no_grad(): second = model(value.detach())
    result = {"strict_load": True, "eval": not model.training, "input_shape": list(value.shape), "output_shape": list(first.shape),
              "output_finite": bool(torch.isfinite(first).all()), "gradient_finite": bool(torch.isfinite(gradient).all()),
              "sigmoid_range": bool(((first >= 0) & (first <= 1)).all()), "repeatable": bool(torch.equal(first.detach(), second)),
              "output_min": float(first.min()), "output_max": float(first.max())}
    args.json_out.parent.mkdir(parents=True, exist_ok=True); args.json_out.write_text(json.dumps(result, indent=2) + "\n")
    if not all(result[key] for key in ["strict_load", "eval", "output_finite", "gradient_finite", "sigmoid_range", "repeatable"]): raise SystemExit(1)
if __name__ == "__main__": main()
