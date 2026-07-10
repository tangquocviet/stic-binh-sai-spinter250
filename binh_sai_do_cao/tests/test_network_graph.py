"""TC-01, TC-02 (SPEC.md mục 6.1)."""

from __future__ import annotations

import pytest

from binh_sai_do_cao.core.network_graph import FragmentedNetworkError, build_graph, check_connectivity
from binh_sai_do_cao.tests.helpers import make_network


def test_tc01_connected_graph_node_edge_counts():
    data = make_network(
        known_points=[("A", 10.0)],
        observations=[
            ("A", "B", 1.0, 5),
            ("B", "C", 1.0, 5),
            ("C", "D", 1.0, 5),
            ("D", "E", 1.0, 5),
            ("E", "A", -4.0, 5),
            ("B", "D", 1.5, 5),  # cạnh dư tạo vòng thứ 2
        ],
    )
    graph = build_graph(data)
    assert graph.number_of_nodes() == 5
    assert graph.number_of_edges() == 6
    check_connectivity(graph)  # không raise


def test_tc02_fragmented_network_raises_with_isolated_point_names():
    data = make_network(
        known_points=[("A", 10.0)],
        observations=[
            ("A", "B", 1.0, 5),
            ("B", "C", 1.0, 5),
            ("D", "E", 1.0, 5),  # cụm tách biệt, không nối với A
        ],
    )
    graph = build_graph(data)
    with pytest.raises(FragmentedNetworkError) as exc_info:
        check_connectivity(graph)
    message = str(exc_info.value)
    assert "D" in message
    assert "E" in message
