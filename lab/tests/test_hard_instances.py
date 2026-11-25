"""Verification tests for adversarial hard-instance generators."""

from __future__ import annotations

import pytest

from om_lab.hard_instances import (
    generate_complete_graph_coloring,
    generate_php,
    generate_planted_3sat,
    generate_tseitin_3sat,
)
from om_lab.solvers import solve_dpll, solve_pysat, verify_cnf_assignment


def test_php_small_unsat_pysat() -> None:
    for n in range(1, 6):
        inst = generate_php(n)
        assert inst.n_vars == (n + 1) * n
        res = solve_pysat(inst.n_vars, inst.clauses)
        assert not res.satisfiable
        assert res.verified


def test_php_small_unsat_dpll() -> None:
    for n in range(1, 5):
        inst = generate_php(n)
        res = solve_dpll(inst.n_vars, inst.clauses, max_decisions=100_000)
        assert not res.satisfiable
        assert res.verified
        assert not res.timed_out


def test_tseitin_unsat_pysat() -> None:
    for n_vertices in (4, 6, 8):
        inst = generate_tseitin_3sat(n_vertices, charge_pattern="unsat")
        res = solve_pysat(inst.n_vars, inst.clauses)
        assert not res.satisfiable
        assert res.verified


def test_tseitin_sat_witness() -> None:
    inst = generate_tseitin_3sat(4, charge_pattern="sat")
    res = solve_pysat(inst.n_vars, inst.clauses)
    assert res.satisfiable
    assert res.verified
    assert res.model is not None


def test_planted_3sat_satisfiable() -> None:
    inst = generate_planted_3sat(n_vars=20, n_clauses=80, seed=7)
    res = solve_pysat(inst.n_vars, inst.clauses)
    assert res.satisfiable
    assert res.verified


def test_complete_graph_coloring_satisfiable() -> None:
    inst = generate_complete_graph_coloring(3)
    res = solve_pysat(inst.n_vars, inst.clauses)
    assert res.satisfiable
    assert res.verified


def test_literals_are_in_range() -> None:
    for inst in (
        generate_php(4),
        generate_tseitin_3sat(4, charge_pattern="unsat"),
        generate_planted_3sat(10, 20, seed=1),
        generate_complete_graph_coloring(3),
    ):
        for clause in inst.clauses:
            for lit in clause:
                assert 1 <= abs(lit) <= inst.n_vars


def test_planted_3sat_hidden_assignment_satisfies() -> None:
    """Regression (Lumi): the hidden assignment must satisfy every clause,
    including at clause densities above the 3-SAT threshold (~4.27)."""
    for seed in range(20):
        inst = generate_planted_3sat(n_vars=30, n_clauses=180, seed=seed)
        hidden = inst.metadata["hidden_assignment"]
        model = [int(v) if val else -int(v) for v, val in hidden.items()]
        assert verify_cnf_assignment(inst.clauses, model)
        res = solve_pysat(inst.n_vars, inst.clauses)
        assert res.satisfiable and res.verified
