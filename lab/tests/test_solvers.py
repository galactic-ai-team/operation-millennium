import math

import pytest

from om_lab.generators import generate_random_3sat
from om_lab.solvers import (
    SolveResult,
    Status,
    StopReason,
    Verification,
    normalize_cnf,
    solve_dpll,
    solve_pysat,
    verify_cnf_assignment,
)


def test_verify_cnf_assignment():
    clauses = [[1, 2], [-1, 3]]
    assert verify_cnf_assignment(clauses, [1, -2, 3])
    assert not verify_cnf_assignment(clauses, [1, -2, -3])
    assert not verify_cnf_assignment(clauses, None)
    # Malformed models are rejected: contradictory pair, literal 0.
    assert not verify_cnf_assignment(clauses, [1, -1, 3])
    assert not verify_cnf_assignment(clauses, [1, -2, 3, 0])


def test_dpll_and_pysat_edge_cases():
    # Empty CNF is SAT, with a checked (vacuous) witness.
    for fn in (solve_dpll, solve_pysat):
        res = fn(2, [])
        assert res.satisfiable
        assert res.status == Status.SAT
        assert res.verification_status == Verification.SAT_WITNESS_CHECKED
        assert res.verified

    # Empty clause and contradictory units are UNSAT. Without a checked
    # certificate the claim is UNVERIFIED (Section 4.1 repair); with
    # certify=True the PySAT path is proof-checked.
    for clauses in ([[1], []], [[1], [-1]]):
        for fn in (solve_dpll, solve_pysat):
            res = fn(2, clauses)
            assert not res.satisfiable
            assert res.status == Status.UNSAT
            assert res.verification_status == Verification.UNVERIFIED
            assert not res.verified
        certified = solve_pysat(2, clauses, certify=True)
        assert certified.status == Status.UNSAT
        assert certified.verification_status == Verification.UNSAT_PROOF_CHECKED
        assert certified.verified
        assert certified.certificate["result"] == "VALID"


def test_dpll_matches_pysat_on_random_3sat():
    for seed in range(25):
        inst = generate_random_3sat(n_vars=16, n_clauses=68, seed=seed)
        r_pysat = solve_pysat(inst.n_vars, inst.clauses, certify=True)
        r_dpll = solve_dpll(inst.n_vars, inst.clauses)
        # PySAT claims are always independently checked here: SAT by witness,
        # UNSAT by a DRAT certificate checked in om_lab.proof_check.
        assert r_pysat.verified
        # DPLL SAT claims carry a checked witness; DPLL UNSAT is UNVERIFIED
        # on its own and is corroborated by the certified PySAT result.
        assert r_dpll.verified == r_dpll.satisfiable
        assert r_pysat.satisfiable == r_dpll.satisfiable


def test_budget_exhaustion_is_unknown_never_unsat():
    inst = generate_random_3sat(n_vars=40, n_clauses=170, seed=11)
    res = solve_dpll(inst.n_vars, inst.clauses, max_decisions=3)
    assert res.status == Status.UNKNOWN
    assert res.stop_reason == StopReason.DECISION_BUDGET
    assert res.timed_out and not res.satisfiable and not res.verified
    assert res.verification_status == Verification.NOT_APPLICABLE
    assert res.decisions == 3


def test_solve_result_rejects_inconsistent_labels():
    common = dict(solver_name="x", model=None, elapsed_s=0.0, decisions=0, propagations=0)
    # The pre-repair pattern "UNSAT with verified=True" no longer type-checks.
    with pytest.raises(ValueError):
        SolveResult(satisfiable=False, verified=True, **common)
    with pytest.raises(ValueError):
        SolveResult(satisfiable=True, verified=True, timed_out=True, **common)
    with pytest.raises(ValueError):
        SolveResult(
            satisfiable=False, verified=False, status=Status.UNKNOWN,
            verification_status=Verification.UNSAT_PROOF_CHECKED, **common,
        )
    with pytest.raises(ValueError):
        SolveResult(satisfiable=False, verified=False, status="MAYBE", **common)


def test_solvers_reject_out_of_range_literals():
    # Before the repair, solve_dpll(1, [[2]]) returned SAT with an unverifiable
    # truncated model while PySAT returned verified SAT.
    for fn in (solve_dpll, solve_pysat):
        with pytest.raises(ValueError):
            fn(1, [[2]])
        with pytest.raises(ValueError):
            fn(2, [[1, 0]])
    with pytest.raises(ValueError):
        normalize_cnf(2, [[True]])
    with pytest.raises(TypeError):
        normalize_cnf(2, [[1.0]])


def test_generator_clause_input_is_materialised_before_checking():
    inst = generate_random_3sat(n_vars=20, n_clauses=60, seed=3)
    for fn in (solve_dpll, solve_pysat):
        res = fn(inst.n_vars, (list(c) for c in inst.clauses))
        assert res.satisfiable
        # The witness is checked against the real clauses, not an exhausted iterator.
        assert verify_cnf_assignment(inst.clauses, res.model)


def test_pysat_model_covers_every_declared_variable():
    res = solve_pysat(10, [[1, 2], [-1, 3]])
    assert res.satisfiable
    assert sorted(abs(lit) for lit in res.model) == list(range(1, 11))


def test_certify_requires_proof_capable_backend():
    with pytest.raises(ValueError, match="proof logging"):
        solve_pysat(1, [[1], [-1]], solver_name="m22", certify=True)


def test_capped_effort_definition_matches_budget_convention():
    # Y = ln(1 + min(D, B)); an exhausted run reports exactly D = B.
    inst = generate_random_3sat(n_vars=40, n_clauses=170, seed=11)
    budget = 5
    res = solve_dpll(inst.n_vars, inst.clauses, max_decisions=budget)
    assert res.decisions == budget
    assert math.isclose(math.log1p(min(res.decisions, budget)), math.log1p(budget))
