#!/usr/bin/env python3
"""Resolve exact official wheel URLs, sizes and SHA-256 values for a lock file."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ALLOWED = {"download.pytorch.org", "download-r2.pytorch.org", "pypi.org", "files.pythonhosted.org"}
PYTORCH_INDEX = "https://download.pytorch.org/whl/cu128/"


def get(url: str) -> bytes:
    host = urllib.parse.urlparse(url).hostname
    if host not in ALLOWED:
        raise RuntimeError(f"disallowed host: {host}")
    req = urllib.request.Request(url, headers={"User-Agent": "s1-r1-gpu-preflight/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def pypi_candidate(name: str, version: str) -> tuple[str, int | None, str | None]:
    data = json.loads(get(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/{urllib.parse.quote(version)}/json"))
    candidates = []
    for item in data.get("urls", []):
        filename = item.get("filename", "")
        if filename.endswith(".whl") and (("manylinux" in filename or "linux" in filename) and ("x86_64" in filename or "amd64" in filename) or "none-any" in filename):
            candidates.append(item)
    if not candidates:
        raise RuntimeError(f"no Linux x86_64 wheel in PyPI JSON for {name}=={version}")
    item = sorted(candidates, key=lambda x: ("cp39" not in x["filename"], x["filename"]))[0]
    return item["url"], item.get("size"), (item.get("digests") or {}).get("sha256")


def pytorch_candidate(name: str, version: str) -> tuple[str, int | None, str | None] | None:
    index = get(PYTORCH_INDEX).decode("utf-8", errors="replace")
    stem = name.replace("-", "_")
    pattern = re.compile(r'href=["\']([^"\']*' + re.escape(stem) + r'[^"\']+\.whl(?:#[^"\']*)?)["\']', re.I)
    hits = []
    for raw in pattern.findall(index):
        href = html.unescape(raw)
        parsed = urllib.parse.urlparse(href)
        filename = Path(parsed.path).name
        if version not in filename or not ("manylinux" in filename or "linux" in filename) or not ("x86_64" in filename or "amd64" in filename):
            continue
        digest = urllib.parse.parse_qs(parsed.fragment).get("sha256", [None])[0]
        url = urllib.parse.urljoin(PYTORCH_INDEX, parsed.path)
        hits.append((url, None, digest))
    return sorted(hits, key=lambda x: ("cp39" not in x[0], x[0]))[0] if hits else None


def head_size(url: str) -> int | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "s1-r1-gpu-preflight/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            value = response.headers.get("Content-Length")
            return int(value) if value else None
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lock", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    failures = []
    for line in args.lock.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, version = line.strip().split("==", 1)
        candidate = pytorch_candidate(name, version) if name.lower().startswith("nvidia-") or name.lower() == "triton" else None
        source = "download.pytorch.org"
        if candidate is None:
            try:
                candidate = pypi_candidate(name, version)
                source = urllib.parse.urlparse(candidate[0]).hostname
            except Exception as exc:
                failures.append({"name": name, "version": version, "error": str(exc)})
                continue
        url, size, sha = candidate
        size = size or head_size(url)
        filename = Path(urllib.parse.urlparse(url).path).name
        rows.append({"name": name, "version": version, "filename": filename, "url": url, "source_domain": source, "size": size, "sha256": sha, "platform": "linux-x86_64"})
        if not sha or not size:
            failures.append({"name": name, "version": version, "error": "missing official size or sha256", "url": url})
    payload = {"allowed_domains": sorted(ALLOWED), "torch_index": PYTORCH_INDEX, "rows": rows, "failures": failures}
    (out / "official_wheel_manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = ["# Official GPU wheel manifest", "", f"Rows: {len(rows)}", f"Failures: {len(failures)}", "", "| package | filename | bytes | sha256 | source |", "|---|---|---:|---|---|"]
    md.extend(f"| {r['name']}=={r['version']} | {r['filename']} | {r['size']} | `{r['sha256']}` | {r['source_domain']} |" for r in rows)
    if failures:
        md.extend(["", "## Failures", "", "```json", json.dumps(failures, indent=2), "```"])
    (out / "official_wheel_manifest.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "failures": len(failures)}, indent=2))
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
