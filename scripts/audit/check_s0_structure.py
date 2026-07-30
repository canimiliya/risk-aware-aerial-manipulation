from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ROOT = Path(r"D:\Desktop\my_project\Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation")
EXPECTED_TASK_BYTES = 27587
EXPECTED_TASK_LINES = 1056
EXPECTED_TASK_SHA = "3EA65A31E1D641847FAD1163D2A801B681B76CF9B49C3610C155C97CFD362425"
FORBIDDEN_STALE_PROGRESS_MARKERS = [
    "PRESTART_WAITING_REPOSITORY_AND_HARDWARE_INFO", "GitHub 仓库：等待项目负责人创建",
    "本地根目录：等待项目负责人提供", "当前执行任务：无", "仓库 URL：WAITING_INPUT",
    "仓库所有者：WAITING_INPUT", "可见性：WAITING_INPUT", "本地项目根目录：WAITING_INPUT",
    "CPU：WAITING_INPUT", "GPU：WAITING_INPUT", "操作系统：WAITING_INPUT", "允许执行 S0：尚未授权",
]
errors = []
warnings = []

def check(label, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{(': ' + detail) if detail else ''}")
    if not ok:
        errors.append(label)

def text(path):
    return path.read_text(encoding="utf-8-sig")

def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()

check("project root", ROOT.resolve() == EXPECTED_ROOT.resolve(), str(ROOT))
check("single project .git", (ROOT / ".git").exists() and not any((p / ".git").exists() for p in ROOT.parents))
check("remote", git("remote", "get-url", "origin").rstrip("/") == "https://github.com/canimiliya/risk-aware-aerial-manipulation.git")
check("branch", git("branch", "--show-current") == "agent/s0-r1-workspace-hardware-audit")

required = [
    "00_空中机械臂驱鸟器仿真研究项目_权威总纲_v1.0.md", "01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md",
    "docs/tasks/S0-R1_项目初始化硬件与依赖审计_任务卡.md", "docs/tasks/S0-R1-R2_治理状态收口与权威任务卡替换_任务卡.md",
    "docs/reviews/S0-R1-R1_review_2026-07-31.md", "docs/reports/S0-R1-R2_closeout_report.md",
    "docs/milestones/S0_status.md", "docs/evidence/S0-R1-R2/recovery_interrupted_files_manifest.md",
    "third_party/licenses/AM-Planner_LICENSE_STATUS_7ea9a0a.md", "docs/evidence/S0-R1-R1/hardware_audit.json",
]
for rel in required:
    path = ROOT / rel
    check(f"required {rel}", path.is_file() and path.stat().st_size > 0)

task_path = ROOT / "docs/tasks/S0-R1_项目初始化硬件与依赖审计_任务卡.md"
task_bytes = task_path.read_bytes()
actual_lines = task_bytes.count(b"\n") + (0 if task_bytes.endswith(b"\n") else 1)
check("authoritative task bytes", len(task_bytes) == EXPECTED_TASK_BYTES, str(len(task_bytes)))
check("authoritative task lines", actual_lines == EXPECTED_TASK_LINES, str(actual_lines))
check("authoritative task SHA-256", hashlib.sha256(task_bytes).hexdigest().upper() == EXPECTED_TASK_SHA)

progress = text(ROOT / "01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md")
check("progress >= 12KB", (ROOT / "01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md").stat().st_size >= 12000)
for section in ["文件权威性与使用规则", "标准任务闭环", "统一状态", "阶段总表", "当前任务槽位", "任务历史", "高级总控审查模板", "进度更新规则", "计算资源", "GitHub 信息", "硬件与系统", "决策记录", "当前待办"]:
    check(f"progress section {section}", section in progress)
for marker in FORBIDDEN_STALE_PROGRESS_MARKERS:
    check(f"stale marker absent: {marker}", marker not in progress)
for fact in ["S0_SUBMITTED_FOR_REVIEW", "S0-R1-R2", "https://github.com/canimiliya/risk-aware-aerial-manipulation.git", r"D:\Desktop\my_project\Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation", "HARDWARE_PASS_WITH_LIMITATIONS"]:
    check(f"current progress fact: {fact}", fact in progress)
check("no approved S0", not re.search(r"(?:总体状态|^S0\s*[:：]|\|\s*S0\s*\|)[^\n]{0,80}(?:PASS_WITH_LIMITATIONS|(?<!SUBMITTED_)PASS)(?![A-Z_])", progress, re.M))

audit_path = ROOT / "docs/evidence/S0-R1-R1/hardware_audit.json"
try:
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    check("hardware JSON top-level object", isinstance(audit, dict), type(audit).__name__)
except Exception as exc:
    audit = {}
    check("hardware JSON parse", False, str(exc))
for name in ["python", "conda", "git", "gh"]:
    item = audit.get(name, {}) if isinstance(audit, dict) else {}
    out = str(item.get("version_output", ""))
    check(f"{name} real version", item.get("status") == "OK" and "usage:" not in out.lower() and bool(re.search(r"\d+\.\d+", out)))
for rel in ["wsl_status_utf8.txt", "wsl_version_utf8.txt", "wsl_list_verbose_utf8.txt", "AirFAR-Ubuntu20_os_release.txt"]:
    data = (ROOT / "docs/evidence/S0-R1-R1" / rel).read_bytes()
    try:
        data.decode("utf-8")
        valid = b"\x00" not in data
    except UnicodeDecodeError:
        valid = False
    check(f"UTF-8/NUL {rel}", valid)

license_path = ROOT / "third_party/licenses/AM-Planner_LICENSE_STATUS_7ea9a0a.md"
license_text = text(license_path)
manifest = text(ROOT / "docs/third_party_manifest.md")
license_status = "README_DECLARES_MIT_LICENSE_BUT_LICENSE_FILE_UNAVAILABLE_AT_FROZEN_COMMIT"
check("AM-Planner license status", license_status in license_text and license_status in manifest)
check("no inaccurate AM-Planner statement", "README 未给明确许可证" not in manifest)

large = [p for p in ROOT.rglob("*") if p.is_file() and p.stat().st_size > 10 * 1024 * 1024 and ".git" not in p.parts]
check("no large files", not large, str(large))
secret = re.compile(r"ghp_|github_pat_|AKIA|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|password\s*=|token\s*=", re.I)
hits = []
for path in ROOT.rglob("*"):
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    if path.is_file() and path.stat().st_size < 2 * 1024 * 1024 and ".git" not in path.parts and "__pycache__" not in path.parts and "docs/tasks/" not in rel and path.name != "check_s0_structure.py":
        if secret.search(path.read_text(encoding="utf-8", errors="ignore")):
            hits.append(rel)
check("no secret patterns", not hits, str(hits))
print(f"SUMMARY errors={len(errors)} warnings={len(warnings)}")
sys.exit(1 if errors else 0)
