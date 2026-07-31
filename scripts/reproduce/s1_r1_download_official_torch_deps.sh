#!/usr/bin/env bash
set -euo pipefail
out=/home/amplanner/am-planner-ws/downloads/torch-2.7.1-cu128-py39
mkdir -p "$out"
base=https://download-r2.pytorch.org/whl/cu128
urls=(
  nvidia-cuda-nvrtc-cu12-12.8.61-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl
  nvidia-cuda-runtime-cu12-12.8.57-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  nvidia-cuda-cupti-cu12-12.8.57-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  nvidia-cudnn-cu12-9.7.1.26-py3-none-manylinux_2_27_x86_64.whl
  nvidia-cublas-cu12-12.8.3.14-py3-none-manylinux_2_27_x86_64.whl
  nvidia-cufft-cu12-11.3.3.41-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  nvidia-curand-cu12-10.3.9.55-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  nvidia-cusolver-cu12-11.7.2.55-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  nvidia-cusparse-cu12-12.5.7.53-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  nvidia-cusparselt-cu12-0.6.3-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  nvidia-nccl-cu12-2.26.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  nvidia-nvtx-cu12-12.8.55-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  nvidia-nvjitlink-cu12-12.8.61-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  nvidia-cufile-cu12-1.13.0.11-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
  triton-3.3.1-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
)
for name in "${urls[@]}"; do
  if [ -s "$out/$name" ]; then continue; fi
  echo "downloading $name"
  curl -L --fail --retry 2 --connect-timeout 30 --max-time 1800 "$base/$name" -o "$out/$name"
done
sha256sum "$out"/*.whl
