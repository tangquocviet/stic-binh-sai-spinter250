"""Dataclass schema cho dữ liệu lưới độ cao (SPEC.md mục 2, 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


AdjustmentMethod = Literal["indirect", "conditional"]
ClosureFormula = Literal["k_sqrt_n", "k_sqrt_L"]
WeightBasis = Literal["station_count", "distance_km"]


@dataclass
class ProjectInfo:
    name: str
    date: str = ""
    surveyor: str = ""
    computer: str = ""
    checker: str = ""


@dataclass
class Settings:
    adjustment_method: AdjustmentMethod = "indirect"
    closure_formula: ClosureFormula = "k_sqrt_n"
    k_coefficient_mm: float = 0.3
    weight_basis: WeightBasis = "station_count"


@dataclass
class Point:
    name: str
    height_m: float


@dataclass
class Observation:
    id: int
    from_: str
    to: str
    measured_dh_m: float
    stations: Optional[int] = None
    distance_km: Optional[float] = None


@dataclass
class NetworkInput:
    project: ProjectInfo
    settings: Settings
    known_points: list[Point] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)

    def known_names(self) -> set[str]:
        return {p.name for p in self.known_points}

    def known_height(self, name: str) -> float:
        for p in self.known_points:
            if p.name == name:
                return p.height_m
        raise KeyError(name)
