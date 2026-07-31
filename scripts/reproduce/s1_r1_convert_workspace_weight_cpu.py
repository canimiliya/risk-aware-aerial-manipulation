#!/usr/bin/env python3
"""Create and verify an out-of-tree CPU checkpoint copy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import torch


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_state_dict(state):
    if not isinstance(state, dict):
        raise TypeError(f"expected state dict, received {type(state).__name__}")
    tensors = [(key, value) for key, value in state.items() if isinstance(value, torch.Tensor)]
    if len(tensors) != len(state) or not tensors:
        raise ValueError("state dict must contain only at least one tensor")
    if any(value.device.type != "cpu" for _, value in tensors):
        raise ValueError("all tensors must be on CPU")
    if not all(torch.isfinite(value).all().item() for _, value in tensors):
        raise ValueError("all tensors must be finite")
    if not any(torch.count_nonzero(value).item() for _, value in tensors):
        raise ValueError("at least one tensor must be nonzero")
    return tensors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--converted", required=True, type=Path)
    parser.add_argument("--json-out", required=True, type=Path)
    parser.add_argument("--text-out", required=True, type=Path)
    args = parser.parse_args()
    original = args.original.resolve(); converted = args.converted.resolve()
    before = torch.load(original, map_location="cpu")
    original_tensors = verify_state_dict(before)
    converted.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=converted.parent, prefix=converted.name + ".", delete=False) as handle:
        temporary = Path(handle.name)
        torch.save(before, handle)
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, converted)
    after = torch.load(converted, map_location="cpu")
    converted_tensors = verify_state_dict(after)
    keys_equal = list(before.keys()) == list(after.keys())
    tensors_equal = keys_equal and len(original_tensors) == len(converted_tensors) and all(
        left.shape == right.shape and left.dtype == right.dtype and torch.equal(left, right)
        for (_, left), (_, right) in zip(original_tensors, converted_tensors))
    result = {"original": {"path": str(original), "bytes": original.stat().st_size, "sha256": sha256(original)},
              "converted": {"path": str(converted), "bytes": converted.stat().st_size, "sha256": sha256(converted)},
              "key_order_equal": keys_equal, "tensor_count": len(original_tensors), "tensor_values_equal": tensors_equal,
              "all_cpu": True, "all_finite": True, "has_nonzero_tensor": True}
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.text_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not tensors_equal: raise SystemExit(1)


if __name__ == "__main__": main()
