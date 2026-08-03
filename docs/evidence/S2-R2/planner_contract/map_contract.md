# Official map contract

- `se3_planner.cc:8-17` subscribes to `/global_map` as `sensor_msgs::PointCloud2` and passes it to JPS.
- `se3_planner.cc:540-550` converts the message to points and forces the callback cloud frame to `config_.odomFrame`.
- `plan_manage/misc/jps3d.xml:2-18` defines the default map frame as `world` and the default JPS/map resolution as `0.03` m.
- `utils/map_pcl/src/visual_pcl.cpp:233-235` reads a PCD path and frame id, and `:264-270` publishes `/global_map` as `sensor_msgs::PointCloud2`.

## S2-R2 project map implementation

- Generator: `planner_bridge/scenes/generate_s2_r2_crossarm_map.py`.
- Publisher: `planner_bridge/scenes/publish_s2_r2_crossarm_map.py`, using `sensor_msgs/PointCloud2`, frame `world`, topic `/global_map`.
- Validator/test: `planner_bridge/scenes/validate_s2_r2_crossarm_map.py` and `planner_bridge/tests/test_s2_r2_crossarm_map.py`.
- Scenes: `smoke_free`, `loose`, `nominal`, and `narrow`; every non-free scene retains the main beam, pole, adjacent obstacle, and target proxy.
- Point resolution: `0.02 m`; official JPS runtime resolution remains `0.03 m` as configured by AM-Planner. The project map is not a claim that the planner internally used `0.02 m` JPS voxels.
- Reproducible manifests: `docs/evidence/S2-R2/maps/*.json`, including frame/topic, AABB, point count, and point SHA-256.

The previous sentence claiming that no map was generated was stale historical text from the pre-correction blocker and is superseded by this contract. No obstacle was removed to obtain a successful run.
