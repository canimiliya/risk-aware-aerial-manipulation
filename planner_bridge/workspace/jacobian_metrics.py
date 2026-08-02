from __future__ import annotations

import numpy as np

from .delta_arm_model import DeltaArmModel


def jacobian_metrics(model: DeltaArmModel, q: np.ndarray) -> dict[str, float]:
    jac = model.jacobian(q)
    singular_values = np.linalg.svd(jac, compute_uv=False)
    minimum = float(np.min(singular_values))
    maximum = float(np.max(singular_values))
    return {
        "min_singular_value": minimum,
        "max_singular_value": maximum,
        "condition_number": float(maximum / minimum) if minimum > 0 else float("inf"),
    }


def batch_jacobian_metrics(model: DeltaArmModel, qs: np.ndarray) -> dict[str, np.ndarray]:
    mins = np.full(len(qs), np.nan)
    conds = np.full(len(qs), np.nan)
    for i, q in enumerate(qs):
        try:
            metrics = jacobian_metrics(model, q)
        except ValueError:
            continue
        mins[i] = metrics["min_singular_value"]
        conds[i] = metrics["condition_number"]
    return {"min_singular_value": mins, "condition_number": conds}
