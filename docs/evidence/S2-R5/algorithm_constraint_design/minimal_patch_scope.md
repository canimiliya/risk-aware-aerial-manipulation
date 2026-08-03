# Minimal patch scope

This document is a design boundary only. The smallest future patch would be confined to the official algorithm's arm objective path and its tests/configuration, with no changes to IK/FK, FlatnessMap, URDF/Xacro, ROS, GPU environment, obstacle/proxy geometry, or task-level output post-processing.

The patch should add one explicit constraint mode/configuration, preserve the default behavior when disabled, and expose raw objective/gradient diagnostics. It should not add fabricated q fields to the mode-3 ABI. The S2-R5 branch contains no such algorithm patch.
