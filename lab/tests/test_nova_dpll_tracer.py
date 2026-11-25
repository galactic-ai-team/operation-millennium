"""Adversarial branch-accounting audit (Nova, Phase 4 attack on PR #10).

Compares ``om_lab.solvers.solve_dpll`` against the separately written
tiny reference tracer in ``_nova_dpll_tracer.py`` on status, branch
attempts (``decisions``) and model, over:

* hand-built fixtures (empty CNF, empty clause, unit contradictions,
  chains, PHP, Tseitin);
* random 3-SAT with budgets {None, 0, 1, 2, 5, 20, 100};
* pilot instances (never confirmatory test instances);
* the decision-budget boundary (a run that would finish with exactly
  B decisions must be UNKNOWN with D == B).

Propagations are NOT asserted equal: the tracer implements the
Section 3.6 search semantics in a deliberately different structure
(one unit at a time with re-simplification, versus
``solve_dpll``'s batch unit pass), and the two disagree on the
propagation count on 42/200 random cases and 22/24 pilot cases while
agreeing on decisions/status/model everywhere. That is the finding
NOVA-R10-14 in the review: Section 3.6 pins the branch-attempt
counter but not the interleaving of unit assignment and conflict
detection, so the propagation count is implementation-defined and
cannot be independently reproduced. The vendored
``_reference_solvers_ed6d557`` copy is NOT used here: it is
byte-identical code to the thing under test and cannot audit it.

[Claim Level: Empirical Observation] for every count below.
"""

from __future__ import annotations

import random

import pytest

from _nova_dpll_tracer import trace_dpll
from om_lab.generators import generate_random_3sat
from om_lab.hard_instances import generate_php
from om_lab.matched_instances import generate_matched_tseitin_pair, petersen_graph
from om_lab.solvers import solve_dpll, verify_cnf_assignment


def _compare(n, clauses, max_decisions=None, max_seconds=None):
    """solve_dpll and the tracer must agree on everything the
    preregistration pins: status, branch attempts (``decisions``) and
    model. Propagations are compared separately in
    ``test_propagation_counts_differ_across_implementations``: the
    count depends on the interleaving of unit assignment and conflict
    detection, which Section 3.6 does not pin (see the finding
    NOVA-R10-14 in the review), so an independent implementation is
    expected to disagree on propagations while agreeing on decisions.
    """
    got = solve_dpll(n, clauses, max_decisions=max_decisions, max_seconds=max_seconds)
    ref = trace_dpll(n, clauses, max_decisions=max_decisions, max_seconds=max_seconds)
    assert (got.status, got.decisions, got.timed_out) == (
        ref["status"], ref["decisions"], ref["timed_out"],
    ), (
        f"BRANCH-COUNT MISMATCH n={n} clauses={clauses} budget={max_decisions}: "
        f"solve_dpll=({got.status}, D={got.decisions}, P={got.propagations}) vs "
        f"tracer=({ref['status']}, D={ref['decisions']}, P={ref['propagations']})"
    )
    if got.status == "SAT":
        assert got.model is not None and ref["model"] is not None
        assert verify_cnf_assignment(clauses, got.model)
        assert verify_cnf_assignment(clauses, ref["model"])
        # Both models satisfy the formula; they need not be identical
        # (the search is deterministic, so in practice they are).
        assert got.model == ref["model"]
    else:
        assert got.model is None and ref["model"] is None
    return got, ref


def _propagation_agreement(n, clauses, max_decisions=None):
    got = solve_dpll(n, clauses, max_decisions=max_decisions)
    ref = trace_dpll(n, clauses, max_decisions=max_decisions)
    return got.propagations == ref["propagations"], got, ref


def test_hand_built_fixtures():
    cases = [
        (3, []),                                  # empty CNF: SAT, no work
        (2, [[1, 2], []]),                       # empty clause: UNSAT
        (1, [[1], [-1]]),                        # contradictory units
        (3, [[1], [2], [3]]),                    # three units
        (3, [[1], [-1, 2], [-2, 3], [-3]]),      # unit chain to a conflict
        (3, [[1, 2], [-1, 2], [1, -2], [-1, -2]]),  # 2-var parity UNSAT
        (3, [[1, 2, 3], [-1, 2, 3], [1, -2, 3], [1, 2, -3],
            [-1, -2, 3], [-1, 2, -3], [1, -2, -3], [-1, -2, -3]]),  # 3-var cube
        (2, [[1, 1, 2], [-1, -1]]),              # duplicate literals
        (4, [[1], [1], [1, 2], [-2, -3, 4]]),    # duplicate unit clauses
    ]
    for n, clauses in cases:
        _compare(n, clauses)
        _compare(n, clauses, max_decisions=0)
        _compare(n, clauses, max_decisions=1)
        _compare(n, clauses, max_decisions=2)


def test_php_and_tseitin_fixtures():
    for holes in (2, 3):
        php = generate_php(holes)
        _compare(php.n_vars, php.clauses)
    odd = generate_matched_tseitin_pair(petersen_graph()).odd
    _compare(odd.n_vars, [list(c) for c in odd.clauses])
    even = generate_matched_tseitin_pair(petersen_graph()).even
    _compare(even.n_vars, [list(c) for c in even.clauses])


