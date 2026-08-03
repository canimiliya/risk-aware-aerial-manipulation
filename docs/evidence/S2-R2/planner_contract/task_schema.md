# Official AM-Planner task schema (corrected)

Source: fixed official checkout `third_party/am-planner`, commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`.

- `src/plan/plan_manage/src/plan_manage.cpp:441-489` selects `/mode`, reads `/task`, and loads `/task/start_pt` and `/task/end_pt` for mode `2`.
- `src/plan/plan_manage/src/plan_manage.cpp:458-459` initializes `init_state_` and `fin_state_` as `3x3` matrices; the first column is position and the remaining zero columns represent boundary velocity/acceleration.
- `src/plan/plan_manage/src/plan_manage.cpp:466-473` maps the start/end task values to the first-column base `x,y,z` entries.
- `src/plan/plan_manage/launch/tasks.yaml:1-59` defines task names (`push`, `pull`, `lift`, `press`, `write`) and their `start_pt`, `end_pt`, and `inter_points`.

There is no task-field contract for Delta joint values `m1_1,m2_1,m3_1` or for a joint-vector trajectory input. This is not a blocker for the official AM-Planner contract: the arm is an internal Cartesian MINCO optimization branch, and `/trajectory_arm` is its Cartesian polynomial output. No `q[3]` field is added.
