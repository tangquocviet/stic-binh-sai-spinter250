"""TC-12 (SPEC.md mục 6.1) — lưới 3 điểm, 4 trị đo, đáp số đã tính tay.

Xem lời giải tay trong lịch sử phát triển: hệ phương trình chuẩn
[[3,-2],[-2,3]]·[B,C]ᵀ = [1.000, 4.000]ᵀ cho B=1.000, C=2.000, Mo=10.00mm,
m_B=m_C=10·sqrt(0.6)≈7.746mm.
"""

from __future__ import annotations

import pytest

from binh_sai_do_cao.core.accuracy import compute_accuracy
from binh_sai_do_cao.core.adjustment import run_adjustment
from binh_sai_do_cao.tests.helpers import make_network


def test_tc12_mo_and_m_h_match_hand_solution():
    data = make_network(
        known_points=[("A", 0.0)],
        observations=[
            ("A", "B", 1.000, 1),
            ("A", "C", 2.000, 1),
            ("B", "C", 1.010, 1),
            ("B", "C", 0.990, 1),
        ],
    )
    adjustment = run_adjustment(data)
    assert adjustment.heights_m["B"] == pytest.approx(1.000, abs=1e-6)
    assert adjustment.heights_m["C"] == pytest.approx(2.000, abs=1e-6)

    accuracy = compute_accuracy(data, adjustment)
    assert accuracy.dof == 2
    assert accuracy.mo_mm == pytest.approx(10.00, abs=0.01)
    assert accuracy.m_point_mm["B"] == pytest.approx(7.746, abs=0.01)
    assert accuracy.m_point_mm["C"] == pytest.approx(7.746, abs=0.01)
