import math

from om_lab.generators import (
    GraphColoringInstance,
    generate_graph_coloring,
    generate_random_3sat,
    generate_tsp,
)
from om_lab.solvers import solve_pysat


def test_random_3sat_determinism_and_shape():
    inst1 = generate_random_3sat(n_vars=12, n_clauses=50, seed=42)
    inst2 = generate_random_3sat(n_vars=12, n_clauses=50, seed=42)
    assert inst1.clauses == inst2.clauses
    assert inst1.n_clauses == 50
    for clause in inst1.clauses:
        assert len(clause) == 3
        assert len({abs(lit) for lit in clause}) == 3
        assert all(1 <= abs(lit) <= 12 for lit in clause)


def test_graph_coloring_reduction_k3_vs_k4():
    # Triangle K3 is 3-colorable
    k3 = GraphColoringInstance(
        n_vertices=3, edges=[(0, 1), (1, 2), (0, 2)], k_colors=3
    )
    res_k3 = solve_pysat(k3.to_cnf().n_vars, k3.to_cnf().clauses)
    assert res_k3.satisfiable
    assert res_k3.model is not None
    coloring = k3.decode_model(res_k3.model)
    assert k3.verify_coloring(coloring)

    # K4 is NOT 3-colorable
    k4_edges = [(u, v) for u in range(4) for v in range(u + 1, 4)]
    k4 = GraphColoringInstance(n_vertices=4, edges=k4_edges, k_colors=3)
    res_k4 = solve_pysat(k4.to_cnf().n_vars, k4.to_cnf().clauses)
    assert not res_k4.satisfiable


def test_generated_graph_coloring_reproducible():
    g = generate_graph_coloring(n_vertices=8, edge_prob=0.4, k_colors=3, seed=7)
    cnf = g.to_cnf()
    assert cnf.n_vars == 24
    res = solve_pysat(cnf.n_vars, cnf.clauses)
    if res.satisfiable:
        assert res.model is not None
        assert g.verify_coloring(g.decode_model(res.model))


def test_tsp_symmetry_and_exact_held_karp():
    tsp = generate_tsp(n_cities=6, seed=99, metric=True)
    assert len(tsp.dist_matrix) == 6
    for i in range(6):
        assert tsp.dist_matrix[i][i] == 0.0
        for j in range(6):
            assert math.isclose(tsp.dist_matrix[i][j], tsp.dist_matrix[j][i])

    best_cost, best_tour = tsp.solve_exact_held_karp()
    assert tsp.verify_tour(best_tour)
    assert math.isclose(best_cost, tsp.tour_length(best_tour))
    # Any tour must be >= optimal Held-Karp tour
    alt_tour = list(range(6))
    assert tsp.tour_length(alt_tour) >= best_cost - 1e-9
