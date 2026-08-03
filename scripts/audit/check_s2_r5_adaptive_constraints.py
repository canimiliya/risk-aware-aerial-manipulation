"""Audit S2-R5 evidence without rewriting historical acceptance records."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs/evidence/S2-R5"


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    summaries = []
    for i in range(4):
        p = EV / "rounds" / f"round_{i}/round_summary.json"
        if not p.exists():
            errors.append(f"missing round summary {i}")
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        summaries.append(d)
        if int(d["new_mode3_count"]) > 6:
            errors.append(f"round {i} added more than 6 mode3")
        if int(d["cumulative_mode3_count"]) > 25:
            errors.append(f"round {i} exceeded 25 mode3")
    if len(summaries) != 4:
        errors.append("round 0..3 evidence incomplete")
    phase = (EV / "phase_split_contract.md").read_text(encoding="utf-8") if (EV / "phase_split_contract.md").exists() else ""
    if "PHASE_SPLIT_NOT_SUPPORTED_BY_OFFICIAL_ARM_ENDPOINT_CONTRACT" not in phase:
        errors.append("phase split contract missing")
    for run in ("round_1_nominal_abi_fixed_2", "round_2_nominal", "round_3_nominal"):
        p = EV / "runtime" / run / "processes.json"
        if not p.exists() or json.loads(p.read_text(encoding="utf-8")).get("capture_exit") != 0:
            errors.append(f"runtime capture failed: {run}")
    visuals = list((EV / "visuals").glob("*.png")) if (EV / "visuals").exists() else []
    gifs = list((EV / "visuals").glob("*.gif")) if (EV / "visuals").exists() else []
    if len(visuals) < 8:
        errors.append("fewer than 8 PNG visuals")
    if len(gifs) < 2:
        errors.append("fewer than 2 local GIF visuals")
    diff = subprocess.run(["git", "diff", "--", "third_party/am-planner"], cwd=ROOT, capture_output=True, text=True, check=False)
    if diff.stdout.strip():
        errors.append("third_party/am-planner has a worktree diff")
    for forbidden in ("clip", "saturat", "project_output"):
        if forbidden in "\n".join(str(p) for p in (EV / "rounds").rglob("*.json")):
            warnings.append(f"filename contains {forbidden}")
    result = {"decision": "PASS" if not errors and not warnings else "FAIL", "errors": errors, "warnings": warnings, "rounds": summaries, "visual_png_count": len(visuals), "visual_gif_count": len(gifs), "algorithm_source_diff": bool(diff.stdout.strip())}
    out = EV / "s2_r5_audit.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "errors": len(errors), "warnings": len(warnings)}, ensure_ascii=False))
    return 0 if not errors and not warnings else 1


if __name__ == "__main__":
    raise SystemExit(main())
