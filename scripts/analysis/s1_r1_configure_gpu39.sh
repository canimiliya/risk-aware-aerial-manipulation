#!/usr/bin/env bash
set -euo pipefail

source /home/amplanner/miniforge3/etc/profile.d/conda.sh
conda activate am-planner-gpu-probe-py39
export ROS_DISTRO=noetic
set +u
source /opt/ros/noetic/setup.bash
set -u

GPU39_WS=/home/amplanner/am-planner-gpu39-ws
PYROOT="$CONDA_PREFIX"
PYEXE="$PYROOT/bin/python"
PYINC="$PYROOT/include/python3.9"
PYLIB="$PYROOT/lib/libpython3.9.so"
PYBIND11_DIR=$(dirname "$(find "$PYROOT" -name pybind11Config.cmake -print -quit)")
AUTODIFF_DIR=$(dirname "$(find "$PYROOT" -name autodiffConfig.cmake -print -quit)")

cd "$GPU39_WS"
/usr/bin/catkin config \
  --extend /opt/ros/noetic \
  --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_LINK_WHAT_YOU_USE=TRUE \
    -DCMAKE_EXE_LINKER_FLAGS="-L$PYROOT/lib -Wl,--as-needed" \
    -DCMAKE_SHARED_LINKER_FLAGS="-L$PYROOT/lib -Wl,--as-needed" \
    -DPython_EXECUTABLE="$PYEXE" \
    -DPython_ROOT_DIR="$PYROOT" \
    -DPython_INCLUDE_DIR="$PYINC" \
    -DPython_LIBRARY="$PYLIB" \
    -DPython3_EXECUTABLE="$PYEXE" \
    -DPython3_ROOT_DIR="$PYROOT" \
    -DPython3_INCLUDE_DIR="$PYINC" \
    -DPython3_LIBRARY="$PYLIB" \
    -DPYTHON_EXECUTABLE="$PYEXE" \
    -DPYTHON_INCLUDE_DIR="$PYINC" \
    -DPYTHON_LIBRARY="$PYLIB" \
    -DPYBIND11_FINDPYTHON=ON \
    -Dpybind11_DIR="$PYBIND11_DIR" \
    -Dautodiff_DIR="$AUTODIFF_DIR" \
    -DCMAKE_PREFIX_PATH="$PYROOT;$GPU39_WS/devel;/opt/ros/noetic"
