#!/usr/bin/env python3
from __future__ import annotations

import json
import platform
import sys

try:
    import torch
except Exception as exc:
    print(json.dumps({"python": sys.version, "error": f"{type(exc).__name__}: {exc}"}, indent=2))
    raise

result = {
    "python": sys.version,
    "platform": platform.platform(),
    "torch": torch.__version__,
    "cuda_available": bool(torch.cuda.is_available()),
    "torch_cuda": torch.version.cuda,
}
if result["cuda_available"]:
    result.update({"device": torch.cuda.get_device_name(), "capability": list(torch.cuda.get_device_capability())})
print(json.dumps(result, indent=2))
