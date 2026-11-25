"""Operation Millennium Phase 2 computational laboratory."""

from om_lab.features import (
    CNFFeatures,
    extract_features,
    extract_features_from_clauses,
)
from om_lab.generators import (
    CNFInstance,
    GraphColoringInstance,
    TSPInstance,
    generate_graph_coloring,
    generate_random_3sat,
    generate_tsp,
)
from om_lab.solvers import (
    SolveResult,
    solve_dpll,
    solve_pysat,
    verify_cnf_assignment,
)

__all__ = [
    "CNFInstance",
    "CNFFeatures",
    "GraphColoringInstance",
    "TSPInstance",
    "SolveResult",
    "extract_features",
    "extract_features_from_clauses",
    "generate_random_3sat",
    "generate_graph_coloring",
    "generate_tsp",
    "solve_dpll",
    "solve_pysat",
    "verify_cnf_assignment",
]
