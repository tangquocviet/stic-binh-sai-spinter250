"""Tiện ích dựng NetworkInput nhỏ gọn cho unit test."""

from __future__ import annotations

from binh_sai_do_cao.models.schema import NetworkInput, Observation, Point, ProjectInfo, Settings


def make_network(
    known_points: list[tuple[str, float]],
    observations: list[tuple[str, str, float, int]],
    k_coefficient_mm: float = 0.3,
    weight_basis: str = "station_count",
) -> NetworkInput:
    return NetworkInput(
        project=ProjectInfo(name="TEST"),
        settings=Settings(k_coefficient_mm=k_coefficient_mm, weight_basis=weight_basis),
        known_points=[Point(name=n, height_m=h) for n, h in known_points],
        observations=[
            Observation(id=i + 1, from_=f, to=t, measured_dh_m=dh, stations=st)
            for i, (f, t, dh, st) in enumerate(observations)
        ],
    )
