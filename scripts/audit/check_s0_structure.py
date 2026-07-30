from pathlib import Path
import json, sys

root = Path(__file__).resolve().parents[2]
required = [
    root / 'README.md', root / '.gitignore', root / '00_空中机械臂驱鸟器仿真研究项目_权威总纲_v1.0.md',
    root / '01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md', root / 'docs/archive/01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.0.md',
    root / 'docs/evidence/S0-R1/hardware_audit.json', root / 'docs/evidence/S0-R1/initial_file_hashes.txt',
    root / 'docs/evidence/S0-R1/third_party_refs.txt', root / 'docs/third_party_manifest.md']
missing = [str(p.relative_to(root)) for p in required if not p.is_file() or p.stat().st_size == 0]
try: json.loads((root / 'docs/evidence/S0-R1/hardware_audit.json').read_text(encoding='utf-8-sig'))
except Exception as e: missing.append(f'hardware_audit.json invalid: {e}')
progress = (root / '01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md').read_text(encoding='utf-8') if (root / '01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md').exists() else ''
if 'SUBMITTED_FOR_REVIEW' not in progress: missing.append('progress lacks SUBMITTED_FOR_REVIEW')
if missing:
    print('S0 structure check failed:'); print('\n'.join(missing)); sys.exit(1)
print('S0 structure check passed')
