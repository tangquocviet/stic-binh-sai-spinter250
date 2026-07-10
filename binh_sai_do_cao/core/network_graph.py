"""Dựng đồ hình lưới & kiểm tra liên thông (SPEC.md Bước 3.1)."""

from __future__ import annotations

import networkx as nx

from binh_sai_do_cao.models.schema import NetworkInput


class FragmentedNetworkError(ValueError):
    pass


def build_graph(data: NetworkInput) -> nx.MultiGraph:
    """Mỗi điểm là 1 node, mỗi trị đo là 1 cạnh (vô hướng cho mục đích liên thông)."""
    graph = nx.MultiGraph()

    for point in data.known_points:
        graph.add_node(point.name, is_known=True, height_m=point.height_m)

    for obs in data.observations:
        if obs.from_ not in graph:
            graph.add_node(obs.from_, is_known=False)
        if obs.to not in graph:
            graph.add_node(obs.to, is_known=False)
        graph.add_edge(obs.from_, obs.to, key=obs.id, observation=obs)

    return graph


def check_connectivity(graph: nx.MultiGraph) -> None:
    """Toàn bộ đồ hình phải liên thông (SPEC.md mục 2). Raise nếu bị phân mảnh."""
    if graph.number_of_nodes() == 0:
        raise FragmentedNetworkError("Đồ hình lưới rỗng — không có điểm nào.")

    components = list(nx.connected_components(graph))
    if len(components) <= 1:
        return

    components.sort(key=len, reverse=True)
    main = components[0]
    isolated_points = sorted(
        name for comp in components[1:] for name in comp if name not in main
    )
    raise FragmentedNetworkError(
        "Lưới bị phân mảnh, điểm "
        + ", ".join(isolated_points)
        + " không liên kết với phần còn lại của lưới."
    )
