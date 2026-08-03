# S2-R0 workspace summary recovery

This is a semantic recovery of the missing reviewable summary from the committed S2-R0 preflight acceptance evidence. It is not a byte-level recovery of the original file and it was not recomputed from 100,000 samples.

- Recovery type: `RECOVERED_FROM_COMMITTED_ACCEPTANCE_EVIDENCE`
- Source ref: `c98779e9278f07c4e7f2fcd90d188a294fa65b55`
- Source path: `docs/evidence/S2-R0/final_acceptance/s2_r0_workspace_preflight_audit.json`
- Source object: `checks.workspace_summary`
- Source blob SHA: `0e84ccfb771e33206c02877bf47354470dc0e3f3`
- Recovered path: `outputs/workspace/S2-R0/delta_workspace_100k.json`
- Cross-checks: G-ARM preflight, S2-R0 report, and workspace sampling manifest all agree on the recorded fields.
- Local NPZ: `NOT_PRESENT_LOCAL_ONLY`; no NPZ was downloaded, fabricated, or rehashed.

The recovered JSON contains only the summary object present in the committed audit and does not add unverified sample-level fields.
