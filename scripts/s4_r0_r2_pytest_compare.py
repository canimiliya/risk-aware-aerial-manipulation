"""Create a byte-backed base/head pytest comparison for R2."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_LOG = Path(r"C:/s4r0b/base_pytest.log")
HEAD_LOG = ROOT / "outputs/s4_r0_r2_head_pytest.log"
OUT_JSON = ROOT / "docs/evidence/S4-R0/tests/base_vs_head_pytest.json"
OUT_MD = ROOT / "docs/evidence/S4-R0/tests/base_vs_head_pytest.md"


def parse(path: Path) -> dict[str, object]:
    if path.is_file():
        raw = path.read_bytes()
        text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8", errors="replace")
    else:
        text = ""
    failed = []
    for line in text.splitlines():
        match = re.search(r"FAILED (.+?)(?: - .*)?$", line)
        if match:
            failed.append(match.group(1).strip())
    passed_match = re.search(r"(\d+) passed", text)
    failed_match = re.search(r"(\d+) failed", text)
    duration_match = re.search(r"in ([0-9.]+s(?: \([^)]*\))?)", text)
    return {"log_path": str(path.resolve()), "log_exists": path.is_file(), "passed": int(passed_match.group(1)) if passed_match else None, "failed": int(failed_match.group(1)) if failed_match else 0, "duration": duration_match.group(1) if duration_match else None, "failed_nodes": failed}


def main() -> int:
    base = parse(BASE_LOG)
    head = parse(HEAD_LOG)
    base_failed = set(base["failed_nodes"])
    head_failed = set(head["failed_nodes"])
    payload = {"base_commit": "741dd82e823420e0d8b272c9f06ed81b0b757183", "head_commit": "f268ea800a93c1e82e4bb303b3ee27fa51ab80ab", "environment": "D:/i3/e/python.exe, same repository test command pytest -q", "base": base, "head": head, "common_failures": sorted(base_failed & head_failed), "head_only_failures": sorted(head_failed - base_failed), "base_only_failures": sorted(base_failed - head_failed), "hard_gate_head_only_failures_zero": len(head_failed - base_failed) == 0}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# S4-R0-R2 base/head pytest comparison", "", f"Environment: `{payload['environment']}`", "", "| Revision | Passed | Failed |", "|---|---:|---:|"]
    lines.append(f"| base `{payload['base_commit'][:8]}` | {base['passed']} | {base['failed']} |")
    lines.append(f"| head `{payload['head_commit'][:8]}` | {head['passed']} | {head['failed']} |")
    lines += ["", f"Head-only failures: `{len(payload['head_only_failures'])}`", f"Common failures: `{len(payload['common_failures'])}`", f"Base-only failures: `{len(payload['base_only_failures'])}`", "", "## Failed node IDs", "", "### Common"]
    lines += [f"- `{item}`" for item in payload["common_failures"]] or ["- none"]
    lines += ["", "### Head-only", *([f"- `{item}`" for item in payload["head_only_failures"]] or ["- none"]), "", "### Base-only", *([f"- `{item}`" for item in payload["base_only_failures"]] or ["- none"]), ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"base": [base["passed"], base["failed"]], "head": [head["passed"], head["failed"]], "head_only_failures": len(payload["head_only_failures"])}, ensure_ascii=False), flush=True)
    return 0 if payload["hard_gate_head_only_failures_zero"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