def test_random_3sat_agrees_with_tracer():
    rng = random.Random(20261125)
    compared = 0
    for _ in range(200):
        n = rng.randint(3, 40)
        m = rng.randint(0, 6 * n)
        inst = generate_random_3sat(n, m, seed=rng.getrandbits(64))
        budget = rng.choice([None, 0, 1, 2, 5, 20, 100])
        _compare(n, inst.clauses, max_decisions=budget)
        compared += 1
    assert compared == 200


def test_pilot_instances_agree_with_tracer():
    compared = 0
    for n, a in [(30, 426), (30, 500), (40, 426), (60, 500)]:
        for i in range(6):
            from om_lab.analyze_width import pilot_seed

            seed = pilot_seed(n, a, i)
            inst = generate_random_3sat(n, clause_count(n, a), seed=seed)
            _compare(n, inst.clauses, max_decisions=10000)
            compared += 1
    assert compared == 24


def clause_count(n, a):
    return (a * n + 50) // 100


def test_budget_boundary_convention():
    # A run that would finish with exactly B decisions is UNKNOWN with
    # D == B; with B + 1 it completes identically to the free run.
    for seed in range(200):
        inst = generate_random_3sat(30, 128, seed=seed)
        free = solve_dpll(30, inst.clauses)
        if free.decisions >= 3:
            break
    d = free.decisions
    at, at_ref = _compare(30, inst.clauses, max_decisions=d)
    assert at.status == "UNKNOWN" and at.decisions == d
    assert at.stop_reason == "decision_budget"
    above, _ = _compare(30, inst.clauses, max_decisions=d + 1)
    assert (above.status, above.decisions, above.model) == (
        free.status, free.decisions, free.model,
    )
    # B = 0 makes even the empty formula UNKNOWN (budget at entry).
    zero, zero_ref = _compare(3, [], max_decisions=0)
    assert zero.status == "UNKNOWN" and zero.decisions == 0


def test_tracer_counts_units_one_at_a_time():
    # A chain where unit propagation must fire repeatedly: (1) -> 2 ->
    # 3 -> conflict. Both the batch and the one-at-a-time propagation
    # must count exactly 3 unit assignments.
    clauses = [[1], [-1, 2], [-2, 3], [-3]]
    got, ref = _compare(3, clauses)
    assert got.status == "UNSAT"
    assert got.propagations == ref["propagations"] == 3
    assert got.decisions == ref["decisions"] == 0


def test_propagation_counts_differ_across_implementations():
    # Finding NOVA-R10-14: the propagation count is
    # implementation-defined. Two independently structured UP loops
    # that agree on status, decisions and model everywhere still
    # disagree on propagations whenever a conflict is detected
    # mid-batch (the batch version stops counting at the next
    # re-simplification; the one-at-a-time version assigns the units
    # that became available between snapshot units first). The
    # disagreement goes in both directions, so it is not an off-by-one.
    # Observed on 2026-11-25: 42/200 random cases and 22/24 pilot
    # cases differ. This test asserts the divergence exists (so the
    # finding stays pinned) and that decisions still match on every
    # case where propagations differ; it does NOT assert the exact
    # rates, which change if either UP loop is restructured. If
    # Section 3.6 is ever amended to pin the counting rule, this test
    # should be replaced by an equality assertion.
    rng = random.Random(20261125)
    mismatches = 0
    compared = 0
    for _ in range(200):
        n = rng.randint(3, 40)
        m = rng.randint(0, 6 * n)
        inst = generate_random_3sat(n, m, seed=rng.getrandbits(64))
        budget = rng.choice([None, 0, 1, 2, 5, 20, 100])
        agree, got, ref = _propagation_agreement(n, inst.clauses, budget)
        _compare(n, inst.clauses, max_decisions=budget)
        compared += 1
        if not agree:
            mismatches += 1
            # Decisions (the preregistered response) still match.
            assert got.decisions == ref["decisions"]
            assert got.status == ref["status"]
    assert compared == 200
    assert mismatches > 0, "expected at least one propagation mismatch"
    assert mismatches < compared, "expected at least one agreement"
    print(f"\n[info] propagation mismatches on random cases: {mismatches}/200")

    pilot_mismatches = 0
    pilot_compared = 0
    for n, a in [(30, 426), (30, 500), (40, 426), (60, 500)]:
        for i in range(6):
            from om_lab.analyze_width import pilot_seed

            seed = pilot_seed(n, a, i)
            inst = generate_random_3sat(n, clause_count(n, a), seed=seed)
            agree, got, ref = _propagation_agreement(n, inst.clauses, 10000)
            _compare(n, inst.clauses, max_decisions=10000)
            pilot_compared += 1
            if not agree:
                pilot_mismatches += 1
                assert got.decisions == ref["decisions"]
    assert pilot_compared == 24
    assert pilot_mismatches > 0, "expected at least one pilot mismatch"
    print(f"[info] propagation mismatches on pilot cases: {pilot_mismatches}/24")
