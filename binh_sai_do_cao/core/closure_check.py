"""Tính Wh, Wh(gh), kết luận QC vòng khép (SPEC.md Bước 3.2)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from binh_sai_do_cao.core.loop_finder import Loop
from binh_sai_do_cao.models.schema import Settings

NEAR_LIMIT_RATIO = 0.9

STATUS_OK = "Đạt"
STATUS_FAIL = "Không đạt"
FLAG_NEAR_LIMIT = "sát giới hạn"
FLAG_OVER_LIMIT = "Vượt giới hạn"


@dataclass
class ClosureResult:
    loop: Loop
    wh_mm: float
    wh_gh_mm: float
    status: str
    flag: str | None

    @property
    def ratio(self) -> float:
        if self.wh_gh_mm == 0:
            return math.inf if self.wh_mm != 0 else 0.0
        return abs(self.wh_mm) / self.wh_gh_mm


def compute_wh_gh_mm(loop: Loop, settings: Settings) -> float:
    if settings.closure_formula == "k_sqrt_L":
        n = loop.total_distance_km
        if n is None:
            raise ValueError(
                f"Vòng {loop.path_str}: thiếu distance_km để tính Wh(gh) theo k_sqrt_L."
            )
    else:
        n = loop.total_stations
        if n is None:
            raise ValueError(
                f"Vòng {loop.path_str}: thiếu stations để tính Wh(gh) theo k_sqrt_n."
            )
    return settings.k_coefficient_mm * math.sqrt(n)


def check_closure(loop: Loop, settings: Settings) -> ClosureResult:
    wh_mm = loop.wh_m * 1000.0
    wh_gh_mm = compute_wh_gh_mm(loop, settings)

    if abs(wh_mm) <= wh_gh_mm:
        status = STATUS_OK
        ratio = abs(wh_mm) / wh_gh_mm if wh_gh_mm > 0 else 0.0
        flag = FLAG_NEAR_LIMIT if ratio >= NEAR_LIMIT_RATIO else None
    else:
        status = STATUS_FAIL
        flag = FLAG_OVER_LIMIT

    return ClosureResult(loop=loop, wh_mm=wh_mm, wh_gh_mm=wh_gh_mm, status=status, flag=flag)


def check_all_closures(loops: list[Loop], settings: Settings) -> list[ClosureResult]:
    return [check_closure(loop, settings) for loop in loops]
