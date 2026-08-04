# Official installation method

The formal environment is `D:\i3\e`. The previous `D:\i3\s3_isaaclab_232` remains an untouched failure scene.

1. Install `isaacsim[all,extscache]==5.1.0` with the official NVIDIA extra index.
2. Install `torch==2.7.0` and `torchvision==0.22.0` from the official PyTorch `cu128` index.
3. Clone Isaac Lab from GitHub tag `v2.3.2` to `D:\i3\L`.
4. Build/install `flatdict==4.0.1` from the official PyPI sdist using `setuptools==80.10.2` and `--no-build-isolation`.
5. Run the official source installer with the environment explicitly selected: `isaaclab.bat -i none`.

No Isaac Lab source dependency metadata was edited. No RL framework was installed. The installer did install the upstream `isaaclab_rl` core package, but no `rsl_rl`, `rl_games`, `skrl`, SB3, or `robomimic` package is present.
