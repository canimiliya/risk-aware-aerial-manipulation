from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit/check_s2_r6_execution_envelope.py"
PATCH = ROOT / "third_party/patches/AM-Planner_S2-R6_execution_envelope.patch"


def load_module():
    spec = importlib.util.spec_from_file_location("check_s2_r6_patch_reproducibility", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_patch_has_exact_five_paths_and_header_mode() -> None:
    module = load_module()
    text = PATCH.read_text(encoding="utf-8")
    paths = [match.group(1) for match in re.finditer(r"^diff --git a/(.*?) b/.*$", text, flags=re.MULTILINE)]
    assert paths == module.ALLOWED_PATCH_PATHS
    assert "new file mode 100644" in text
    assert "execution_envelope_barrier.h" in text


def test_patch_repro_evidence_matches_patch_sha_and_tree() -> None:
    module = load_module()
    evidence = json.loads((ROOT / "docs/evidence/S2-R6/patch_only_reproduction.json").read_text(encoding="utf-8"))
    assert evidence["patch_sha256"] == hashlib.sha256(PATCH.read_bytes()).hexdigest()
    assert evidence["patch_apply_check"] is True
    assert evidence["tree_sha_match"] is True
    assert evidence["clean_build_devel"] is True
    assert evidence["targeted_build_exit"] == 0
    assert evidence["nominal_repeat_normalized_equal"] is True


def test_patch_line_endings_are_protected_from_windows_conversion() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "third_party/patches/AM-Planner_S2-R6_execution_envelope.patch -text" in attributes
    assert b"\r\n" not in PATCH.read_bytes()


def test_patch_audit_external_output_passes(tmp_path: Path) -> None:
    output = tmp_path / "s2_r6_audit.json"
    result = subprocess.run([sys.executable, str(SCRIPT), "--output", str(output)], cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["decision"] == "PASS"
    assert data["algorithm_patch"]["patch_self_contained"] is True
