from __future__ import annotations

import json
from pathlib import Path

from scripts.audit.check_s2_r2_am_planner_planning import run as run_r2
from scripts.audit.check_s3_s2_baseline import run as run_baseline


ROOT = Path(__file__).resolve().parents[2]


def test_authoritative_baseline_ignores_original_local_artifact_gap() -> None:
    result = run_baseline(ROOT)
    assert result["decision"] == "PASS"
    assert result["original_audits_required"] is False


def test_archival_r2_uses_committed_provenance_without_clone() -> None:
    result = run_r2(ROOT, audit_mode="archival")
    assert result["decision"] == "SUBMITTED_S2_R2_AM_PLANNER_READY"
    assert result["local_clone_checked"] is False
    assert result["official_commit_source"] == "committed_provenance"


def test_original_r2_missing_clone_is_structured() -> None:
    result = run_r2(ROOT, audit_mode="original", source_clone=ROOT / "does-not-exist")
    assert result["decision"] == "REVISION_REQUIRED"
    assert "official_source_clone_missing" in result["errors"]


def test_archival_provenance_mutation_fails(tmp_path: Path) -> None:
    for source in (ROOT / "docs", ROOT / "scripts"):
        target = tmp_path / source.name
        target.mkdir(parents=True)
    provenance = json.loads((ROOT / "docs/evidence/S2-R2/environment/source_clone_provenance.json").read_text(encoding="utf-8"))
    provenance["official_commit"] = "0" * 40
    assert provenance["official_commit"] != "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d"
