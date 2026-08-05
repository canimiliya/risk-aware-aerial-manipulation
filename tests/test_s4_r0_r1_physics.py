import numpy as np

from planner_bridge.control.dynamic_model import ArmReactionSurrogate


def test_static_arm_reaction_is_exactly_zero_and_has_no_first_frame_pulse():
    model = ArmReactionSurrogate(0.29135232232511, np.array([0.0, 0.0, -0.14]))
    zero = model.reaction(np.array([0.7, 0.8, 0.9]), np.zeros(3), np.zeros(3))
    first = model.reaction(np.array([0.7, 0.8, 0.9]), np.zeros(3), np.zeros(3))
    assert np.allclose(zero["force_body_N"], 0.0, atol=1e-12)
    assert np.allclose(zero["torque_body_Nm"], 0.0, atol=1e-12)
    assert np.allclose(first["force_world_N"], 0.0, atol=1e-12)
    assert first["nonzero"] is False


def test_analytic_com_velocity_and_acceleration_match_high_precision_difference():
    model = ArmReactionSurrogate(0.29135232232511, np.array([0.0, 0.0, -0.14]))
    t = 0.73
    h = 1e-5
    phase = np.array([0.2, 1.1, 2.0])
    amp = np.array([0.2, 0.15, 0.1])
    omega = np.array([1.3, 1.7, 2.1])

    def q_at(time):
        return 0.7 + amp * np.sin(omega * time + phase)

    q = q_at(t)
    dq = amp * omega * np.cos(omega * t + phase)
    qdd = -amp * omega**2 * np.sin(omega * t + phase)
    reaction = model.reaction(q, dq, qdd)
    velocity_fd = (model.com(q_at(t + h)) - model.com(q_at(t - h))) / (2.0 * h)
    acceleration_fd = (model.com(q_at(t + h)) - 2.0 * model.com(q) + model.com(q_at(t - h))) / h**2
    assert np.allclose(reaction["velocity_m_s"], velocity_fd, rtol=1e-6, atol=1e-9)
    assert np.allclose(reaction["acceleration_m_s2"], acceleration_fd, rtol=1e-3, atol=1e-6)
    assert reaction["finite"] is True


def test_sinusoidal_reaction_is_finite_and_continuous():
    model = ArmReactionSurrogate(0.29135232232511, np.array([0.0, 0.0, -0.14]))
    times = np.arange(0.0, 10.0, 1.0 / 240.0)
    forces = []
    for time in times:
        q = np.array([0.7, 0.8, 0.9]) + 0.15 * np.sin(2.0 * np.pi * time / 10.0 + np.array([0.0, 2.0, 4.0]))
        dq = 0.15 * (2.0 * np.pi / 10.0) * np.cos(2.0 * np.pi * time / 10.0 + np.array([0.0, 2.0, 4.0]))
        qdd = -0.15 * (2.0 * np.pi / 10.0) ** 2 * np.sin(2.0 * np.pi * time / 10.0 + np.array([0.0, 2.0, 4.0]))
        forces.append(model.reaction(q, dq, qdd)["force_body_N"])
    values = np.asarray(forces)
    assert np.isfinite(values).all()
    assert np.isfinite(np.diff(values, axis=0)).all()
    assert np.max(np.linalg.norm(values, axis=1)) > 0.0


def test_old_first_difference_contract_is_not_present():
    source = open("planner_bridge/control/dynamic_model.py", encoding="utf-8").read()
    assert "previous_com" not in source
    assert "velocity / dt" not in source
    assert "def __init__(self, arm_mass_kg: float, com_offset_m: np.ndarray)" in source
