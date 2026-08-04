from __future__ import annotations


def phase_for_progress(progress: float) -> tuple[int, str, float]:
    p = min(max(float(progress), 0.0), 1.0)
    if p < 1.0 / 3.0:
        return 0, "APPROACH", p * 3.0
    if p < 2.0 / 3.0:
        return 1, "TRANSFER", (p - 1.0 / 3.0) * 3.0
    return 2, "RETREAT", (p - 2.0 / 3.0) * 3.0
