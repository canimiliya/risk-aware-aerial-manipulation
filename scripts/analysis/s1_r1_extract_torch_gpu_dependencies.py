#!/usr/bin/env python3
"""Extract the exact Linux/Python 3.9 requirements from the installed Torch METADATA."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import platform
import re
from pathlib import Path

try:
    from packaging.requirements import Requirement
    from packaging.markers import default_environment
except ImportError:  # pragma: no cover - packaging is present in the probe env
    Requirement = None


EXPECTED = {
    "nvidia-cuda-nvrtc-cu12": "12.8.61",
    "nvidia-cuda-runtime-cu12": "12.8.57",
    "nvidia-cuda-cupti-cu12": "12.8.57",
    "nvidia-cudnn-cu12": "9.7.1.26",
    "nvidia-cublas-cu12": "12.8.3.14",
    "nvidia-cufft-cu12": "11.3.3.41",
    "nvidia-curand-cu12": "10.3.9.55",
    "nvidia-cusolver-cu12": "11.7.2.55",
    "nvidia-cusparse-cu12": "12.5.7.53",
    "nvidia-cusparselt-cu12": "0.6.3",
    "nvidia-nccl-cu12": "2.26.2",
    "nvidia-nvtx-cu12": "12.8.55",
    "nvidia-nvjitlink-cu12": "12.8.61",
    "nvidia-cufile-cu12": "1.13.0.11",
    "triton": "3.3.1",
}


def parse_requirement(raw: str) -> dict[str, object] | None:
    text = raw.strip()
    if not text:
        return None
    if Requirement is not None:
        req = Requirement(text)
        env = default_environment()
        env.update({"python_version": "3.9", "platform_system": "Linux", "platform_machine": "x86_64", "extra": ""})
        included = not req.marker or req.marker.evaluate(env)
        version = None
        exact = re.search(r"(?:==|===)\s*([^,\s]+)", str(req.specifier))
        if exact:
            version = exact.group(1)
        if version is None and included:
            try:
                version = metadata.version(req.name)
            except metadata.PackageNotFoundError:
                version = None
        return {"raw": text, "name": req.name, "specifier": str(req.specifier), "marker": str(req.marker or ""), "version": version, "included": included}
    # Torch's METADATA uses PEP 508 requirements.  Keep the fallback parser
    # deliberately small and evaluate only the markers relevant to this gate.
    base, _, marker = text.partition(";")
    match = re.match(r"^([A-Za-z0-9_.-]+)\s*(.*)$", base.strip())
    if not match:
        return {"raw": text, "included": False, "reason": "unparsed"}
    name, specifier = match.groups()
    marker = marker.strip()
    valid = not marker or all(token not in marker for token in ("sys_platform", "win32", "darwin"))
    if "python_version" in marker:
        valid = valid and ("3.9" in marker or "<3.10" in marker or ">=3.9" in marker)
    if "platform_machine" in marker:
        valid = valid and ("x86_64" in marker or "amd64" in marker)
    if not valid:
        return {"raw": text, "name": name, "specifier": specifier or "", "marker": marker, "included": False}
    exact = None
    if specifier:
        m = re.search(r"(?:==|===)\s*([^,\s]+)", specifier)
        exact = m.group(1) if m else None
    if exact is None and valid:
        try:
            exact = metadata.version(name)
        except metadata.PackageNotFoundError:
            pass
    return {"raw": text, "name": name, "specifier": specifier or "", "marker": marker, "version": exact, "included": valid}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    dist = metadata.distribution("torch")
    meta_text = dist.read_text("METADATA") or ""
    requires = metadata.requires("torch") or []
    parsed = [item for raw in requires if (item := parse_requirement(raw)) is not None]
    included = [item for item in parsed if item.get("included")]
    drift = []
    for item in included:
        name = str(item.get("name", "")).lower().replace("_", "-")
        expected = EXPECTED.get(name)
        if expected and item.get("version") != expected:
            drift.append({"name": name, "metadata_version": item.get("version"), "expected": expected})
    lock_lines = [
        f"{item['name']}=={item['version']}"
        for item in sorted(included, key=lambda x: str(x.get("name", "")).lower())
        if item.get("version")
    ]
    lock = "\n".join(lock_lines) + "\n"
    (out / "torch_metadata.txt").write_text(meta_text, encoding="utf-8")
    (out / "gpu_runtime_lock.txt").write_text(lock, encoding="utf-8")
    payload = {
        "torch_version": dist.version,
        "python": platform.python_version(),
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "requirements_raw": requires,
        "requirements": parsed,
        "included_count": len(lock_lines),
        "expected_dependency_drift": drift,
        "lock": lock_lines,
    }
    (out / "gpu_runtime_lock.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = hashlib.sha256(lock.encode()).hexdigest()
    (out / "gpu_runtime_lock_sha256.txt").write_text(digest + "\n", encoding="utf-8")
    print(json.dumps({"torch": dist.version, "included": len(lock_lines), "drift": drift, "sha256": digest}, indent=2))
    return 2 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
