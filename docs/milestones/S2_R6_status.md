# S2-R6 status

- S2-R6: `PASS_WITH_LIMITATIONS`
- Result label: `PASS_S2_R6_WITH_LIMITATIONS`
- S2: `PASS_WITH_LIMITATIONS`
- S3: `NOT_STARTED`
- S4-S8: `FROZEN`

The default-off Cartesian execution-envelope barrier was implemented in an independent AM-Planner clone, built with the retained official runtime, and accepted by the S2-R6 evidence audit (`PASS / errors=0 / warnings=0`). The selected `100w0` candidate and all four formal variants pass the retained joint, full-body clearance, direction, finite-output, and multi-rate checks. Patch-only reproduction added the complete five-path patch, targeted clean build/devel evidence, ABI checks, and nominal/repeat runtime evidence. S2-R6 is now closed with limitations as part of the ordinary merge of PR #10 (`8df48d2b4edc0d219ad8eb3a9b211fb291daf2ab`).

The retained limitations are: S2-R0 summary recovery is semantic rather than byte recovery; the local-only NPZ was not regenerated; full-body clearance uses a provisional proxy and is not mesh-exact collision proof; the soft barrier is not a formal hard-constraint proof; and wind, contact, and closed-loop control were not executed.
