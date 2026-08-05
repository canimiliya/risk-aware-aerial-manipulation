# Preserved pip-only failure

The previous pip-only meta-package attempt was stopped after dependency resolution/build metadata stalled at `flatdict==4.0.1`. The first attempt reached the 304-second bound and a bounded retry reached the 92-second bound. The captured root cause is the legacy source build requiring `pkg_resources` in an isolated modern build environment. This directory is historical evidence; the environment was not deleted or reused.

Original environment: `D:\i3\s3_isaaclab_232`

