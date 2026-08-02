#!/usr/bin/env bash
# Installs only the task-approved official CPU torch wheel and records evidence.
set -euo pipefail

ROOT=/home/amplanner/am-planner-ws
OUT="$ROOT/logs/s1-r1-r3-torch"
CACHE="$ROOT/downloads/torch-2.4.1-cpu"
mkdir -p "$OUT" "$CACHE"

source /home/amplanner/miniforge3/etc/profile.d/conda.sh
conda activate am-planner-py38

{
  echo "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python -m pip list
  python -m pip show torch || true
  df -h / /home
} > "$OUT/preinstall_environment.txt" 2>&1
python -m pip index versions torch --index-url https://download.pytorch.org/whl/cpu > "$OUT/official_index_probe.txt" 2>&1
python -m pip download torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu --only-binary=:all: --dest "$CACHE" > "$OUT/download_log.txt" 2>&1

python - <<'PY' > "$OUT/download_manifest.json"
from pathlib import Path
import hashlib, json
cache = Path('/home/amplanner/am-planner-ws/downloads/torch-2.4.1-cpu')
files = []
for path in sorted(cache.iterdir()):
    if path.is_file():
        files.append({'filename': path.name, 'bytes': path.stat().st_size,
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'source_index': 'https://download.pytorch.org/whl/cpu'})
print(json.dumps({'torch_requirement': 'torch==2.4.1',
                  'official_index': 'https://download.pytorch.org/whl/cpu',
                  'files': files}, ensure_ascii=False, indent=2))
PY
sha256sum "$CACHE"/* > "$OUT/wheel_sha256.txt"
python -m pip install --no-index --find-links "$CACHE" torch==2.4.1 > "$OUT/install_log.txt" 2>&1

python - <<'PY' > "$OUT/torch_probe.json"
import json, torch
result = {'torch_version': torch.__version__, 'cuda_available': torch.cuda.is_available(),
          'cuda_version': torch.version.cuda, 'device_count': torch.cuda.device_count()}
x = torch.tensor([[1.0, 2.0, 3.0]], requires_grad=True)
layer = torch.nn.Linear(3, 1)
y = layer(x).sum(); y.backward()
result['nn_forward_ok'] = bool(torch.isfinite(y).item())
result['autograd_ok'] = x.grad is not None and bool(torch.isfinite(x.grad).all().item())
print(json.dumps(result, indent=2))
assert torch.__version__.startswith('2.4.1')
assert result['cuda_available'] is False and result['cuda_version'] is None
assert result['nn_forward_ok'] and result['autograd_ok']
PY
python -m pip show torchvision torchaudio triton > "$OUT/forbidden_packages_probe.txt" 2>&1 || true

WEIGHT="$ROOT/src/am-planner/src/plan/traj_opt/weights/workspace_probability_weight.pth"
test -f "$WEIGHT"
{ stat -c 'bytes=%s path=%n' "$WEIGHT"; sha256sum "$WEIGHT"; } > "$OUT/workspace_weight_manifest.txt"
python - <<'PY' > "$OUT/workspace_weight_load_probe.json"
from pathlib import Path
import json, torch
path = Path('/home/amplanner/am-planner-ws/src/am-planner/src/plan/traj_opt/weights/workspace_probability_weight.pth')
obj = torch.load(str(path), map_location='cpu')
assert isinstance(obj, dict)
tensors = [value for value in obj.values() if torch.is_tensor(value)]
result = {'object_type': type(obj).__name__, 'key_count': len(obj), 'tensor_count': len(tensors),
          'all_finite': all(bool(torch.isfinite(value).all().item()) for value in tensors),
          'nonzero_tensor_count': sum(int(bool(torch.count_nonzero(value).item())) for value in tensors),
          'sample_keys': list(obj.keys())[:20]}
print(json.dumps(result, indent=2, default=str))
assert result['tensor_count'] > 0 and result['all_finite'] and result['nonzero_tensor_count'] > 0
PY
{
  echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python --version
  python -m pip show torch
  python -m pip show torchvision torchaudio triton || true
} > "$OUT/environment_after_torch.txt" 2>&1
