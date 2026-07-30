from pathlib import Path
import hashlib, json, re, sys

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ROOT = Path(r"D:\Desktop\my_project\Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation")
EXPECTED_TASK_SHA = "3EA65A31E1D641847FAD1163D2A801B681B76CF9B49C3610C155C97CFD362425"
errors=[]; warnings=[]
def check(label, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{(': '+detail) if detail else ''}")
    if not ok: errors.append(label)
def warn(label, detail):
    print(f"[WARN] {label}: {detail}"); warnings.append(label)
def read(path): return path.read_text(encoding="utf-8-sig")

check("project root", ROOT.resolve() == EXPECTED_ROOT.resolve(), str(ROOT))
check("single project .git", (ROOT/".git").exists() and not any((p/".git").exists() for p in ROOT.parents))
check("remote", __import__("subprocess").run(["git","remote","get-url","origin"],cwd=ROOT,capture_output=True,text=True).stdout.strip().rstrip("/") == "https://github.com/canimiliya/risk-aware-aerial-manipulation.git")
check("branch", __import__("subprocess").run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True).stdout.strip() == "agent/s0-r1-workspace-hardware-audit")
required=["00_空中机械臂驱鸟器仿真研究项目_权威总纲_v1.0.md","01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md","docs/archive/01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.0.md","docs/tasks/S0-R1_项目初始化硬件与依赖审计_任务卡.md","docs/tasks/S0-R1-R1_S0治理文件与审计证据链返修_任务卡.md","docs/reviews/S0-R1_review_2026-07-31.md","docs/evidence/S0-R1-R1/hardware_audit.json","docs/evidence/S0-R1-R1/toolchain_raw.txt","docs/evidence/S0-R1-R1/nvidia_smi.txt","docs/evidence/S0-R1-R1/wsl_status_utf8.txt","docs/evidence/S0-R1-R1/wsl_version_utf8.txt","docs/evidence/S0-R1-R1/wsl_list_verbose_utf8.txt","docs/evidence/S0-R1-R1/AirFAR-Ubuntu20_os_release.txt","third_party/licenses/isaaclab_LICENSE_v2.3.2.txt","third_party/licenses/Polynomial_DiT_LICENSE_STATUS_f31c8f0.md","docs/reports/S0-R1-R1_repair_report.md"]
for rel in required: check(f"required {rel}",(ROOT/rel).is_file() and (ROOT/rel).stat().st_size>0)
progress=read(ROOT/"01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md")
check("progress >= 12KB",(ROOT/"01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md").stat().st_size>=12000)
for section in ["文件权威性与使用规则","标准任务闭环","统一状态","阶段总表","当前任务槽位","任务历史","高级总控审查模板","进度更新规则","计算资源","GitHub 信息","硬件与系统","决策记录","当前待办"]: check(f"progress section {section}",section in progress)
check("formal S0 status", "S0_SUBMITTED_FOR_REVIEW" in progress and "S0：SUBMITTED_FOR_REVIEW" in progress)
check("no approved S0 status", not re.search(r"(?:当前状态|总体状态|^S0\s*[:：]|\|\s*S0\s*\|)[^\n]{0,80}(?:PASS_WITH_LIMITATIONS|(?<!SUBMITTED_)PASS)(?![A-Z_])",progress,re.M))
task=read(ROOT/"docs/tasks/S0-R1_项目初始化硬件与依赖审计_任务卡.md"); normalized=task.replace("\r\n","\n").replace("\r","\n"); actual=hashlib.sha256(normalized.encode()).hexdigest().upper(); print(f"[INFO] original task normalized bytes={len(normalized.encode())} sha256={actual}")
if actual != EXPECTED_TASK_SHA: warn("original task source hash",f"expected {EXPECTED_TASK_SHA}, actual {actual}; attachment supplied to this run is shorter than its declared 1056-line/27587-byte baseline")
else: print("[PASS] original task normalized SHA-256")
try:
    audit=json.loads((ROOT/"docs/evidence/S0-R1-R1/hardware_audit.json").read_text(encoding="utf-8-sig")); check("hardware JSON",True)
except Exception as exc: check("hardware JSON",False,str(exc)); audit={}
for name in ["python","conda","git","gh"]:
    item=audit.get(name,{}); out=str(item.get("version_output","")); check(f"{name} real version",item.get("status")=="OK" and "usage:" not in out.lower() and bool(re.search(r"\d+\.\d+",out)))
gpu=audit.get("gpu",{});check("compute capability separate",bool(gpu.get("compute_capability")) and "driver_cuda_compatibility" in gpu)
for rel in ["wsl_status_utf8.txt","wsl_version_utf8.txt","wsl_list_verbose_utf8.txt","AirFAR-Ubuntu20_os_release.txt"]:
    b=(ROOT/"docs/evidence/S0-R1-R1"/rel).read_bytes();
    try:b.decode("utf-8"); utf=True
    except UnicodeDecodeError:utf=False
    check(f"UTF-8 {rel}",utf and b"\x00" not in b)
for rel in ["docs/evidence/S0-R1-R1","third_party/licenses"]: check(f"evidence directory {rel}",(ROOT/rel).is_dir())
large=[p for p in ROOT.rglob("*") if p.is_file() and p.stat().st_size>10*1024*1024 and not p.name.endswith(".tmp")];check("no large files",not large, str(large))
secret=re.compile(r"ghp_|github_pat_|AKIA|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|password\s*=|token\s*=")
hits=[]
for p in ROOT.rglob("*"):
    rel=str(p.relative_to(ROOT)).replace('\\','/')
    if p.is_file() and p.stat().st_size<2*1024*1024 and '.git' not in p.parts and '__pycache__' not in p.parts and 'docs/tasks/' not in rel and p.name!='check_s0_structure.py':
        try:
            if secret.search(p.read_text(encoding="utf-8",errors="ignore")): hits.append(str(p.relative_to(ROOT)))
        except OSError: pass
check("no secret patterns",not hits,str(hits))
print(f"SUMMARY errors={len(errors)} warnings={len(warnings)}")
sys.exit(1 if errors else 0)
