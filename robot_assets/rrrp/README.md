# RRRP native dynamics asset

This directory is the independent S4-R4 replacement for the legacy Delta
asset. `rrrp_design.yaml` is the only authoritative design input. The URDF
and USD are generated from that file; neither is a second parameter source.

The model is an open-chain PhysX articulation:

`fixed_base/uav_mount -> q1 -> link1 -> q2 -> link2 -> q3 -> link3 -> d -> slider -> gripper_mount`

All current numbers are `ENGINEERING_NOMINAL` and `provisional: true`. The
floating-base UAV mass and inertia are explicitly `PROVISIONAL_LEGACY`; they
are not hardware validation. Collision geometry is conservative box geometry
derived from the same dimensions used for the mass and inertia manifest.

Generate the two deliverables with:

```powershell
D:/i3/e/python.exe robot_assets/rrrp/generate_rrrp_urdf.py
D:/i3/e/python.exe robot_assets/rrrp/import_rrrp_to_usd.py
```

The USD authoring path uses USD Physics joint schemas directly so the
runtime test can audit the exact articulation topology rather than relying on
visual playback.
