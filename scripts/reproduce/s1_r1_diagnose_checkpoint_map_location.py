#!/usr/bin/env python3
"""Prove the checkpoint map_location calling convention without changing AM-Planner."""
import argparse
import hashlib
import json
from pathlib import Path

import torch


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def describe(value):
    tensors = [tensor for tensor in value.values() if isinstance(tensor, torch.Tensor)] if isinstance(value, dict) else []
    return {
        "object_type": type(value).__name__, "key_count": len(value) if isinstance(value, dict) else None,
        "tensor_count": len(tensors), "all_finite": all(torch.isfinite(t).all().item() for t in tensors),
        "has_nonzero_tensor": any(torch.count_nonzero(t).item() > 0 for t in tensors),
    }


def attempt(name, func):
    try:
        return {"name": name, "success": True, "result": describe(func())}
    except Exception as error:  # The exception is the expected first result.
        return {"name": name, "success": False, "error_type": type(error).__name__, "error": str(error)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", required=True, type=Path)
    parser.add_argument("--json-out", required=True, type=Path)
    parser.add_argument("--text-out", required=True, type=Path)
    args = parser.parse_args()
    path = args.weight.resolve()
    malformed = attempt("positional_dict", lambda: torch.load(path, {"map_location": "cpu"}))
    keyword = attempt("keyword_map_location", lambda: torch.load(path, map_location="cpu"))
    result = {"torch_version": torch.__version__, "cuda_available": torch.cuda.is_available(),
              "weight_path": str(path), "weight_bytes": path.stat().st_size, "weight_sha256": sha256(path),
              "positional_dict": malformed, "keyword_map_location": keyword,
              "root_cause_confirmed": (not malformed["success"] and keyword["success"])}
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.text_out.write_text("\n".join([
        f"torch={result['torch_version']} cuda_available={result['cuda_available']}",
        f"weight={path} bytes={result['weight_bytes']} sha256={result['weight_sha256']}",
        f"positional_dict success={malformed['success']} detail={malformed.get('error', malformed.get('result'))}",
        f"keyword_map_location success={keyword['success']} detail={keyword.get('error', keyword.get('result'))}",
        f"root_cause_confirmed={result['root_cause_confirmed']}",
    ]) + "\n", encoding="utf-8")
    if not result["root_cause_confirmed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
