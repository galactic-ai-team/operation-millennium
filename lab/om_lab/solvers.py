"""SAT solvers (PySAT CDCL + instrumented pure-Python DPLL baseline) and verifier."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Sequence

from pysat.solvers import Solver as PySATSolver


@dataclass(frozen=True)
class SolveResult:
    """Standardized solver output with instrumentation and witness verification."""

    solver_name: str
    satisfiable: bool
    model: list[int] | None
    elapsed_s: float
    decisions: int
    propagations: int
    verified: bool


def verify_cnf_assignment(clauses: Sequence[Sequence[int]], model: Sequence[int] | None) -> bool:
    """Independently verify that a literal assignment satisfies all CNF clauses."""
    if model is None:
        return False
    assignment: dict[int, bool] = {}
    for lit in model:
        var = abs(lit)
        val = lit > 0
        if var in assignment and assignment[var] != val:
            return False
        assignment[var] = val

    for clause in clauses:
        if not any(
            (lit > 0 and assignment.get(abs(lit), False))
            or (lit < 0 and not assignment.get(abs(lit), True))
            for lit in clause
            if abs(lit) in assignment
        ):
            return False
    return True


def solve_pysat(
    n_vars: int,
    clauses: Sequence[Sequence[int]],
    solver_name: str = "cd195",
) -> SolveResult:
    """Solve a CNF formula using PySAT (default: CaDiCaL 1.9.5 'cd195')."""
    t0 = time.perf_counter()
    with PySATSolver(name=solver_name, bootstrap_with=clauses) as solver:
        sat = bool(solver.solve())
        model = list(solver.get_model()) if sat else None
        stats = solver.accum_stats() if hasattr(solver, "accum_stats") else {}
    elapsed = time.perf_counter() - t0

    verified = verify_cnf_assignment(clauses, model) if sat else True
    decisions = int(stats.get("decisions", 0))
    propagations = int(stats.get("propagations", 0))
    return SolveResult(
        solver_name=f"pysat:{solver_name}",
        satisfiable=sat,
        model=model,
        elapsed_s=elapsed,
        decisions=decisions,
        propagations=propagations,
        verified=verified,
    )


def solve_dpll(n_vars: int, clauses: Sequence[Sequence[int]]) -> SolveResult:
    """Pure-Python DPLL baseline with unit propagation and decision/propagation counters."""
    t0 = time.perf_counter()
    norm_clauses = [list(c) for c in clauses]
    stats = {"decisions": 0, "propagations": 0}

    def simplify(
        cls_list: list[list[int]], assign: dict[int, bool]
    ) -> list[list[int]] | None:
        new_clauses: list[list[int]] = []
        for clause in cls_list:
            satisfied = False
            reduced: list[int] = []
            for lit in clause:
                var = abs(lit)
                if var in assign:
                    val = assign[var]
                    if (lit > 0 and val) or (lit < 0 and not val):
                        satisfied = True
                        break
                else:
                    reduced.append(lit)
            if satisfied:
                continue
            if not reduced:
                return None  # Conflict (empty clause)
            new_clauses.append(reduced)
        return new_clauses

    def dpll(cls_list: list[list[int]], assign: dict[int, bool]) -> dict[int, bool] | None:
        # Unit propagation loop
        while True:
            cls_list = simplify(cls_list, assign)
            if cls_list is None:
                return None
            if not cls_list:
                return assign
            unit_lits = [c[0] for c in cls_list if len(c) == 1]
            if not unit_lits:
                break
            conflict = False
            for lit in unit_lits:
                var = abs(lit)
                val = lit > 0
                if var in assign:
                    if assign[var] != val:
                        conflict = True
                        break
                else:
                    assign[var] = val
                    stats["propagations"] += 1
            if conflict:
                return None

        # Choose unassigned variable appearing in shortest clause (MOMS/JW-like simple heuristic)
        shortest = min(cls_list, key=len)
        branch_var = abs(shortest[0])

        for val in (True, False):
            stats["decisions"] += 1
            next_assign = dict(assign)
            next_assign[branch_var] = val
            res = dpll(cls_list, next_assign)
            if res is not None:
                return res
        return None

    solution = dpll(norm_clauses, {})
    elapsed = time.perf_counter() - t0

    if solution is None:
        return SolveResult(
            solver_name="dpll",
            satisfiable=False,
            model=None,
            elapsed_s=elapsed,
            decisions=stats["decisions"],
            propagations=stats["propagations"],
            verified=True,
        )

    model = [v if solution.get(v, True) else -v for v in range(1, n_vars + 1)]
    verified = verify_cnf_assignment(clauses, model)
    return SolveResult(
        solver_name="dpll",
        satisfiable=True,
        model=model,
        elapsed_s=elapsed,
        decisions=stats["decisions"],
        propagations=stats["propagations"],
        verified=verified,
    )
