# S4-R0-R2 visual crash matrix

Source: `D:\i3\a\aerial_manipulator_v2.usd`
SHA-256: `74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d`

| Probe | Exit | Native crash | Last marker | Result |
|---|---:|---:|---|---|
| P0 | 0 | True | PHASE_STATIC_CAPTURE | FAIL_NATIVE_EXIT |
| P1 | 0 | True | PHASE_ROOT_DEFAULT_UPDATE_COMPLETE | FAIL_NATIVE_EXIT |
| P2 | 0 | True | PHASE_LINK_DEFAULT_UPDATE_COMPLETE | FAIL_NATIVE_EXIT |
| P3 | 0 | True | PHASE_LIVE_LOOP_COMPLETE | FAIL_NATIVE_EXIT |

Minimum trigger: P0: capture_viewport_to_file after the real USD has loaded; P1 reaches 20 default-time root updates before the same capture failure; P2 reaches 20 direct AA_1 link updates before capture failure; P3 reaches 20 live PhysX visual updates before capture failure

P4 was not run because the matrix isolates the direct real-link update route; visual cache feasibility is audited separately.
