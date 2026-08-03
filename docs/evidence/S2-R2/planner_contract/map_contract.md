# Official map contract

- `se3_planner.cc:8-17` subscribes to `/global_map` as `sensor_msgs::PointCloud2` and passes it to JPS.
- `se3_planner.cc:540-550` converts the message to points and forces the callback cloud frame to `config_.odomFrame`.
- `plan_manage/misc/jps3d.xml:2-18` defines the default map frame as `world` and the default JPS/map resolution as `0.03` m.
- `utils/map_pcl/src/visual_pcl.cpp:233-235` reads a PCD path and frame id, and `:264-270` publishes `/global_map` as `sensor_msgs::PointCloud2`.

S2-R2 did not generate or publish a crossarm map because the planner-contract gate failed before B5.
