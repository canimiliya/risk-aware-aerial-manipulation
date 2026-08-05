"""Deterministic metric calculations for S4-R0 evidence."""

from __future__ import annotations

import numpy as np


def rmse(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(values * values)))


def vector_rmse(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    return rmse(np.linalg.norm(values, axis=-1))


def max_norm(values: np.ndarray) -> float:
    return float(np.max(np.linalg.norm(np.asarray(values, dtype=float), axis=-1)))


def settling_time(time_s: np.ndarray, error_norm: np.ndarray, threshold: float, hold_s: float) -> float | None:
    time_s = np.asarray(time_s, dtype=float)
    error_norm = np.asarray(error_norm, dtype=float)
    for index in range(len(time_s)):
        end = time_s[index] + hold_s
        stop = int(np.searchsorted(time_s, end, side="left"))
        if stop <= index or np.all(error_norm[index:stop] <= threshold):
            return float(time_s[index])
    return None


def saturation_summary(time_s: np.ndarray, flags: np.ndarray, dt: float) -> dict[str, float | bool]:
    flags = np.asarray(flags, dtype=bool)
    ratio = float(np.mean(flags)) if flags.size else 0.0
    longest = 0
    current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        longest = max(longest, current)
    return {"ratio": ratio, "longest_duration_s": float(longest * dt), "continuous_over_0_5s": bool(longest * dt > 0.5)}
