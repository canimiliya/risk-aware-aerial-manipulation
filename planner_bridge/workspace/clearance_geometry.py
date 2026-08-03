from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Box:
    name: str
    center: np.ndarray
    size: np.ndarray

    @property
    def lower(self) -> np.ndarray:
        return self.center - self.size / 2.0

    @property
    def upper(self) -> np.ndarray:
        return self.center + self.size / 2.0


def point_box_distance(point: np.ndarray, box: Box) -> float:
    delta = np.maximum(np.maximum(box.lower - point, 0.0), point - box.upper)
    return float(np.linalg.norm(delta))


def segment_box_distance(start: np.ndarray, end: np.ndarray, box: Box, samples: int = 33) -> float:
    points = np.linspace(start, end, samples)
    return min(point_box_distance(point, box) for point in points)


def clearance_for_links(link_points: dict[str, np.ndarray], boxes: list[Box]) -> float:
    distances: list[float] = []
    for segments in (link_points["upper_segments"], link_points["lower_segments"]):
        for start, end in segments:
            distances.extend(segment_box_distance(start, end, box) for box in boxes)
    return float(min(distances)) if distances else float("inf")


def proxy_clearance(point: np.ndarray, boxes: list[Box], radius: float = 0.0) -> float:
    return min(point_box_distance(point, box) - radius for box in boxes)
