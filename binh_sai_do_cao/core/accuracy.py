"""Đánh giá độ chính xác lưới sau bình sai (SPEC.md Bước 3.4)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from binh_sai_do_cao.core.adjustment import AdjustmentError, AdjustmentResult
from binh_sai_do_cao.models.schema import NetworkInput


@dataclass
class AccuracyResult:
    mo_mm: float
    dof: int
    qxx: np.ndarray
    m_point_mm: dict[str, float] = field(default_factory=dict)  # tất cả điểm (gốc = 0.0)
    m_obs_mm: dict[int, float] = field(default_factory=dict)  # obs.id -> SSTP (mm)


def compute_accuracy(data: NetworkInput, adjustment: AdjustmentResult) -> AccuracyResult:
    num_obs = len(data.observations)
    num_unknowns = len(adjustment.unknown_names)
    dof = num_obs - num_unknowns
    if dof <= 0:
        raise AdjustmentError(
            f"Không có trị đo dư thừa (số trị đo={num_obs}, số ẩn={num_unknowns}, "
            "bậc tự do<=0) — không tính được Mo."
        )

    v_mm = adjustment.V * 1000.0
    vtpv_mm2 = float(np.sum(adjustment.P * v_mm**2))
    mo_mm = math.sqrt(vtpv_mm2 / dof)

    qxx = np.linalg.inv(adjustment.AtPA)

    m_point_mm: dict[str, float] = {p.name: 0.0 for p in data.known_points}
    for name, idx in adjustment.unknown_index.items():
        variance = max(0.0, qxx[idx, idx])
        m_point_mm[name] = mo_mm * math.sqrt(variance)

    m_obs_mm: dict[int, float] = {}
    for row, obs in enumerate(data.observations):
        f = adjustment.A[row, :]
        variance = max(0.0, float(f @ qxx @ f))
        m_obs_mm[obs.id] = mo_mm * math.sqrt(variance)

    return AccuracyResult(mo_mm=mo_mm, dof=dof, qxx=qxx, m_point_mm=m_point_mm, m_obs_mm=m_obs_mm)


@dataclass
class AccuracyExtremes:
    point_max_name: str
    point_max_mm: float
    point_min_name: str
    point_min_mm: float
    obs_max_pair: tuple[str, str]
    obs_max_mm: float
    obs_min_pair: tuple[str, str]
    obs_min_mm: float


def compute_extremes(data: NetworkInput, accuracy: AccuracyResult) -> AccuracyExtremes:
    new_point_names = set(accuracy.m_point_mm) - data.known_names()
    if not new_point_names:
        raise ValueError("Không có điểm mới nào để đánh giá SSTP.")

    point_items = sorted((accuracy.m_point_mm[n], n) for n in new_point_names)
    point_min_val, point_min_name = point_items[0]
    point_max_val, point_max_name = point_items[-1]

    obs_items = []
    for obs in data.observations:
        obs_items.append((accuracy.m_obs_mm[obs.id], (obs.from_, obs.to)))
    obs_items.sort(key=lambda t: t[0])
    obs_min_val, obs_min_pair = obs_items[0]
    obs_max_val, obs_max_pair = obs_items[-1]

    return AccuracyExtremes(
        point_max_name=point_max_name,
        point_max_mm=point_max_val,
        point_min_name=point_min_name,
        point_min_mm=point_min_val,
        obs_max_pair=obs_max_pair,
        obs_max_mm=obs_max_val,
        obs_min_pair=obs_min_pair,
        obs_min_mm=obs_min_val,
    )
