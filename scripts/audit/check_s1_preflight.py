from pathlib import Path
import json, re, sys

ROOT = Path(__file__).resolve().parents[2]
errors, warnings = [], []
def check(label, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{(': ' + detail) if detail else ''}")
    if not ok: errors.append(label)
def read(rel): return (ROOT / rel).read_text(encoding="utf-8-sig")

progress = read("01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.3.md")
check("v1.3 progress exists", "S1_PREFLIGHT_" in progress)
check("S0 pass with limitations", "S0：PASS_WITH_LIMITATIONS" in progress)
check("S1 submitted or in progress", "S1：SUBMITTED_FOR_REVIEW" in progress or "S1：IN_PROGRESS" in progress)
check("S2-S8 frozen", "S2–S8：FROZEN" in progress)
for rel in ["docs/archive/01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md", "docs/tasks/BATCH-S0C-S1P_任务卡.md", "docs/milestones/S1_status.md", "docs/reports/S1-R0_preflight_report.md", "docs/environment_lock_s1_am_planner.md", "docs/evidence/S0-FINAL/pr_merged_snapshot.json"]:
    check(rel, (ROOT / rel).is_file() and (ROOT / rel).stat().st_size > 0)
evidence = ROOT / "docs/evidence/S1-R0"
for name in ["wsl_version", "wsl_status", "wsl_list_verbose", "wsl_list_running", "distro_Ubuntu_24_04", "distro_Ubuntu", "distro_NMPC_Ubuntu22", "distro_dbLaCAM_Ubuntu", "distro_AirFAR_Ubuntu20"]:
    path = evidence / f"{name}.json"; check(f"recorded {name}", path.is_file())
    if path.is_file():
        obj=json.loads(path.read_text(encoding="utf-8-sig")); check(f"{name} has result", "timed_out" in obj and "exit_code" in obj)
report=read("docs/reports/S1-R0_preflight_report.md")
for fact in ["CREATE_NEW_ISOLATED_UBUNTU20_RECOMMENDED", "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d", "f31c8f04e5fa045bc08c7bbaaadfe60bb54816f1", "基础规划可暂时绕过", "未安装、未创建 Conda 环境、未下载 checkpoint、未运行规划、未训练"]:
    check(f"report fact: {fact}", fact in report)
check("no false license claim", "Polynomial_DiT.*MIT" not in report)
large=[p for p in ROOT.rglob("*") if p.is_file() and p.stat().st_size > 10*1024*1024 and ".git" not in p.parts and "third_party" not in p.parts]
check("no large files", not large, str(large))
secret=re.compile(r"ghp_|github_pat_|AKIA|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|password\s*=|token\s*=", re.I)
hits=[]
for p in ROOT.rglob("*"):
    rel=str(p.relative_to(ROOT)).replace("\\", "/")
    if p.is_file() and p.stat().st_size < 2*1024*1024 and ".git" not in p.parts and "third_party" not in p.parts and "__pycache__" not in p.parts and not rel.startswith("docs/tasks/") and not rel.startswith("scripts/audit/"):
        if secret.search(p.read_text(encoding="utf-8", errors="ignore")): hits.append(str(p.relative_to(ROOT)))
check("no secret patterns", not hits, str(hits))
print(f"SUMMARY errors={len(errors)} warnings={len(warnings)}")
sys.exit(1 if errors else 0)
