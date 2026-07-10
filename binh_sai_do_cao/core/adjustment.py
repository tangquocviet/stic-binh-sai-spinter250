"""Bình sai gián tiếp toàn mạng lưới bằng LSQ (SPEC.md Bước 3.3).

Ghi chú triển khai: spec mô tả ẩn số là số hiệu chỉnh X quanh độ cao gần
đúng H0 (H = H0 + X). Vì mô hình thủy chuẩn là tuyến tính hoàn toàn theo H
(không cần tuyến tính hoá), chọn H0 = 0 cho mọi điểm mới cho ra đúng cùng
nghiệm X ≡ H như khi chọn H0 khác — nên ở đây giải trực tiếp cho H của các
điểm mới, tương đương về toán học với phương án H0+X của spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from binh_sai_do_cao.models.schema import NetworkInput, Observation


class AdjustmentError(ValueError):
    pass


@dataclass
class AdjustmentResult:
    unknown_names: list[str]
    unknown_index: dict[str, int]
    A: np.ndarray
    P: np.ndarray  # vector trọng số (đường chéo), c = 1
    L: np.ndarray
    X: np.ndarray
    V: np.ndarray  # số hiệu chỉnh từng trị đo (m), theo đúng thứ tự observations
    AtPA: np.ndarray
    heights_m: dict[str, float] = field(default_factory=dict)  # toàn bộ điểm (gốc + mới)
    corrections_m: dict[int, float] = field(default_factory=dict)  # obs.id -> V (m)
    adjusted_dh_m: dict[int, float] = field(default_factory=dict)  # obs.id -> h_BS (m)


def _collect_unknown_names(data: NetworkInput) -> list[str]:
    known_names = data.known_names()
    seen: set[str] = set()
    unknown_names: list[str] = []
    for obs in data.observations:
        for name in (obs.from_, obs.to):
            if name not in known_names and name not in seen:
                seen.add(name)
                unknown_names.append(name)
    return unknown_names


def _weight(obs: Observation, weight_basis: str) -> float:
    denom = obs.distance_km if weight_basis == "distance_km" else obs.stations
    return 1.0 / denom


def run_adjustment(data: NetworkInput) -> AdjustmentResult:
    known_heights = {p.name: p.height_m for p in data.known_points}
    unknown_names = _collect_unknown_names(data)
    unknown_index = {name: i for i, name in enumerate(unknown_names)}

    num_unknowns = len(unknown_names)
    num_obs = len(data.observations)
    if num_unknowns >= num_obs:
        raise AdjustmentError(
            f"Số ẩn số ({num_unknowns}) >= số trị đo ({num_obs}) — lưới không có "
            "trị đo dư thừa (hệ vô định). Cần đo thêm để bình sai."
        )

    A = np.zeros((num_obs, num_unknowns))
    P = np.zeros(num_obs)
    L = np.zeros(num_obs)

    for row, obs in enumerate(data.observations):
        L_k = obs.measured_dh_m
        if obs.to in known_heights:
            L_k -= known_heights[obs.to]
        else:
            A[row, unknown_index[obs.to]] += 1.0
        if obs.from_ in known_heights:
            L_k += known_heights[obs.from_]
        else:
            A[row, unknown_index[obs.from_]] += -1.0
        L[row] = L_k
        P[row] = _weight(obs, data.settings.weight_basis)

    AtP = A.T * P  # (num_unknowns, num_obs), mỗi cột nhân trọng số dòng tương ứng
    AtPA = AtP @ A
    AtPL = AtP @ L

    try:
        X = np.linalg.solve(AtPA, AtPL)
    except np.linalg.LinAlgError as exc:
        raise AdjustmentError(
            "Ma trận (AᵀPA) suy biến — không giải được hệ phương trình chuẩn. "
            "Kiểm tra lưới có bị phân mảnh ẩn hoặc thiếu trị đo dư thừa không."
        ) from exc

    V = A @ X - L

    heights_m = dict(known_heights)
    for name, idx in unknown_index.items():
        heights_m[name] = float(X[idx])

    corrections_m = {obs.id: float(V[row]) for row, obs in enumerate(data.observations)}
    adjusted_dh_m = {
        obs.id: float(obs.measured_dh_m + V[row]) for row, obs in enumerate(data.observations)
    }

    return AdjustmentResult(
        unknown_names=unknown_names,
        unknown_index=unknown_index,
        A=A,
        P=P,
        L=L,
        X=X,
        V=V,
        AtPA=AtPA,
        heights_m=heights_m,
        corrections_m=corrections_m,
        adjusted_dh_m=adjusted_dh_m,
    )
