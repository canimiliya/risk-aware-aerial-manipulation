# S3-R0 official asset inventory

Source is the repository's read-only `third_party/am-planner` checkout at commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`.

- URDF/Xacro: `third_party/am-planner/src/uam_sim/delta-display/delta_display/urdf/arm.xacro`
- Meshes: `third_party/am-planner/src/uam_sim/delta-display/delta_display/meshes/`
- Active joints: `m1_1`, `m2_1`, `m3_1`
- Passive/trailing joints: `m1_2`, `m1_3`, `m2_2`, `m2_3`, `m3_2`, `m3_3`
- Base-to-arm frame: B to A0 translation `[0, 0, -0.05]`, RPY `[0, 0, -1.5708]`
- Asset source was not modified. The URDF used for import was an external materialized copy under `D:\i3\a` with only numeric scale/path resolution.
