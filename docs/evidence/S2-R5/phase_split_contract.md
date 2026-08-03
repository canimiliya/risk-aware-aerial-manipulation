# S2-R5 phase-split contract audit

`PHASE_SPLIT_NOT_SUPPORTED_BY_OFFICIAL_ARM_ENDPOINT_CONTRACT`

The official read-only source audit found that `SE3GCOPTER::setup` initializes both arm endpoint states to the fixed value `[0, 0, -cfg_->boundArmZ]` and resets the arm MINCO optimizer from those states. The mode-3 task interface fixes intermediate arm Cartesian points, but it does not expose a non-default arm start/end state. Therefore this task does not splice approach/insert/pull/retreat segments and does not claim continuity across independently planned phases.

Read-only source anchors:

- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/se3gcopter.h:934-943`: `iArmSta_` and `fArmSta_` are zeroed and their position column is set to `[0, 0, -boundArmZ]`.
- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/se3gcopter.h:1012-1013`: `armOpt_.reset(iArmSta_, fArmSta_, tN_)` uses those fixed endpoint states.
- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/se3gcopter.h:298-316`: only fixed intermediate arm columns are substituted by `forwardPA`.

No third-party source was modified.
