# S2-R0 坐标系合同

| frame | parent | transform | units | source | mode |
|---|---|---|---|---|---|
| W | — | world origin | m/rad | S2-R0 contract | dynamic in full planning |
| B | W | vehicle pose | m/rad | not available in S2-R0 | dynamic, not executed |
| A0 | B | `[0,0,-0.05]`, RPY `[0,0,-1.5708]` | m/rad | official `arm.xacro::ini_connect` | static |
| E | A0 | official closed-chain `FK_kin(q)` | m | official `delta_display.cpp` | dynamic |
| T | E | axis `[1,0,0]` for horizontal task candidate | unitless | `PROVISIONAL_S2_ASSUMPTION` | static candidate |
| C | W | obstacle/crossarm proxy geometry | m | `PROVISIONAL_S2_ASSUMPTION` | static scene |

`A0→E` is the position-only mapping proven by the official Delta source. Full orientation, tool length and body pose are intentionally not inferred from the `PolynomialTrajectory` message.
