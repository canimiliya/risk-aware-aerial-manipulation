from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit/check_s2_r0_workspace_preflight.py"
FINAL_SCRIPT = ROOT / "scripts/audit/check_s2_r0_final_acceptance.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_archival_passes_without_local_npz() -> None:
    audit = load("check_s2_r0_workspace_preflight_archival", SCRIPT)
    result = audit.run(ROOT, audit_mode="archival")
    assert result["errors"] == []
    assert result["checks"]["local_npz_status"] == "NOT_PRESENT_LOCAL_ONLY"


def test_original_missing_npz_is_structured_failure() -> None:
    audit = load("check_s2_r0_workspace_preflight_original", SCRIPT)
    result = audit.run(ROOT, audit_mode="original")
    assert "local_npz_missing" in result["errors"]


def test_archival_missing_summary_is_structured_failure(monkeypatch) -> None:
    audit = load("check_s2_r0_workspace_preflight_missing_summary", SCRIPT)
    original = audit.read_json

    def missing_summary(path: Path):
        if path == ROOT / audit.SUMMARY_PATH:
            return None
        return original(path)

    monkeypatch.setattr(audit, "read_json", missing_summary)
    result = audit.run(ROOT, audit_mode="archival")
    assert "workspace_summary_missing" in result["errors"]


def test_archival_summary_mutation_is_rejected(monkeypatch) -> None:
    audit = load("check_s2_r0_workspace_preflight_mutated_summary", SCRIPT)
    original = audit.read_json

    def changed_summary(path: Path):
        value = original(path)
        if path == ROOT / audit.SUMMARY_PATH and value:
            changed = copy.deepcopy(value)
            changed["valid_fk_count"] += 1
            return changed
        return value

    monkeypatch.setattr(audit, "read_json", changed_summary)
    result = audit.run(ROOT, audit_mode="archival")
    assert "workspace_summary" in result["errors"]


def test_archival_missing_recovery_provenance_is_rejected(monkeypatch) -> None:
    audit = load("check_s2_r0_workspace_preflight_missing_recovery", SCRIPT)
    original = audit.read_json

    def missing_recovery(path: Path):
        if path == ROOT / audit.RECOVERY_PATH:
            return None
        return original(path)

    monkeypatch.setattr(audit, "read_json", missing_recovery)
    result = audit.run(ROOT, audit_mode="archival")
    assert "summary_recovery_provenance" in result["errors"]


def test_archival_manifest_mutation_is_rejected(monkeypatch) -> None:
    audit = load("check_s2_r0_workspace_preflight_mutated_manifest", SCRIPT)
    original = audit.read_json

    def changed_manifest(path: Path):
        value = original(path)
        if path == ROOT / "docs/evidence/S2-R0/workspace_sampling_manifest.json" and value:
            changed = copy.deepcopy(value)
            changed["random_seed"] += 1
            return changed
        return value

    monkeypatch.setattr(audit, "read_json", changed_manifest)
    result = audit.run(ROOT, audit_mode="archival")
    assert "workspace_manifest" in result["errors"]


def test_archival_g_arm_mutation_is_rejected(monkeypatch) -> None:
    audit = load("check_s2_r0_workspace_preflight_mutated_garm", SCRIPT)
    original = audit.read_json

    def changed_garm(path: Path):
        value = original(path)
        if path == ROOT / "docs/evidence/S2-R0/g_arm_preflight.json" and value:
            changed = copy.deepcopy(value)
            changed["workspace"]["valid_fk_count"] += 1
            return changed
        return value

    monkeypatch.setattr(audit, "read_json", changed_garm)
    result = audit.run(ROOT, audit_mode="archival")
    assert "g_arm_summary_consistent" in result["errors"]


def test_archival_rejects_detached_head(monkeypatch) -> None:
    audit = load("check_s2_r0_workspace_preflight_detached", SCRIPT)
    original = audit.git_stdout

    def detached(root: Path, *args: str) -> str:
        if args == ("branch", "--show-current"):
            return ""
        return original(root, *args)

    monkeypatch.setattr(audit, "git_stdout", detached)
    result = audit.run(ROOT, audit_mode="archival")
    assert "s2_branch" in result["errors"]
    assert "non_detached_head" in result["errors"]


def test_final_acceptance_passes_archival_mode_and_forwards_it(monkeypatch) -> None:
    final = load("check_s2_r0_final_acceptance_forwarding", FINAL_SCRIPT)
    original = final.subprocess.run
    calls: list[list[str]] = []

    def spy(command, *args, **kwargs):
        if isinstance(command, list) and any(str(item).endswith("check_s2_r0_workspace_preflight.py") for item in command):
            calls.append(command)
        return original(command, *args, **kwargs)

    monkeypatch.setattr(final.subprocess, "run", spy)
    result = final.run(ROOT, audit_mode="archival")
    assert result["decision"] == "PASS_WITH_LIMITATIONS"
    assert calls and "--audit-mode" in calls[0] and calls[0][calls[0].index("--audit-mode") + 1] == "archival"


def test_tracked_outputs_are_guarded(tmp_path: Path) -> None:
    preflight = subprocess.run([sys.executable, str(SCRIPT), "--output", str(ROOT / "docs/evidence/S2-R0/final_acceptance/s2_r0_workspace_preflight_audit.json")], cwd=ROOT, capture_output=True, text=True, check=False)
    final = subprocess.run([sys.executable, str(FINAL_SCRIPT), "--output", str(ROOT / "docs/evidence/S2-R0/final_acceptance/s2_r0_final_acceptance.json")], cwd=ROOT, capture_output=True, text=True, check=False)
    assert preflight.returncode == 2
    assert final.returncode == 2
