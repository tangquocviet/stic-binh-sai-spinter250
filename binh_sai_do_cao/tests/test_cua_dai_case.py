"""TC-20 → TC-27: hồi quy bằng bộ số liệu thật "Cầu Cửa Đại lần 3" (SPEC.md mục 6.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from binh_sai_do_cao.core import network_graph
from binh_sai_do_cao.core.accuracy import compute_accuracy, compute_extremes
from binh_sai_do_cao.core.adjustment import run_adjustment
from binh_sai_do_cao.core.closure_check import check_all_closures
from binh_sai_do_cao.core.loop_finder import find_fundamental_cycles
from binh_sai_do_cao.io.input_loader import load_json

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def data():
    return load_json(FIXTURES / "cua_dai_input.json")


@pytest.fixture(scope="module")
def expected():
    with open(FIXTURES / "cua_dai_expected.json", encoding="utf-8") as f:
        return json.load(f)


def test_tc20_input_counts(data):
    assert len(data.known_points) == 2
    assert len(data.observations) == 67
    all_names = {p.name for p in data.known_points}
    for obs in data.observations:
        all_names.add(obs.from_)
        all_names.add(obs.to)
    assert len(all_names) - 2 == 53


def test_tc21_loop_count_matches_reference(data, expected):
    graph = network_graph.build_graph(data)
    network_graph.check_connectivity(graph)
    loops = find_fundamental_cycles(data)
    assert len(loops) == 13
    assert len(loops) == len(expected["loops"])


def _canonical_edge_set(path: list[str]) -> frozenset:
    """Vòng khép là 1 chu trình vô hướng — biểu diễn bất biến với điểm bắt đầu/chiều đi
    để so khớp với file mẫu (nơi điểm bắt đầu hiển thị có thể khác quy ước)."""
    return frozenset(
        tuple(sorted((path[i], path[i + 1]))) for i in range(len(path) - 1)
    )


def test_tc22_wh_gh_matches_formula_and_reference(data, expected):
    loops = find_fundamental_cycles(data)
    closures = check_all_closures(loops, data.settings)
    expected_by_edges = {
        _canonical_edge_set(loop["path"].split(" → ")): loop for loop in expected["loops"]
    }

    assert len(closures) == len(expected_by_edges)
    for c in closures:
        key = _canonical_edge_set(c.loop.path)
        assert key in expected_by_edges, f"Vòng không khớp file mẫu: {c.loop.path_str}"
        exp = expected_by_edges[key]
        assert c.loop.n_segments == exp["n"]
        assert c.loop.total_stations == exp["total_stations"]
        # Sai số khép Wh có thể lệch tới ~0.1-0.2mm so với file mẫu do làm tròn hiển thị
        # trị đo về 4 chữ số thập phân trước khi cộng dồn (SPEC.md mục 7).
        assert c.wh_mm == pytest.approx(exp["wh_mm"], abs=0.15)
        assert c.wh_gh_mm == pytest.approx(exp["wh_gh_mm"], abs=0.01)


def test_tc23_near_limit_flag_on_mc6_loop(data):
    loops = find_fundamental_cycles(data)
    closures = check_all_closures(loops, data.settings)
    target = [c for c in closures if c.loop.path_str == "MC6 → M24TL → M24HL → MC6"]
    assert len(target) == 1
    c = target[0]
    assert c.wh_mm == pytest.approx(-0.60, abs=0.01)
    assert c.wh_gh_mm == pytest.approx(0.60, abs=0.01)
    assert c.status == "Đạt"
    assert c.flag == "sát giới hạn"


def test_tc24_mo(data, expected):
    adjustment = run_adjustment(data)
    accuracy = compute_accuracy(data, adjustment)
    assert accuracy.mo_mm == pytest.approx(expected["mo_mm"], abs=0.01)


def test_tc25_sstp_point_extremes(data, expected):
    adjustment = run_adjustment(data)
    accuracy = compute_accuracy(data, adjustment)
    extremes = compute_extremes(data, accuracy)
    assert extremes.point_max_name == expected["m_h_max_point"]
    assert extremes.point_max_mm == pytest.approx(expected["m_h_max_value_mm"], abs=0.01)
    assert extremes.point_min_name == expected["m_h_min_point"]
    assert extremes.point_min_mm == pytest.approx(expected["m_h_min_value_mm"], abs=0.01)


def test_tc26_adjusted_heights_match_reference(data, expected):
    adjustment = run_adjustment(data)
    for row in expected["adjusted_points"]:
        h = adjustment.heights_m[row["name"]]
        assert h == pytest.approx(row["height_m"], abs=0.0001)


def test_tc26b_sstp_per_observation_matches_reference(data, expected):
    adjustment = run_adjustment(data)
    accuracy = compute_accuracy(data, adjustment)
    for obs, exp in zip(data.observations, expected["observation_results"]):
        assert obs.from_ == exp["from"]
        assert obs.to == exp["to"]
        assert adjustment.corrections_m[obs.id] == pytest.approx(exp["shc_m"], abs=0.0005)
        assert adjustment.adjusted_dh_m[obs.id] == pytest.approx(exp["bs_m"], abs=0.0005)
        assert accuracy.m_obs_mm[obs.id] == pytest.approx(exp["sstp_mm"], abs=0.02)
