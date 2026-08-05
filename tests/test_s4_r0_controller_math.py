import numpy as np

from planner_bridge.control.nominal_base_controller import NominalBaseController


def test_hover_wrench_contains_weight_compensation():
    config = {"mass_kg": .98, "gravity_m_s2": 9.81, "kp_pos": [4,4,8], "kd_pos": [3.2,3.2,4.8], "kp_att": [2.8,2.8,1.2], "kd_att": [.22,.22,.16], "inertia_kg_m2": [.018,.018,.032], "max_force_n": 30, "max_torque_nm": [1.5,1.5,.8]}
    cmd = NominalBaseController(config).compute(np.zeros(3), np.zeros(3), np.eye(3), np.zeros(3), np.zeros(3))
    assert np.allclose(cmd.raw_force_world, [0, 0, .98 * 9.81])
    assert not cmd.force_saturated


def test_attitude_torque_is_restoring():
    config = {"mass_kg": 1, "gravity_m_s2": 9.81, "kp_pos": [1,1,1], "kd_pos": [1,1,1], "kp_att": [2,2,2], "kd_att": [1,1,1], "inertia_kg_m2": [1,1,1], "max_force_n": 30, "max_torque_nm": [30,30,30]}
    angle = .1
    rotation = np.array([[1,0,0],[0,np.cos(angle),-np.sin(angle)],[0,np.sin(angle),np.cos(angle)]])
    cmd = NominalBaseController(config).compute(np.zeros(3), np.zeros(3), rotation, np.zeros(3), np.zeros(3))
    assert cmd.clipped_torque_body[0] < 0
