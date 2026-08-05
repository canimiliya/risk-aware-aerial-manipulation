# S4-R0-R2 base/head pytest comparison

Environment: `D:/i3/e/python.exe, same repository test command pytest -q`

| Revision | Passed | Failed |
|---|---:|---:|
| base `741dd82e` | 65 | 13 |
| head `f268ea80` | 79 | 13 |

Head-only failures: `0`
Common failures: `13`
Base-only failures: `0`

## Failed node IDs

### Common
- `planner_bridge/tests/test_export_contract.py::test_all_four_official_exports_pass`
- `planner_bridge/tests/test_export_contract.py::test_contract_metadata_has_no_fake_semantics`
- `tests/audit/test_audit_no_side_effects.py::test_historical_audits_leave_status_and_acceptance_bytes_unchanged`
- `tests/audit/test_check_s0_structure.py::test_current_s0_audit_passes`
- `tests/audit/test_s1_audit_no_side_effects.py::test_default_run_does_not_rewrite_historical_acceptance`
- `tests/audit/test_s1_audit_no_side_effects.py::test_external_output_is_supported`
- `tests/audit/test_s1_audit_no_side_effects.py::test_tracked_output_requires_update_record`
- `tests/audit/test_s2_r0_archival_audit.py::test_archival_passes_without_local_npz`
- `tests/audit/test_s2_r0_archival_audit.py::test_final_acceptance_passes_archival_mode_and_forwards_it`
- `tests/audit/test_s2_r6_patch_reproducibility.py::test_patch_audit_external_output_passes`
- `tests/test_s3_r0_distance_representation.py::test_nominal_point_cloud_count_and_sha_remain_frozen`
- `tests/test_s3_r0_distance_representation.py::test_nominal_point_group_membership_is_frozen`
- `tests/test_s3_r0_protocol.py::test_manifest_hashes_match`

### Head-only
- none

### Base-only
- none
