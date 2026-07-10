"""Nạp & kiểm tra dữ liệu đầu vào (SPEC.md Bước 3.1)."""

from __future__ import annotations

import json
import math
from pathlib import Path

from binh_sai_do_cao.models.schema import (
    NetworkInput,
    Observation,
    Point,
    ProjectInfo,
    Settings,
)


class InputValidationError(ValueError):
    pass


def _is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def load_dict(data: dict) -> NetworkInput:
    """Parse + validate a raw dict already matching the schema (SPEC.md mục 2)."""
    project_raw = data.get("project", {}) or {}
    project = ProjectInfo(
        name=project_raw.get("name", ""),
        date=project_raw.get("date", ""),
        surveyor=project_raw.get("surveyor", ""),
        computer=project_raw.get("computer", ""),
        checker=project_raw.get("checker", ""),
    )

    settings_raw = data.get("settings", {}) or {}
    settings = Settings(
        adjustment_method=settings_raw.get("adjustment_method", "indirect"),
        closure_formula=settings_raw.get("closure_formula", "k_sqrt_n"),
        k_coefficient_mm=float(settings_raw.get("k_coefficient_mm", 0.3)),
        weight_basis=settings_raw.get("weight_basis", "station_count"),
    )

    known_points_raw = data.get("known_points", []) or []
    if not known_points_raw:
        raise InputValidationError("Phải có ít nhất 1 điểm gốc (known_points rỗng).")

    known_points: list[Point] = []
    seen_known_names: set[str] = set()
    for kp in known_points_raw:
        name = kp.get("name")
        if _is_missing(name):
            raise InputValidationError("Điểm gốc thiếu tên (name).")
        if name in seen_known_names:
            raise InputValidationError(f"Tên điểm gốc bị trùng lặp: '{name}'.")
        seen_known_names.add(name)
        height = kp.get("height_m")
        if _is_missing(height):
            raise InputValidationError(f"Điểm gốc '{name}' thiếu độ cao (height_m).")
        known_points.append(Point(name=name, height_m=float(height)))

    observations_raw = data.get("observations", []) or []
    if not observations_raw:
        raise InputValidationError("Danh sách trị đo (observations) rỗng.")

    observations: list[Observation] = []
    seen_ids: set = set()
    for i, obs in enumerate(observations_raw):
        obs_id = obs.get("id", i + 1)
        if obs_id in seen_ids:
            raise InputValidationError(f"Trị đo trùng id: {obs_id}.")
        seen_ids.add(obs_id)

        from_name = obs.get("from")
        to_name = obs.get("to")
        if _is_missing(from_name) or _is_missing(to_name):
            raise InputValidationError(f"Trị đo id={obs_id} thiếu 'from'/'to'.")
        if from_name == to_name:
            raise InputValidationError(
                f"Trị đo id={obs_id}: 'from' và 'to' trùng nhau ('{from_name}')."
            )

        dh = obs.get("measured_dh_m")
        if _is_missing(dh):
            raise InputValidationError(f"Trị đo id={obs_id} thiếu measured_dh_m.")
        dh = float(dh)
        if math.isnan(dh) or math.isinf(dh):
            raise InputValidationError(f"Trị đo id={obs_id} có measured_dh_m không hợp lệ.")

        stations = obs.get("stations")
        distance_km = obs.get("distance_km")

        if settings.weight_basis == "station_count":
            if _is_missing(stations):
                raise InputValidationError(
                    f"Trị đo id={obs_id} thiếu 'stations' (bắt buộc khi weight_basis=station_count)."
                )
            stations = int(stations)
            if stations <= 0:
                raise InputValidationError(f"Trị đo id={obs_id}: 'stations' phải > 0.")
        elif settings.weight_basis == "distance_km":
            if _is_missing(distance_km):
                raise InputValidationError(
                    f"Trị đo id={obs_id} thiếu 'distance_km' (bắt buộc khi weight_basis=distance_km)."
                )
            distance_km = float(distance_km)
            if distance_km <= 0:
                raise InputValidationError(f"Trị đo id={obs_id}: 'distance_km' phải > 0.")

        observations.append(
            Observation(
                id=obs_id,
                from_=from_name,
                to=to_name,
                measured_dh_m=dh,
                stations=stations,
                distance_km=distance_km,
            )
        )

    # from/to không có trong known_points sẽ được suy ra là điểm mới — không lỗi ở bước này.
    return NetworkInput(
        project=project,
        settings=settings,
        known_points=known_points,
        observations=observations,
    )


def load_json(path: str | Path) -> NetworkInput:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return load_dict(data)
