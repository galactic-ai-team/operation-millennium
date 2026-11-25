"""Deterministic generators for canonical NP-complete / NP-hard problems."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Sequence


@dataclass(frozen=True)
class CNFInstance:
    """A CNF formula in DIMACS-style 1-indexed literal lists."""

    n_vars: int
    clauses: list[list[int]]
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def n_clauses(self) -> int:
        return len(self.clauses)

    @property
    def ratio(self) -> float:
        return self.n_clauses / self.n_vars if self.n_vars > 0 else 0.0


def generate_random_3sat(
    n_vars: int, n_clauses: int, seed: int | None = None
) -> CNFInstance:
    """Generate a uniform random 3-SAT instance with 3 distinct variables per clause."""
    if n_vars < 3:
        raise ValueError("n_vars must be at least 3 for 3-SAT")
    if n_clauses < 0:
        raise ValueError("n_clauses must be non-negative")

    rng = random.Random(seed)
    vars_pool = range(1, n_vars + 1)
    clauses: list[list[int]] = []
    for _ in range(n_clauses):
        chosen = rng.sample(vars_pool, 3)
        clause = [v if rng.random() < 0.5 else -v for v in chosen]
        clauses.append(clause)

    return CNFInstance(
        n_vars=n_vars,
        clauses=clauses,
        metadata={
            "problem": "random_3sat",
            "seed": seed,
            "ratio": n_clauses / n_vars,
        },
    )


@dataclass(frozen=True)
class GraphColoringInstance:
    """Undirected graph k-coloring instance with exact CNF reduction."""

    n_vertices: int
    edges: list[tuple[int, int]]
    k_colors: int
    seed: int | None = None

    def var_id(self, vertex: int, color: int) -> int:
        """1-indexed SAT variable meaning 'vertex v has color c'."""
        return vertex * self.k_colors + color + 1

    def to_cnf(self) -> CNFInstance:
        """Reduce k-coloring to CNF: each vertex gets >=1 color, <=1 color, adjacent !=."""
        if self.k_colors < 1:
            raise ValueError("k_colors must be >= 1")
        clauses: list[list[int]] = []
        # At least one color per vertex
        for v in range(self.n_vertices):
            clauses.append([self.var_id(v, c) for c in range(self.k_colors)])
            # At most one color per vertex
            for c1 in range(self.k_colors):
                for c2 in range(c1 + 1, self.k_colors):
                    clauses.append([-self.var_id(v, c1), -self.var_id(v, c2)])
        # Adjacent vertices cannot share a color
        for u, v in self.edges:
            for c in range(self.k_colors):
                clauses.append([-self.var_id(u, c), -self.var_id(v, c)])

        return CNFInstance(
            n_vars=self.n_vertices * self.k_colors,
            clauses=clauses,
            metadata={
                "problem": "graph_coloring",
                "n_vertices": self.n_vertices,
                "n_edges": len(self.edges),
                "k_colors": self.k_colors,
                "seed": self.seed,
            },
        )

    def decode_model(self, model: Sequence[int]) -> list[int]:
        """Extract a vertex -> color assignment from a satisfying SAT model."""
        pos = {lit for lit in model if lit > 0}
        coloring = [-1] * self.n_vertices
        for v in range(self.n_vertices):
            for c in range(self.k_colors):
                if self.var_id(v, c) in pos:
                    coloring[v] = c
                    break
        return coloring

    def verify_coloring(self, coloring: Sequence[int]) -> bool:
        """Independently verify that a coloring is valid."""
        if len(coloring) != self.n_vertices:
            return False
        if any(c < 0 or c >= self.k_colors for c in coloring):
            return False
        return all(coloring[u] != coloring[v] for u, v in self.edges)


def generate_graph_coloring(
    n_vertices: int,
    edge_prob: float,
    k_colors: int = 3,
    seed: int | None = None,
) -> GraphColoringInstance:
    """Generate an Erdos-Renyi G(n, p) graph k-coloring instance."""
    if n_vertices < 1:
        raise ValueError("n_vertices must be >= 1")
    if not (0.0 <= edge_prob <= 1.0):
        raise ValueError("edge_prob must be in [0, 1]")
    if k_colors < 1:
        raise ValueError("k_colors must be >= 1")

    rng = random.Random(seed)
    edges: list[tuple[int, int]] = []
    for u in range(n_vertices):
        for v in range(u + 1, n_vertices):
            if rng.random() < edge_prob:
                edges.append((u, v))

    return GraphColoringInstance(
        n_vertices=n_vertices,
        edges=edges,
        k_colors=k_colors,
        seed=seed,
    )


@dataclass(frozen=True)
class TSPInstance:
    """Symmetric Traveling Salesperson Problem instance."""

    n_cities: int
    coords: list[tuple[float, float]] | None
    dist_matrix: list[list[float]]
    seed: int | None = None

    def verify_tour(self, tour: Sequence[int]) -> bool:
        """Verify that tour is a permutation of 0..n_cities-1."""
        return (
            len(tour) == self.n_cities
            and set(tour) == set(range(self.n_cities))
        )

    def tour_length(self, tour: Sequence[int]) -> float:
        """Compute closed tour length; raises ValueError on invalid tour."""
        if not self.verify_tour(tour):
            raise ValueError("Invalid TSP tour")
        if self.n_cities <= 1:
            return 0.0
        total = 0.0
        for i in range(self.n_cities):
            a = tour[i]
            b = tour[(i + 1) % self.n_cities]
            total += self.dist_matrix[a][b]
        return total

    def solve_exact_held_karp(self) -> tuple[float, list[int]]:
        """Exact Held-Karp DP baseline for small instances (n <= 15)."""
        n = self.n_cities
        if n == 0:
            return 0.0, []
        if n == 1:
            return 0.0, [0]
        if n > 15:
            raise ValueError("Held-Karp exact baseline restricted to n <= 15")

        # dp[mask][last] = (cost, prev) for paths starting at 0 visiting `mask` ending at `last`
        full_mask = 1 << n
        dp: dict[tuple[int, int], tuple[float, int]] = {}
        for j in range(1, n):
            dp[(1 | (1 << j), j)] = (self.dist_matrix[0][j], 0)

        for mask in range(1, full_mask):
            if not (mask & 1):
                continue
            for last in range(1, n):
                if not (mask & (1 << last)):
                    continue
                state = dp.get((mask, last))
                if state is None:
                    continue
                cur_cost, _ = state
                for nxt in range(1, n):
                    if mask & (1 << nxt):
                        continue
                    nmask = mask | (1 << nxt)
                    cand = cur_cost + self.dist_matrix[last][nxt]
                    prev_best = dp.get((nmask, nxt))
                    if prev_best is None or cand < prev_best[0]:
                        dp[(nmask, nxt)] = (cand, last)

        end_mask = full_mask - 1
        best_cost = math.inf
        best_last = -1
        for last in range(1, n):
            cand = dp[(end_mask, last)][0] + self.dist_matrix[last][0]
            if cand < best_cost:
                best_cost = cand
                best_last = last

        # Reconstruct tour
        rev_tour = [best_last]
        mask = end_mask
        cur = best_last
        while cur != 0:
            _, prev = dp[(mask, cur)]
            mask ^= 1 << cur
            cur = prev
            if cur != 0:
                rev_tour.append(cur)
        tour = [0] + list(reversed(rev_tour))
        return best_cost, tour


def generate_tsp(
    n_cities: int,
    seed: int | None = None,
    metric: bool = True,
) -> TSPInstance:
    """Generate a symmetric TSP instance (2D Euclidean if metric=True)."""
    if n_cities < 1:
        raise ValueError("n_cities must be >= 1")
    rng = random.Random(seed)

    if metric:
        coords = [(rng.uniform(0.0, 100.0), rng.uniform(0.0, 100.0)) for _ in range(n_cities)]
        dist = [[0.0] * n_cities for _ in range(n_cities)]
        for i in range(n_cities):
            for j in range(i + 1, n_cities):
                d = math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1])
                dist[i][j] = d
                dist[j][i] = d
        return TSPInstance(n_cities=n_cities, coords=coords, dist_matrix=dist, seed=seed)

    dist = [[0.0] * n_cities for _ in range(n_cities)]
    for i in range(n_cities):
        for j in range(i + 1, n_cities):
            d = rng.uniform(1.0, 100.0)
            dist[i][j] = d
            dist[j][i] = d
    return TSPInstance(n_cities=n_cities, coords=None, dist_matrix=dist, seed=seed)
