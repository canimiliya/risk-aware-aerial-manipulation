from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/s4_r6_r3_revolute_dynamics_isolation.py"


def test_r6_r3_script_and_outputs_are_scoped():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "S4-R6-R3-REVOLUTE-DYNAMICS-ISOLATION-R1" in text
    assert "S4_R6_R3_REVOLUTE_NUMERICS_RESOLVED" in text
    assert "BLOCKED_S4_R6_R3_PHYSX_REVOLUTE_SOLVER" in text
    assert "physics_model_frozen" in text


def test_r6_r3_does_not_author_source_asset_or_frozen_tag():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "Export" not in text
    assert "s4-physics-model-v1" not in text
    assert "BLOCKED_S4_R6_TIMESTEP_CONVERGENCE" in text
    assert "BLOCKED_S4_R6_R2_SOLVER_CONVERGENCE" in text
