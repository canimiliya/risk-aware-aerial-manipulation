# S1-R2 trajectory export contract

This contract is limited to fields actually present in the saved `quadrotor_msgs/PolynomialTrajectory` messages and proven by fixed AM-Planner source. It does not retrofit idealized attitude, joint, phase, or waypoint schemas.

## Required files per run

Each directory under `data/trajectories/S1-R2/` contains `metadata.json`, `raw_trajectory.json`, `raw_trajectory_arm.json`, `sampled_trajectory.csv`, `sampled_trajectory_arm.csv`, `sampled_trajectory.npz`, `sampled_trajectory_arm.npz`, `validation.json`, and `sha256_manifest.txt`.

## Sampling

The exporter samples at 100 Hz (`sample_dt=0.01 s`) and includes exactly one final sample at total duration. Coefficients are evaluated as the source does: descending powers of normalized segment time `u`, with physical derivatives divided by duration powers.

## Validation rules

`planner_bridge.validation.validate_exported_trajectory` checks:

1. message type and field lengths;
2. positive finite segment durations;
3. finite raw coefficients, sample values, and zero NaN/Inf;
4. sampled end time equals the sum of segment durations;
5. raw segment count equals the exported segment count;
6. CSV and NPZ numeric matrices agree to absolute tolerance `1e-12`;
7. first sample is at zero and the final sample is not duplicated;
8. position, velocity, and acceleration continuity at every segment boundary.

The continuity tolerance is `1e-8` in output units. It is a numerical comparison tolerance for the same float64 polynomial evaluated from adjacent pieces; it is not a task or safety tolerance. The source's explicit derivative formulas justify validating position, velocity, and acceleration. No unsupported fields are filled with zero placeholders.
