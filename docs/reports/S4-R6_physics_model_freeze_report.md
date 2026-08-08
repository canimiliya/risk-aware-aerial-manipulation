# S4-R6 Physics Model Freeze Report

TASK:
S4-R6-PHYSICS-MODEL-FREEZE-R1

START_HEAD:
1b207c572c89da21a60ad7d919efcebc8aefc757

END_HEAD:
561ceac6081bafce15138d3b0a0b26fc7e9c2586

FINAL_LABEL:
BLOCKED_S4_R6_TIMESTEP_CONVERGENCE

PHYSICS_MODEL_FROZEN:
false

FREEZE_TAG:
None (blocked; no freeze tag created)

RRRP_NATIVE:
true

FOUR_ROTOR_ACTUATION:
true

TOTAL_SYSTEM_MASS_KG:
1.6499999985098839

PHYSICS_RATE_HZ:
240

STOWED_CONFIGURATION:
[0.0, 1.5707963705062866, 0.0, 0.0]

STOWED_COM_M:
[0.050424257111536176, 5.003177505501864e-09, -0.04196971228714405]

STOWED_TRIM_THRUSTS_N:
[5.358295729648676, 5.3582954693564595, 2.734954263042304, 2.7349545233345207]

STOWED_MAX_ROTOR_UTILIZATION:
0.7290198271630851

APPROACH_CONFIGURATION:
[0.0, 0.0, 0.0, 0.0]

APPROACH_COM_M:
[0.09239392992980042, 0.0, 0.0]

APPROACH_P_MAX_COM_M:
[0.09821211329934483, 0.0, 0.0]

APPROACH_MAX_ROTOR_UTILIZATION:
0.8981477987638947

TIMESTEP_CONVERGENCE:
FAIL

LINEAR_MOMENTUM_RELATIVE_DRIFT:
2.642050708996445e-07

ANGULAR_MOMENTUM_VALIDATED:
false

ENERGY_DIAGNOSTIC:
FAIL

DIRECT_WORLD_FORCE_COMMAND:
false

DIRECT_WORLD_TORQUE_COMMAND:
false

MANUAL_REACTION:
false

ROOT_RUNTIME_STATE_WRITE:
false

JOINT_RUNTIME_POSITION_WRITE:
false

HEADLESS_10000_STEP:
PASS

HEAD_ONLY_FAILURES:
0

HARDWARE_PARAMETER_VALIDATED:
false

CONTACT_DYNAMICS_VALIDATED:
false

CLOSED_LOOP_CONTROL_VALIDATED:
false

S4_READY:
false

## Findings

- 81/81 sampled configurations were geometrically valid for the coarse AABB contract. The selected STOWED configuration is `[0, pi/2, 0, 0]`; its maximum static trim utilization is `0.729020`, passing the 0.80 gate.
- Horizontal APPROACH at P=0, middle, and max has maximum utilization `0.898148`, passing the 0.90 gate. The legacy neutral/straight configuration remains a diagnostic, not the stowed flight pose.
- The timestep audit fails the specified 2%/1% criteria; therefore the physics model is not frozen. The dominant failure is the q1 pulse response, not a parameter adjustment opportunity.
- Linear momentum passes with relative drift `2.642050709e-07`. Angular momentum is explicitly unvalidated. Energy diagnostic completed but did not pass the 0.5% drift criterion.
- No tag was created, no cleanup was performed, no controller/wind/contact/gripper work was started, and S4 remains not ready.

Evidence: `docs/evidence/S4-R6/summary/s4_r6_physics_freeze_readiness.json`, `docs/evidence/S4-R6/runtime/rrrp_hover_trim_envelope.json`, `docs/evidence/S4-R6/runtime/timestep_convergence.json`, `docs/evidence/S4-R6/runtime/linear_momentum_validation.json`, `docs/evidence/S4-R6/runtime/energy_validation.json`, `docs/evidence/S4-R6/runtime/final_actuation_audit.json`, and `docs/evidence/S4-R6/runtime/headless_10000_step_stability.json`.
