from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit/check_s0_structure.py"
spec = importlib.util.spec_from_file_location("check_s0_structure", SCRIPT)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_branch_gate_accepts_main_and_stage_branches_but_not_detached() -> None:
    assert audit.branch_is_allowed("main")
    assert audit.branch_is_allowed("agent/s2-r0-delta-workspace-scene-contract")
    assert not audit.branch_is_allowed("")
    assert audit.branch_is_allowed("agent/s2-r0-delta-workspace-scene-contract", "agent/s2-r0-delta-workspace-scene-contract")
    assert not audit.branch_is_allowed("main", "agent/s2-r0-delta-workspace-scene-contract")


def test_progress_prefers_v14() -> None:
    assert audit.select_progress_path(ROOT).name == "01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.4.md"


def test_authoritative_task_sha_gate() -> None:
    task = ROOT / "docs/tasks/S0-R1_项目初始化硬件与依赖审计_任务卡.md"
    data = task.read_bytes()
    assert len(data) == audit.EXPECTED_TASK_BYTES
    assert hashlib.sha256(data).hexdigest().upper() == audit.EXPECTED_TASK_SHA


def test_safe_files_skips_invalid_symlink(tmp_path: Path) -> None:
    target = tmp_path / "missing-target"
    link = tmp_path / "invalid-link"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows host")
    skipped: list[str] = []
    files = audit.safe_files(tmp_path, skipped)
    assert link not in files
    assert "invalid-link" in skipped


def test_current_s0_audit_passes() -> None:
    assert audit.run_audit(ROOT) == 0
