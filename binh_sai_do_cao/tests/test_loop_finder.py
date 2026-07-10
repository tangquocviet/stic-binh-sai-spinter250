"""TC-03, TC-04 (SPEC.md mục 6.1)."""

from __future__ import annotations

from binh_sai_do_cao.core.loop_finder import find_fundamental_cycles
from binh_sai_do_cao.tests.helpers import make_network


def test_tc03_independent_loop_count_equals_e_minus_v_plus_1():
    data = make_network(
        known_points=[("A", 10.0)],
        observations=[
            ("A", "B", 1.0, 5),
            ("B", "C", 1.0, 5),
            ("C", "D", 1.0, 5),
            ("D", "E", 1.0, 5),
            ("E", "A", -4.0, 5),
            ("B", "D", 1.5, 5),
        ],
    )
    loops = find_fundamental_cycles(data)
    v, e = 5, 6
    assert len(loops) == e - v + 1


def test_tc04_tree_network_has_no_loops():
    data = make_network(
        known_points=[("A", 10.0)],
        observations=[
            ("A", "B", 1.0, 5),
            ("B", "C", 1.0, 5),
            ("C", "D", 1.0, 5),
        ],
    )
    loops = find_fundamental_cycles(data)
    assert loops == []
