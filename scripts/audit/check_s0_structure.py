from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ROOT = Path(r"D:\Desktop\my_project\Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation")
EXPECTED_TASK_BYTES = 27587
EXPECTED_TASK_LINES = 1056
EXPECTED_TASK_SHA = "3EA65A31E1D641847FAD1163D2A801B681B76CF9B49C3610C155C97CFD362425"
FORBIDDEN_STALE_PROGRESS_MARKERS = [
    "PRESTART_WAITING_REPOSITORY_AND_HARDWARE_INFO", "WAITING_INPUT", "当前执行任务：无", "允许执行 S0：尚未授权",
]


def is_link_like(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        stat_result = os.lstat(path)
    except OSError:
        return True
    return bool(getattr(stat_result, "st_file_attributes", 0) & 0x400)


def safe_files(root: Path, skipped_paths: list[str]) -> list[Path]:
    files: list[Path] = []

    def onerror(error: OSError) -> None:
        skipped_paths.append(f"{error.filename or root}: {error}")

    for directory, directories, filenames in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        base = Path(directory)
        kept: list[str] = []
        for name in directories:
            path = base / name
            if is_link_like(path):
                skipped_paths.append(str(path.relative_to(root)).replace("\\", "/"))
            else:
                kept.append(name)
        directories[:] = kept
        for name in filenames:
            path = base / name
            if is_link_like(path):
                skipped_paths.append(str(path.relative_to(root)).replace("\\", "/"))
            else:
                files.append(path)
    return files


def branch_is_allowed(branch: str, expected_branch: str | None = None) -> bool:
    return bool(branch) and (expected_branch is None or branch == expected_branch)


def current_branch(root: Path) -> str:
    return subprocess.run(["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True, check=False).stdout.strip()


def select_progress_path(root: Path) -> Path:
    for version in ("v1.4", "v1.3", "v1.2"):
        matches = list(root.glob(f"01_*_{version}.md"))
        if matches:
            return matches[0]
    return root / "01_progress_v1.4.md"


def find_one(root: Path, pattern: str) -> Path:
    matches = list(root.glob(pattern))
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[0]


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False).stdout.strip()


def run_audit(root: Path = ROOT, expected_branch: str | None = None) -> int:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    skipped_paths: list[str] = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}{(': ' + detail) if detail else ''}")
        if not ok:
            errors.append(label)

    progress_path = select_progress_path(root)
    task_path = find_one(root / "docs/tasks", "S0-R1_*.md")
    required_paths = [
        find_one(root, "00_*_v1.0.md"), progress_path,
        find_one(root / "docs/archive", "01_*_v1.2.md"), task_path,
        find_one(root / "docs/tasks", "S0-R1-R2_*.md"),
        root / "docs/reviews/S0-R1-R1_review_2026-07-31.md", root / "docs/reviews/S0_final_review_2026-07-31.md",
        root / "docs/reports/S0-R1-R2_closeout_report.md", root / "docs/milestones/S0_status.md",
        root / "docs/evidence/S0-R1-R2/recovery_interrupted_files_manifest.md",
        root / "third_party/licenses/AM-Planner_LICENSE_STATUS_7ea9a0a.md", root / "docs/evidence/S0-R1-R1/hardware_audit.json",
    ]
    check("project root", root == EXPECTED_ROOT.resolve(), str(root))
    check("single project .git", (root / ".git").exists() and not any((p / ".git").exists() for p in root.parents))
    check("remote", git(root, "remote", "get-url", "origin").rstrip("/") == "https://github.com/canimiliya/risk-aware-aerial-manipulation.git")
    branch = current_branch(root)
    check("branch", branch_is_allowed(branch, expected_branch), branch or "DETACHED_HEAD")
    for path in required_paths:
        try:
            ok = path.is_file() and path.stat().st_size > 0
        except OSError as error:
            skipped_paths.append(str(path) + ": " + str(error))
            ok = False
        check(f"required {path.relative_to(root)}", ok)

    task_bytes = task_path.read_bytes()
    check("authoritative task bytes", len(task_bytes) == EXPECTED_TASK_BYTES, str(len(task_bytes)))
    check("authoritative task lines", task_bytes.count(b"\n") + (0 if task_bytes.endswith(b"\n") else 1) == EXPECTED_TASK_LINES)
    check("authoritative task SHA-256", hashlib.sha256(task_bytes).hexdigest().upper() == EXPECTED_TASK_SHA)

    progress = progress_path.read_text(encoding="utf-8-sig")
    if progress_path.name.endswith("v1.4.md"):
        checks = ["S0", "S1-R1", "S1-R2", "S1", "S2", "S3--S8", "PASS_WITH_LIMITATIONS", "IN_PROGRESS", "FROZEN"]
        check("progress v1.4 selected", True, progress_path.name)
    else:
        checks = ["文件权威性与使用规则", "标准任务闭环", "统一状态", "阶段总表", "当前任务槽位", "任务历史", "高级总控审查模板", "进度更新规则", "计算资源", "GitHub 信息", "硬件与系统", "决策记录", "当前待办", "S0：PASS_WITH_LIMITATIONS"]
        check("progress >= 12KB", progress_path.stat().st_size >= 12000)
    for item in checks:
        check(f"progress fact {item}", item in progress)
    for marker in FORBIDDEN_STALE_PROGRESS_MARKERS:
        check(f"stale marker absent: {marker}", marker not in progress)
    check("S1 not falsely reproduced", not re.search(r"S1[^\n]{0,100}(?:已复现|已安装|可运行)", progress))

    final_review = (root / "docs/reviews/S0_final_review_2026-07-31.md").read_text(encoding="utf-8-sig")
    for fact in ["S0-R1-R2", "2f441c4d4ebace01c3ef76cec00d546813dee267", "PASS_WITH_LIMITATIONS", "Isaac Sim/Lab", "WSL", "ROS Noetic"]:
        check(f"final review fact: {fact}", fact in final_review)
    audit = json.loads((root / "docs/evidence/S0-R1-R1/hardware_audit.json").read_text(encoding="utf-8-sig"))
    check("hardware JSON top-level object", isinstance(audit, dict), type(audit).__name__)
    for name in ["python", "conda", "git", "gh"]:
        item = audit.get(name, {})
        out = str(item.get("version_output", ""))
        check(f"{name} real version", item.get("status") == "OK" and "usage:" not in out.lower() and bool(re.search(r"\d+\.\d+", out)))
    for rel in ["wsl_status_utf8.txt", "wsl_version_utf8.txt", "wsl_list_verbose_utf8.txt", "AirFAR-Ubuntu20_os_release.txt"]:
        data = (root / "docs/evidence/S0-R1-R1" / rel).read_bytes()
        try:
            data.decode("utf-8")
            valid = b"\x00" not in data
        except UnicodeDecodeError:
            valid = False
        check(f"UTF-8/NUL {rel}", valid)

    license_status = "README_DECLARES_MIT_LICENSE_BUT_LICENSE_FILE_UNAVAILABLE_AT_FROZEN_COMMIT"
    license_text = (root / "third_party/licenses/AM-Planner_LICENSE_STATUS_7ea9a0a.md").read_text(encoding="utf-8-sig")
    manifest = (root / "docs/third_party_manifest.md").read_text(encoding="utf-8-sig")
    check("AM-Planner license status", license_status in license_text and license_status in manifest)
    check("no inaccurate AM-Planner statement", "README 未给明确许可证" not in manifest)

    all_files = safe_files(root, skipped_paths)
    large = [p for p in all_files if ".git" not in p.parts and "third_party" not in p.parts and p.stat().st_size > 10 * 1024 * 1024]
    check("no large files", not large, str(large))
    secret = re.compile(r"ghp_|github_pat_|AKIA|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|password\s*=|token\s*=", re.I)
    hits = []
    for path in all_files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        if ".git" not in path.parts and "__pycache__" not in path.parts and "third_party" not in path.parts and "docs/tasks/" not in rel and not rel.startswith("scripts/audit/") and path.stat().st_size < 2 * 1024 * 1024:
            try:
                if secret.search(path.read_text(encoding="utf-8", errors="ignore")):
                    hits.append(rel)
            except OSError as error:
                skipped_paths.append(rel + ": " + str(error))
    check("no secret patterns", not hits, str(hits))
    print(f"SKIPPED_PATHS count={len(set(skipped_paths))}")
    for item in sorted(set(skipped_paths)):
        print(f"[SKIP] {item}")
    print(f"SUMMARY errors={len(errors)} warnings={len(warnings)} skipped_paths={len(set(skipped_paths))}")
    return 1 if errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--expected-branch", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_audit(args.repo, args.expected_branch))
