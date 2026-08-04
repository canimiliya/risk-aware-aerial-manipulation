from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PlaybackRecorder:
    """Small deterministic recorder shared by offline and Isaac adapters."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(self, record: dict[str, Any]) -> None:
        self.records.append(dict(record))

    def write(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps({"protocol": "S3-R0-playback-log-v1", "records": self.records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
