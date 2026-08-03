# S2-R2 environment setup attempt

## Fixed target

- WSL distro: `AMPlanner-Ubuntu20` (Ubuntu 20.04.3 LTS).
- Required workspace: `/home/amplanner/am-planner-s2-r2-ws`.
- Required official source commit: `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`.
- Existing isolated overlay: `/home/amplanner/ros-noetic-py39-overlay-r7r3-r1`.
- Existing GPU environment: `am-planner-gpu-probe-py39`.

## Verified before the gate

- Python: `3.9.23`.
- Torch: `2.7.1+cu128`.
- CUDA: available; device `NVIDIA GeForce RTX 5060 Ti`.
- Required target workspace was absent before the setup attempt.
- Existing old workspaces were not reused for this gate.

## Official-source attempts

1. `git clone --filter=blob:none --no-checkout https://github.com/SYSU-HILAB/am-planner.git /home/amplanner/am-planner-s2-r2-ws`
   - Result: `GnuTLS recv error (-110)`.
2. Retry with `GIT_HTTP_VERSION=HTTP/1.1` and `git -c http.version=HTTP/1.1`.
   - Result: `Failed to connect to github.com port 443: Connection timed out`.
3. The repository-local official checkout at `third_party/am-planner` is frozen at the required commit, but its local clone into WSL failed because a required Git object was unavailable. This was recorded as a source-preserving fallback attempt; no mirror or unrelated source was used.

After each failed attempt, `/home/amplanner/am-planner-s2-r2-ws` was verified absent. No build/devel/install directory was copied or created for S2-R2.

## Gate result

This environment setup is not claimed as a completed clean WSL clone/build. The subsequent planner-contract gate independently blocks S2-R2 before runtime.
