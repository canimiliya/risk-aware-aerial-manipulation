from __future__ import annotations

import numpy as np

from planner_bridge.export.sampling import sample_message


def payload() -> dict:
    return {
        "message_type": "quadrotor_msgs/PolynomialTrajectory",
        "message": {
            "header": {"frame_id": "world"},
            "num_segment": 1,
            "order": [2],
            "time": [2.0],
            "coef_x": [1.0, 0.0, 0.0],
            "coef_y": [0.0, 0.0, 0.0],
            "coef_z": [0.0, 0.0, 1.0],
        },
    }


def test_source_power_order_and_physical_derivatives() -> None:
    sampled = sample_message(payload(), sample_dt=1.0)
    # x=u^2 and z=1, with u=t/2; dx/dt=2u/2=u.
    assert np.allclose(sampled["position"][:, 0], [0.0, 0.25, 1.0])
    assert np.allclose(sampled["velocity"][:, 0], [0.0, 0.5, 1.0])
    assert np.allclose(sampled["acceleration"][:, 0], [0.5, 0.5, 0.5])
    assert sampled["time"][-1] == 2.0


def test_segment_boundary_uses_normalized_local_time() -> None:
    message = payload()["message"]
    message.update({
        "num_segment": 2,
        "order": [1, 1],
        "time": [1.0, 1.0],
        "coef_x": [1.0, 0.0, 1.0, 0.0],
        "coef_y": [0.0, 0.0, 0.0, 0.0],
        "coef_z": [0.0, 0.0, 0.0, 0.0],
    })
    sampled = sample_message({"message_type": payload()["message_type"], "message": message}, sample_dt=0.5)
    assert sampled["segment_id"].tolist() == [0, 0, 0, 1, 1]
    assert np.isfinite(sampled["position"]).all()
