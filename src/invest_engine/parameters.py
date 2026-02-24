from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class ParameterSet:
    name: str
    region: str
    valid_from: date
    valid_to: date
    params: dict


class ParameterStore:
    def __init__(self, path: str | Path):
        raw = json.loads(Path(path).read_text())
        self._sets = [
            ParameterSet(
                name=s["name"],
                region=s["region"],
                valid_from=date.fromisoformat(s["valid_from"]),
                valid_to=date.fromisoformat(s["valid_to"]),
                params=s["params"],
            )
            for s in raw["parameter_sets"]
        ]

    def resolve(self, region: str, year: int, name: str | None = None) -> ParameterSet:
        dt = date(year, 1, 1)
        candidates = [
            s
            for s in self._sets
            if s.region == region and s.valid_from <= dt <= s.valid_to and (name is None or s.name == name)
        ]
        if not candidates:
            raise ValueError(f"No parameter set found for region={region}, year={year}, name={name}")
        return candidates[0]
