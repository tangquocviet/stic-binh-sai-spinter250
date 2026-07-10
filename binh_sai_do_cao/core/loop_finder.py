"""Phát hiện vòng khép độc lập (fundamental cycles) — SPEC.md Bước 3.2.

Thuật toán: dựng cây khung bằng Union-Find, xử lý các trị đo theo đúng thứ tự
trong danh sách đầu vào (điều này tái tạo đúng bộ vòng khép mà phần mềm tham
chiếu sinh ra). Mỗi trị đo không thuộc cây khung ("cạnh dư") tạo ra đúng 1
vòng khép độc lập khi ghép với đường đi trong cây khung giữa 2 đầu mút của nó.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from binh_sai_do_cao.models.schema import NetworkInput, Observation


class _UnionFind:
    def __init__(self, nodes):
        self._parent = {n: n for n in nodes}

    def find(self, x):
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


@dataclass
class LoopEdgeUse:
    observation: Observation
    forward: bool  # True nếu đi theo đúng chiều from_->to của trị đo


@dataclass
class Loop:
    index: int
    path: list[str]  # dãy điểm hiển thị, khép kín (điểm đầu = điểm cuối)
    edges: list[LoopEdgeUse]
    wh_m: float

    @property
    def n_segments(self) -> int:
        return len(self.edges)

    @property
    def total_stations(self) -> int | None:
        if any(e.observation.stations is None for e in self.edges):
            return None
        return sum(e.observation.stations for e in self.edges)

    @property
    def total_distance_km(self) -> float | None:
        if any(e.observation.distance_km is None for e in self.edges):
            return None
        return sum(e.observation.distance_km for e in self.edges)

    @property
    def path_str(self) -> str:
        return " → ".join(self.path)


def _bfs_edge_path(tree_adj: dict, start: str, end: str):
    """Trả về (path_nodes, path_edges) đi từ start đến end trong cây khung."""
    if start == end:
        return [start], []

    parent = {start: (None, None)}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == end:
            break
        for neighbor, obs in tree_adj[node]:
            if neighbor not in parent:
                parent[neighbor] = (node, obs)
                queue.append(neighbor)

    if end not in parent:
        raise ValueError(f"Không tìm thấy đường trong cây khung giữa '{start}' và '{end}'.")

    nodes_rev = [end]
    edges_rev = []
    cur = end
    while cur != start:
        prev, obs = parent[cur]
        edges_rev.append(obs)
        nodes_rev.append(prev)
        cur = prev

    return list(reversed(nodes_rev)), list(reversed(edges_rev))


def find_fundamental_cycles(data: NetworkInput) -> list[Loop]:
    nodes: set[str] = {p.name for p in data.known_points}
    for obs in data.observations:
        nodes.add(obs.from_)
        nodes.add(obs.to)

    uf = _UnionFind(nodes)
    tree_adj: dict[str, list[tuple[str, Observation]]] = {n: [] for n in nodes}
    chords: list[Observation] = []

    for obs in data.observations:
        if uf.find(obs.from_) != uf.find(obs.to):
            uf.union(obs.from_, obs.to)
            tree_adj[obs.from_].append((obs.to, obs))
            tree_adj[obs.to].append((obs.from_, obs))
        else:
            chords.append(obs)

    loops: list[Loop] = []
    for idx, chord in enumerate(chords, start=1):
        u, v = chord.from_, chord.to
        path_nodes, path_edges = _bfs_edge_path(tree_adj, v, u)

        edges_in_order = [
            LoopEdgeUse(
                observation=obs,
                forward=(obs.from_ == path_nodes[i] and obs.to == path_nodes[i + 1]),
            )
            for i, obs in enumerate(path_edges)
        ]
        edges_in_order.append(LoopEdgeUse(observation=chord, forward=True))

        wh_m = sum(
            e.observation.measured_dh_m if e.forward else -e.observation.measured_dh_m
            for e in edges_in_order
        )

        loops.append(
            Loop(
                index=idx,
                path=path_nodes + [v],
                edges=edges_in_order,
                wh_m=wh_m,
            )
        )

    return loops
