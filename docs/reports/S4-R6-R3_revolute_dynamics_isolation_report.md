# S4-R6-R3 Revolute Dynamics Isolation Report

TASK: S4-R6-R3-REVOLUTE-DYNAMICS-ISOLATION-R1

START_HEAD: fb8dbc7c537aedfa10c8c50a38e8892c13bcde00

END_HEAD: fb8dbc7c537aedfa10c8c50a38e8892c13bcde00

FINAL_LABEL: BLOCKED_S4_R6_R3_PHYSX_REVOLUTE_SOLVER

Q1_ROOT_CAUSE: PHYSX_REVOLUTE_SOLVER_OR_NATIVE_REVOLUTE_INTEGRATION

SINGLE_1R_CONVERGENCE: FAIL

FIXED_RRRP_CONVERGENCE: FAIL

FLOATING_RRRP_CONVERGENCE: FAIL

Q1_FORWARD_DYNAMICS_REFERENCE_QDD: 457.7916664144857

Q1_FIRST_STEP_240_QDD: 105.27466535568237

Q1_FIRST_STEP_480_QDD: 105.27466535568237

Q1_FIRST_STEP_960_QDD: 105.27466535568237

Q1_FIRST_STEP_1920_QDD: 105.27466535568237

MASS_MATRIX_POSITIVE_DEFINITE: true

MASS_MATRIX_CONDITION_NUMBER: 1412.3752857010977

Q1_EFFECTIVE_INERTIA: 0.0004368799492713341

Q1_LIMIT_HIT: false

Q1_VELOCITY_CLAMP_HIT: false

Q1_HIDDEN_DRIVE_FOUND: false

ENERGY_SINGLE_1R: {"240": {"label": "single_1r", "rate_hz": 240, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 8.548139681099861e-07, "min_energy_j": 8.492988454664432e-07, "max_energy_j": 8.548139681099861e-07, "relative_energy_drift": 0.006451839639140412, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}, "480": {"label": "single_1r", "rate_hz": 480, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 8.548600339057072e-07, "min_energy_j": 8.493414988606377e-07, "max_energy_j": 8.548600339057072e-07, "relative_energy_drift": 0.006455483735572736, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}, "960": {"label": "single_1r", "rate_hz": 960, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 8.548831103460287e-07, "min_energy_j": 8.493606374358402e-07, "max_energy_j": 8.548831103460287e-07, "relative_energy_drift": 0.006459915798258354, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}, "1920": {"label": "single_1r", "rate_hz": 1920, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 8.548947106139026e-07, "min_energy_j": 8.493800209525027e-07, "max_energy_j": 8.548947106139026e-07, "relative_energy_drift": 0.0064507238060226854, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}}

ENERGY_FIXED_RRRP: {"240": {"label": "fixed_rrrp", "rate_hz": 240, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 1.170531265811143e-07, "min_energy_j": 1.160866791198574e-07, "max_energy_j": 1.170531265811143e-07, "relative_energy_drift": 0.008256485661552874, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}, "480": {"label": "fixed_rrrp", "rate_hz": 480, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 1.1704000627122048e-07, "min_energy_j": 1.1608745973135305e-07, "max_energy_j": 1.1704000627122048e-07, "relative_energy_drift": 0.008138640540227508, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}, "960": {"label": "fixed_rrrp", "rate_hz": 960, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 1.1703359655274259e-07, "min_energy_j": 1.161137085832845e-07, "max_energy_j": 1.1719492642253832e-07, "relative_energy_drift": 0.009238525270532445, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}, "1920": {"label": "fixed_rrrp", "rate_hz": 1920, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 1.170301483047403e-07, "min_energy_j": 1.163553445646034e-07, "max_energy_j": 1.1864383460033849e-07, "relative_energy_drift": 0.019554705081428876, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}}

ENERGY_FLOATING_RRRP: {"240": {"label": "floating_rrrp", "rate_hz": 240, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 2.0746819036648223e-05, "min_energy_j": 2.054026169255062e-05, "max_energy_j": 2.0746819036648223e-05, "relative_energy_drift": 0.009956097063975386, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}, "480": {"label": "floating_rrrp", "rate_hz": 480, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 2.0748562408525138e-05, "min_energy_j": 2.0542097678562003e-05, "max_energy_j": 2.0748562408525138e-05, "relative_energy_drift": 0.009950796874404316, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}, "960": {"label": "floating_rrrp", "rate_hz": 960, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 2.0749433377964257e-05, "min_energy_j": 2.0542949610385054e-05, "max_energy_j": 2.0749433377964257e-05, "relative_energy_drift": 0.009951296684490997, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}, "1920": {"label": "floating_rrrp", "rate_hz": 1920, "gravity": false, "drive": false, "damping": false, "friction": false, "collision": false, "external_force": false, "initial_energy_j": 2.0749868457393294e-05, "min_energy_j": 2.0543217915752263e-05, "max_energy_j": 2.0749868457393294e-05, "relative_energy_drift": 0.009959125382667211, "finite": true, "energy_pass": false, "initial_joint_velocity_seed_rad_s": 0.03}}

ASSET_BUG_FOUND: false

PHYSX_SOLVER_LIMITATION_SUSPECTED: true

PHYSICS_MODEL_FROZEN: false

CLEANUP_ALLOWED: false

## Scope and method

- The source USD, RRRP design, mass, inertia, rotor, motor, and gate thresholds were not modified.
- The single 1R model is an in-memory clone of the authored fixed-base, q1, and link1 specs. It was not exported.
- Isaac Sim 5.1 public Python binding does not expose `computeJointAcceleration()` on the articulation view. The oracle is therefore `M(q0)^-1 * tau`, using the native generalized mass matrix readback; this limitation is explicit in evidence.
- Historical R6 and R6-R2 blockers remain preserved and were not overwritten.
