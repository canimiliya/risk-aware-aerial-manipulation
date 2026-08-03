# Risk assessment

- Cartesian envelope risk: an approximate envelope may admit a point whose official IK is outside the branch. Mitigation: conservative construction plus independent dense official IK/FK validation.
- IK penalty risk: branch switching or singular gradients can destabilize L-BFGS. Mitigation: explicit branch continuity and gradient tests.
- More fixed points risk: as shown by Round2, adding task points can move the unconstrained polynomial overshoot rather than remove it. Stop at the three-round/25-point bound.
- Endpoint risk: the official constructor hard-codes both arm endpoint states to `[0,0,-boundArmZ]`; phase splitting is not supported under the current contract.
- Acceptance risk: output clipping, proxy reduction, gate lowering, or historical-evidence replacement would invalidate the result and are prohibited.
