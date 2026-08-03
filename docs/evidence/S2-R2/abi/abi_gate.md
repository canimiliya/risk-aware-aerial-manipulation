# S2-R2 ABI and GPU gate

Decision: ABI and GPU prerequisites passed for the clean S2-R2 workspace.

- Direct ELF dependency inspection for `libse3_planner.so` and `se3_node` found no Python 3.8 dependency; the direct Python dependency is `libpython3.9.so.1.0`.
- With official ROS, the Python 3.9 overlay, the new S2-R2 devel space, and its runtime library path, the independent `ldd` closure had `ABI_RUNTIME_NOT_FOUND=0` and no `python3.8`.
- GPU probe: Python 3.9.23, Torch `2.7.1+cu128`, CUDA available, NVIDIA GeForce RTX 5060 Ti, capability `(12, 0)`.

The accepted S1 CMake ABI patch is preserved as provenance; no CPU fallback, weight conversion, or algorithm-source modification was used.
