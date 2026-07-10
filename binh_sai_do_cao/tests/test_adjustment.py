"""TC-09 → TC-11 (SPEC.md mục 6.1)."""

from __future__ import annotations

import pytest

from binh_sai_do_cao.core.adjustment import AdjustmentError, run_adjustment
from binh_sai_do_cao.tests.helpers import make_network


def test_tc09_minimal_network_two_known_points_no_redundancy_at_that_obs():
    # 2 điểm gốc, 1 trị đo duy nhất giữa chúng, khớp hoàn toàn với chênh cao gốc.
    data = make_network(
        known_points=[("A", 10.000), ("B", 11.500)],
        observations=[("A", "B", 1.500, 5)],
    )
    result = run_adjustment(data)
    assert len(result.unknown_names) == 0
    obs_id = data.observations[0].id
    assert result.corrections_m[obs_id] == pytest.approx(0.0, abs=1e-9)


def test_tc10_single_unknown_two_observations_weighted_mean():
    # 1 điểm mới P, 2 trị đo từ 2 điểm gốc khác nhau -> P là trung bình trọng số P=1/n.
    data = make_network(
        known_points=[("A", 10.0), ("B", 10.5)],
        observations=[
            ("A", "P", 1.0, 1),   # ngụ ý P = 11.0, trọng số w=1/1=1
            ("B", "P", 0.4, 4),   # ngụ ý P = 10.9, trọng số w=1/4=0.25
        ],
    )
    result = run_adjustment(data)
    expected_p = (1 * 11.0 + 0.25 * 10.9) / (1 + 0.25)
    assert result.heights_m["P"] == pytest.approx(expected_p, abs=1e-9)


def test_tc11_underdetermined_system_raises_clear_error():
    data = make_network(
        known_points=[("A", 10.0)],
        observations=[
            ("A", "P", 1.0, 5),
            ("P", "Q", 1.0, 5),
        ],
    )
    with pytest.raises(AdjustmentError):
        run_adjustment(data)
