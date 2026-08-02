#!/usr/bin/env python3
"""Verify a manifest-backed wheelhouse before offline installation."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--wheelhouse", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows, problems = [], []
    expected = {r["filename"]: r for r in manifest.get("rows", [])}
    for row in manifest.get("rows", []):
        path = args.wheelhouse / row["filename"]
        item = {"name": row["name"], "version": row["version"], "filename": row["filename"], "path": str(path), "expected_bytes": row["size"], "expected_sha256": row["sha256"]}
        if not path.exists():
            item["status"] = "missing"; problems.append(item); rows.append(item); continue
        item["bytes"] = path.stat().st_size
        item["sha256"] = sha(path)
        item["zip_complete"] = False
        try:
            with zipfile.ZipFile(path) as zf:
                item["zip_complete"] = zf.testzip() is None
        except zipfile.BadZipFile:
            pass
        item["status"] = "ok" if item["bytes"] == row["size"] and item["sha256"] == row["sha256"] and item["zip_complete"] else "invalid"
        if item["status"] != "ok": problems.append(item)
        rows.append(item)
    unknown = [str(p) for p in args.wheelhouse.iterdir() if p.is_file() and p.name not in expected and not p.name.endswith((".log", ".txt", ".jsonl"))]
    payload = {"expected_count": len(expected), "rows": rows, "missing": sum(r["status"] == "missing" for r in rows), "corrupt_or_mismatch": sum(r["status"] == "invalid" for r in rows), "unknown": unknown}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "wheel_inventory_after.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = ["# GPU wheelhouse verification", "", f"Expected: {payload['expected_count']}", f"Missing: {payload['missing']}", f"Corrupt or hash mismatch: {payload['corrupt_or_mismatch']}", f"Unknown files: {len(unknown)}", "", "| wheel | bytes | sha256 | zip | status |", "|---|---:|---|---|---|"]
    md.extend(f"| {r['filename']} | {r.get('bytes')} | `{r.get('sha256')}` | {r.get('zip_complete')} | {r['status']} |" for r in rows)
    if unknown: md.extend(["", "Unknown files:", ""] + [f"- `{x}`" for x in unknown])
    (args.out_dir / "wheelhouse_verification.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("expected_count", "missing", "corrupt_or_mismatch", "unknown")}, indent=2))
    return 0 if payload["missing"] == 0 and payload["corrupt_or_mismatch"] == 0 and len(payload["unknown"]) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
