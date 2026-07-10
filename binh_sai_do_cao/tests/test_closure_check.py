"""TC-05 → TC-08 (SPEC.md mục 6.1)."""

from __future__ import annotations

import pytest

from binh_sai_do_cao.core.closure_check import check_closure
from binh_sai_do_cao.core.loop_finder import LoopEdgeUse, find_fundamental_cycles, Loop
from binh_sai_do_cao.models.schema import Observation, Settings
from binh_sai_do_cao.tests.helpers import make_network


def _dummy_loop(wh_m: float, stations: int) -> Loop:
    obs = Observation(id=1, from_="X", to="Y", measured_dh_m=0.0, stations=stations)
    return Loop(index=1, path=["X", "Y", "X"], edges=[LoopEdgeUse(obs, True)], wh_m=wh_m)


def test_tc05_wh_simple_loop_matches_algebraic_sum():
    data = make_network(
        known_points=[("A", 10.0)],
        observations=[
            ("A", "B", 1.000, 5),
            ("B", "C", 2.000, 5),
            ("C", "A", -2.999, 5),  # tổng = 0.001 m
        ],
    )
    loops = find_fundamental_cycles(data)
    assert len(loops) == 1
    assert loops[0].wh_m == pytest.approx(0.001, abs=1e-6)


def test_tc06_wh_gh_formula_k_sqrt_n():
    # n=120, k=0.3 (khớp ví dụ SPEC.md mục 2: 2 trị đo MC2<->MC6, 61+59=120 trạm)
    data = make_network(
        known_points=[("MC2", 0.7614), ("MC6", 1.7587)],
        observations=[
            ("MC2", "MC6", 0.9973, 61),
            ("MC6", "MC2", -0.9975, 59),
        ],
    )
    loops = find_fundamental_cycles(data)
    assert len(loops) == 1
    result = check_closure(loops[0], data.settings)
    assert result.wh_gh_mm == pytest.approx(3.286, abs=0.01)


def test_tc07_near_limit_flag_when_ratio_at_least_0_9():
    loop = _dummy_loop(wh_m=0.60 / 1000, stations=4)  # k*sqrt(4)=0.6mm -> tỉ lệ = 1.0
    result = check_closure(loop, Settings(k_coefficient_mm=0.3))
    assert result.status == "Đạt"
    assert result.flag == "sát giới hạn"


def test_tc08_over_limit_status_khong_dat():
    loop = _dummy_loop(wh_m=5.0 / 1000, stations=100)  # k*sqrt(100)=3.0mm
    result = check_closure(loop, Settings(k_coefficient_mm=0.3))
    assert result.wh_gh_mm == pytest.approx(3.0, abs=1e-9)
    assert result.status == "Không đạt"
    assert result.flag == "Vượt giới hạn"
