#!/usr/bin/env python3
"""Inventory candidate wheel/partial files without deleting anything."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def inspect(path: Path) -> dict:
    row = {"path": str(path), "name": path.name, "bytes": path.stat().st_size, "sha256": None, "zip_complete": False, "dist_info": None, "wheel_tag": None, "kind": "part" if path.name.endswith(".part") else "file"}
    if path.is_file():
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(block)
        row["sha256"] = h.hexdigest()
        if path.suffix == ".whl":
            try:
                with zipfile.ZipFile(path) as zf:
                    bad = zf.testzip()
                    row["zip_complete"] = bad is None
                    infos = [n for n in zf.namelist() if n.endswith(".dist-info/WHEEL")]
                    if infos:
                        text = zf.read(infos[0]).decode("utf-8", errors="replace")
                        row["dist_info"] = infos[0].split("/")[0]
                        row["wheel_tag"] = [line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("Tag:")]
            except zipfile.BadZipFile:
                row["zip_complete"] = False
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("paths", nargs="+", type=Path)
    args = ap.parse_args()
    rows = []
    for root in args.paths:
        if root.exists():
            files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
            rows.extend(inspect(p) for p in files if p.is_file())
    payload = {"roots": [str(p) for p in args.paths], "rows": rows}
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "wheel_inventory_before.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Wheel inventory before recovery", "", f"Files: {len(rows)}", "", "| file | bytes | sha256 | zip complete | kind |", "|---|---:|---|---|---|"]
    lines.extend(f"| `{r['path']}` | {r['bytes']} | `{r['sha256']}` | {r['zip_complete']} | {r['kind']} |" for r in rows)
    (out / "wheel_inventory_before.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
