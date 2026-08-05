# S3 final acceptance

- decision：`PASS_S3_WITH_LIMITATIONS`
- reviewed PR：`#13`
- reviewed technical Head：`85bbb04ceefe5897826f6892fc9ff408b8cf0a5b`
- merge method：普通 `merge`；治理 commit、merge commit 和最终 `main` SHA 在对应动作完成后回填。
- formal progress after merge：`4/9≈44%`
- formal close date：`2026-08-05`
- S4 status：`FROZEN`；S4–S8 均未启动。

## Accepted evidence

Protocol, Isaac asset import, scene load, kinematic playback, arm FK, world EE FK, exact clearance, S2 state-replay clearance delta, S2 point containment, framewise conservative order, Isaac AABB read-back, PNG contract and local chronological video contract all passed. Final readiness remained `READY_FOR_S3_FINAL_REVIEW` with empty errors and warnings before this formal closure.

The corrected Column contract is center `[0,0,0.73]`, size `[0.12,0.12,1.30]`, with world z bounds `[0.08,1.38] m`; the other three obstacles and all S2 frozen artifacts were not changed. The R8 visual evidence contains real Isaac GUI dangerous-time screenshots and two local chronological nominal/repeat videos covering frame `329`, time `1.3708333333333333 s`, and final frame `1254`.

## Accepted limitations

- S3 uses kinematic playback articulation; there is no full closed-chain dynamics.
- The scene uses a provisional proxy / AABB envelope. Distance is exact for the frozen sampled proxy, not a mesh-exact safety proof.
- No wind, task contact, closed-loop control, ROS/ROS2 real-time bridge, or training was performed.
- Local temporal videos are represented in the repository by manifest, SHA and metadata only; the video files remain local.
- Six pre-existing S0/S1/S2 historical audit/archive-dependent test failures are retained and were not caused by this governance closure.
