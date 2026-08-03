from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit/check_s1_final_acceptance.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_s1_final_acceptance_no_side_effects", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_default_run_does_not_rewrite_historical_acceptance() -> None:
    target = ROOT / "docs/evidence/S1/final_acceptance/s1_final_acceptance.json"
    before = sha256(target)
    result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert sha256(target) == before


def test_external_output_is_supported(tmp_path: Path) -> None:
    output = tmp_path / "s1.json"
    result = subprocess.run([sys.executable, str(SCRIPT), "--output", str(output)], cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert output.is_file()


def test_tracked_output_requires_update_record(tmp_path: Path) -> None:
    target = ROOT / "docs/evidence/S1/final_acceptance/s1_final_acceptance.json"
    before = sha256(target)
    result = subprocess.run([sys.executable, str(SCRIPT), "--output", str(target)], cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "tracked_output_requires_update_record" in result.stdout
    assert sha256(target) == before


def test_update_record_can_write_the_default_record(monkeypatch, tmp_path: Path) -> None:
    module = load_module()
    target = tmp_path / "historical.json"
    monkeypatch.setattr(module, "DEFAULT_OUTPUT", target)
    monkeypatch.setattr(module, "run", lambda: {"decision": "PASS_WITH_LIMITATIONS", "errors": []})
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--update-record"])
    assert module.main() == 0
    assert target.is_file()
