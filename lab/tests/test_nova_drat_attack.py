"""Adversarial differential tests for the DRAT checker (Nova, Phase 4 attack on PR #10).

Compares ``om_lab.proof_check.check_drat`` against the independently
written naive checker in ``_nova_independent_drat.py`` on:

* genuine CaDiCaL certificates (random 3-SAT, PHP, Tseitin);
* mutated certificates (truncation, corrupted lemmas, wrong formula,
  satisfiable prefix);
* malformed proof syntax;
* handcrafted RAT/RUP edge cases, deletion cases, and proofs attached
  to the wrong input formula.

A checker disagreement is a test failure: it must be investigated, not
settled by majority vote. Where the two checkers are *expected* to
differ -- the strict-deletion mode, which applies deletions the
documented DRAT-trim convention ignores -- the test asserts the
direction of the difference explicitly.

No confirmatory test instance is solved here. Genuine certificates come
from pilot seeds and small hand-built formulas only.

[Claim Level: Empirical Observation] for every verdict below.
"""

from __future__ import annotations

import os
import random

import pytest

from _nova_independent_drat import (
    nova_check_drat,
    nova_check_drat_strict,
)
from om_lab.proof_check import run_drat_trim
from om_lab.certify import reference_certificate
from om_lab.generators import generate_random_3sat
from om_lab.hard_instances import generate_php
from om_lab.matched_instances import generate_matched_tseitin_pair, petersen_graph
from om_lab.proof_check import check_drat
from om_lab.solvers import solve_dpll


def _agree(clauses, proof):
    """Both checkers must give the same verdict on (clauses, proof)."""
    mine = nova_check_drat(clauses, proof)
    theirs = check_drat(clauses, proof)
    assert mine.valid == theirs.valid, (
        f"CHECKER DISAGREEMENT: nova={mine.valid} ({mine.reason}) vs "
        f"om_lab={theirs.valid} ({theirs.reason})"
    )
    return mine, theirs


def _unsat_proof(n, clauses):
    result, _summary = reference_certificate(n, clauses)
    assert result.status == "UNSAT", "fixture must be UNSAT"
    assert result.certificate is not None
    return list(result.certificate["proof"])


def _first_unsat_random(n, m, seed_lo=0, seed_hi=200):
    for seed in range(seed_lo, seed_hi):
        inst = generate_random_3sat(n, m, seed=seed)
        if solve_dpll(n, inst.clauses).status == "UNSAT":
            return inst
    raise AssertionError("no UNSAT instance found in range")


# ---------------------------------------------------------------------------
# Genuine certificates
# ---------------------------------------------------------------------------


def test_genuine_certificates_agree_random_3sat():
    compared = 0
    for n, m, seed in [(20, 110, 3), (20, 120, 7), (30, 150, 11), (30, 170, 23), (40, 200, 5)]:
        inst = generate_random_3sat(n, m, seed=seed)
        if solve_dpll(n, inst.clauses).status != "UNSAT":
            continue
        proof = _unsat_proof(n, inst.clauses)
        mine, theirs = _agree(inst.clauses, proof)
        assert mine.valid and theirs.valid
        assert mine.n_rup + mine.n_rat == theirs.n_additions_checked
        compared += 1
    assert compared >= 3


def test_genuine_certificates_agree_php_and_tseitin():
    php = generate_php(3)
    proof = _unsat_proof(php.n_vars, php.clauses)
    mine, theirs = _agree(php.clauses, proof)
    assert mine.valid and theirs.valid
    odd = generate_matched_tseitin_pair(petersen_graph()).odd
    proof = _unsat_proof(odd.n_vars, [list(c) for c in odd.clauses])
    mine, theirs = _agree([list(c) for c in odd.clauses], proof)
    assert mine.valid and theirs.valid


# ---------------------------------------------------------------------------
# Mutated certificates
# ---------------------------------------------------------------------------


def test_mutated_certificates_agree():
    inst = _first_unsat_random(20, 110)
    proof = _unsat_proof(inst.n_vars, inst.clauses)
    assert len(proof) > 5
    mutations = {
        "truncated (drop last line)": proof[:-1],
        "truncated (first half)": proof[: len(proof) // 2],
        "empty proof": [],
        "first lemma corrupted": [proof[0].replace("1", "2", 1)] + proof[1:],
        "empty-clause line removed": [line for line in proof if line.strip() != "0"],
        "proof reversed": list(reversed(proof)),
    }
    for name, mutated in mutations.items():
        mine, theirs = _agree(inst.clauses, mutated)
        assert not mine.valid and not theirs.valid, f"{name} was accepted"
    # Duplicating a lemma is harmless: the lemma is still RUP/RAT the
    # second time, so the proof stays valid in both checkers. (The
    # checkers stop at the empty clause, so the count grows by exactly
    # one addition, not by the number of trailing lines.)
    _, orig = _agree(inst.clauses, proof)
    mine, theirs = _agree(inst.clauses, [proof[0]] + proof)
    assert mine.valid and theirs.valid
    assert theirs.n_additions_checked == orig.n_additions_checked + 1


def test_proof_attached_to_wrong_formula_agree():
    inst = _first_unsat_random(20, 110)
    proof = _unsat_proof(inst.n_vars, inst.clauses)
    # A different UNSAT formula of the same size.
    other = _first_unsat_random(20, 110, seed_lo=100, seed_hi=300)
    assert other.clauses != inst.clauses
    mine, theirs = _agree(other.clauses, proof)
    assert not mine.valid and not theirs.valid
    # A satisfiable prefix of the same formula (soundness probe).
    prefix = [list(c) for c in inst.clauses]
    while solve_dpll(inst.n_vars, prefix).status == "UNSAT":
        prefix = prefix[:-1]
    assert solve_dpll(inst.n_vars, prefix).status == "SAT"
    mine, theirs = _agree(prefix, proof)
    assert not mine.valid and not theirs.valid


# ---------------------------------------------------------------------------
# Malformed proof syntax
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_proof",
    [
        ["1 2"],                    # missing terminating 0
        ["1 2 0 3 0"],              # 0 in the middle of a line
        ["1 x 0"],                  # non-integer token
        ["1 2.5 0"],                # float token
        ["d"],                      # deletion with no literals
        ["d 0"],                    # deletion of the empty clause alone
        ["01 2 0"],                 # leading-zero token
        ["+1 2 0"],                 # explicit plus sign
        ["1 --2 0"],                # double minus
        [b"\xff\xfe 0"],            # non-ASCII bytes
        [123],                      # non-text line
        ["1 2 0", "garbage"],       # garbage after a valid line
    ],
)
def test_malformed_proofs_agree(bad_proof):
    clauses = [[1, 2], [-1, 2], [1, -2], [-1, -2]]
    mine, theirs = _agree(clauses, bad_proof)
    assert not mine.valid and not theirs.valid


def test_proof_without_empty_clause_and_lines_after_it():
    # [[1],[−1]] is UNSAT; a proof that adds a RUP lemma but never the
    # empty clause must be rejected by both checkers.
    clauses = [[1], [-1]]
    mine, theirs = _agree(clauses, ["1 0"])
    assert not mine.valid and not theirs.valid
    # The empty clause alone is a complete proof; trailing lines are ignored.
    proof = ["0", "1 2 0", "garbage-after-empty"]
    # NOTE: the trailing garbage line is malformed, so both parsers reject
    # the whole certificate; lines after the empty clause are only ignored
    # when they parse.
    mine, theirs = _agree(clauses, ["0", "1 2 0"])
    assert mine.valid and theirs.valid
    assert mine.empty_clause_line == 1 and theirs.empty_clause_line == 1


def test_formula_with_empty_clause_is_trivially_unsat():
    clauses = [[1, 2], []]
    mine, theirs = _agree(clauses, [])
    assert mine.valid and theirs.valid
    mine, theirs = _agree(clauses, ["1 2 0"])
    assert mine.valid and theirs.valid


# ---------------------------------------------------------------------------
# RUP / RAT edge cases (handcrafted, no solver involved)
# ---------------------------------------------------------------------------


def test_rup_only_lemma_accepted():
    # F = (x) & (-x v y) & (-y). Lemma (y) is RUP: assuming -y, UP gives
    # -y -> (-x v y) forces -x, contradicting (x).
    clauses = [[1], [-1, 2], [-2]]
    proof = ["2 0", "0"]
    mine, theirs = _agree(clauses, proof)
    assert mine.valid and theirs.valid
    assert mine.n_rup >= 1 and theirs.n_rup >= 1


def test_rat_only_lemma_accepted():
    # The full 3-variable cube (all 8 clauses over 1, 2, 3) is UNSAT
    # but not refutable by unit propagation alone. Lemma (1) is
    # RAT-only: assuming -1 leaves four 2-literal clauses and no unit,
    # so it is not RUP; but every clause containing -1 resolves with
    # (1) to a clause already in the database, so each resolvent is AT.
    # After (1) and (2) are added, unit propagation derives 3 and -3,
    # so the empty clause is RUP.
    clauses = [
        [1, 2, 3], [-1, 2, 3], [1, -2, 3], [1, 2, -3],
        [-1, -2, 3], [-1, 2, -3], [1, -2, -3], [-1, -2, -3],
    ]
    proof = ["1 0", "2 0", "0"]
    mine, theirs = _agree(clauses, proof)
    assert mine.valid and theirs.valid
    assert mine.n_rat >= 1 and theirs.n_rat >= 1
    assert mine.n_rup >= 1 and theirs.n_rup >= 1


def test_lemma_neither_rup_nor_rat_rejected():
    # F = (1 v 2 v 3) & (-1 v 4 v 5) is satisfiable. Lemma (1):
    # - not RUP: assuming -1 leaves (2 v 3) open and satisfies the
    #   second clause, so no conflict;
    # - not RAT on 1: the only clause containing -1 is (-1 v 4 v 5),
    #   whose resolvent (1 v 4 v 5) is neither a tautology nor AT
    #   (assuming -1, -4, -5 leaves (1 v 2 v 3) with 2 and 3 open).
    clauses = [[1, 2, 3], [-1, 4, 5]]
    mine, theirs = _agree(clauses, ["1 0", "0"])
    assert not mine.valid and not theirs.valid
    assert mine.first_failed_line == 1 and theirs.first_failed_line == 1


def test_rat_pivot_is_first_literal_only():
    # Lemma (1 v 6) on the same F: RAT on its FIRST literal (1) fails
    # (the resolvent (1 v 6 v 4 v 5) is neither a tautology nor AT),
    # and it is not RUP either. RAT on the SECOND literal (6) would
    # succeed vacuously (no clause contains -6), so a checker that
    # used any literal as the pivot would accept this lemma. Both
    # checkers must reject it at line 1 -- the proof has no empty
    # clause, so a line-1 failure proves the lemma itself was
    # rejected, not a later step.
    clauses = [[1, 2, 3], [-1, 4, 5]]
    mine, theirs = _agree(clauses, ["1 6 0"])
    assert not mine.valid and not theirs.valid
    assert mine.first_failed_line == 1 and theirs.first_failed_line == 1


def test_tautological_and_duplicate_literal_lemmas():
    clauses = [[1], [-1]]
    # (1 v -1 v 2) is a tautology: negating it is contradictory, so it
    # is AT (RUP) in both checkers.
    mine, theirs = _agree(clauses, ["1 -1 2 0", "0"])
    assert mine.valid and theirs.valid
    # Duplicate literals are deduped: (1 v 1) is the unit (1), RUP.
    mine, theirs = _agree(clauses, ["1 1 0", "0"])
    assert mine.valid and theirs.valid


# ---------------------------------------------------------------------------
# Deletion cases
# ---------------------------------------------------------------------------


def test_deletion_of_unit_clause_is_ignored_by_both():
    clauses = [[1], [-1, 2], [-2]]
    # Delete the unit (1) -- both checkers ignore it (DRAT-trim default)
    # and the proof still derives the empty clause.
    proof = ["d 1 0", "2 0", "0"]
    mine, theirs = _agree(clauses, proof)
    assert mine.valid and theirs.valid
    assert mine.n_deletions_ignored == theirs.n_deletions_ignored_reason
    assert mine.n_deletions_ignored >= 1


def test_deletion_of_root_reason_clause_is_ignored_by_both():
    # (1) is a unit; (-1 v 2) is a root-level reason for 2 once (1) is
    # propagated. Deleting (-1 v 2) must be ignored by both checkers.
    clauses = [[1], [-1, 2], [-2, 3], [-3]]
    proof = ["d -1 2 0", "2 0", "0"]
    mine, theirs = _agree(clauses, proof)
    assert mine.valid and theirs.valid
    assert mine.n_deletions_ignored >= 1


def test_applied_deletion_is_honoured_by_both():
    # Delete a clause that is neither a unit nor a root reason, then
    # offer a lemma that only follows with the deleted clause present:
    # both checkers must reject it.
    # F = (1 v 2) & (-1 v 2) & (1 v -2) & (-1 v -2) & (3 v 1) & (-3 v 1).
    # Delete (3 v 1) [not a unit, not a root reason: no units at root].
    # Lemma (1) is RUP with (3 v 1) present? Assuming -1: (1 v 2) gives
    # 2; (-1 v 2) is satisfied; (1 v -2) gives -2 -- conflict with 2.
    # So (1) is RUP even without (3 v 1). Use a different lemma: (3).
    # Assuming -3: (-3 v 1) gives 1; (1 v 2) satisfied; (-1 v 2) gives 2;
    # (1 v -2) satisfied; (-1 v -2) is falsified (1 true, 2 true) --
    # wait, (-1 v -2) with 1 and 2 true is falsified, so (3) IS RUP
    # without (3 v 1) as well. Instead delete (-1 v -2): then (3) is no
    # longer RUP (assuming -3 gives 1, 2, and no clause is falsified).
    clauses = [[1, 2], [-1, 2], [1, -2], [-1, -2], [3, 1], [-3, 1]]
    proof = ["d -1 -2 0", "3 0", "0"]
    mine, theirs = _agree(clauses, proof)
    assert not mine.valid and not theirs.valid
    assert mine.n_deletions_applied == 1 and theirs.n_deletions_applied == 1


def test_missing_deletion_is_ignored_and_counted_by_both():
    clauses = [[1], [-1]]
    proof = ["d 9 9 0", "0"]
    mine, theirs = _agree(clauses, proof)
    assert mine.valid and theirs.valid
    assert mine.n_deletions_ignored >= 1
    assert theirs.n_deletions_ignored_missing >= 1


def test_strict_deletions_disagree_in_the_expected_direction():
    # The same proof as test_deletion_of_unit_clause_is_ignored_by_both,
    # but with deletions applied strictly: deleting the unit (1) removes
    # the only way to derive (2) by RUP, so the strict checker rejects
    # while both convention checkers accept. This is the documented
    # incompleteness trade-off of the DRAT-trim deletion convention, not
    # a soundness failure: ignoring a deletion can only keep more
    # clauses, never fewer, so acceptance still implies UNSAT.
    clauses = [[1], [-1, 2], [-2]]
    proof = ["d 1 0", "2 0", "0"]
    mine = nova_check_drat(clauses, proof)
    theirs = check_drat(clauses, proof)
    strict = nova_check_drat_strict(clauses, proof)
    assert mine.valid and theirs.valid
    assert not strict.valid
    assert strict.first_failed_line == 2


def test_random_differential_fuzz():
    rng = random.Random(20261125)
    disagreements = 0
    compared = 0
    for trial in range(300):
        n = rng.randint(1, 5)
        m = rng.randint(0, 8)
        clauses = []
        for _ in range(m):
            k = rng.randint(0, 3)
            clause = []
            for _ in range(k):
                v = rng.randint(1, n)
                clause.append(v if rng.random() < 0.5 else -v)
            clauses.append(clause)
        # Random proof: a mix of additions, deletions, comments, blanks.
        proof = []
        for _ in range(rng.randint(0, 6)):
            kind = rng.random()
            if kind < 0.15:
                proof.append("c a comment")
            elif kind < 0.35:
                lits = [rng.choice([v, -v]) for v in range(1, n + 1)
                        for _ in range(rng.randint(0, 2))]
                proof.append("d " + " ".join(map(str, lits)) + " 0")
            else:
                lits = [rng.choice([v, -v]) for v in range(1, n + 1)
                        for _ in range(rng.randint(0, 3))]
                proof.append(" ".join(map(str, lits)) + " 0")
        mine = nova_check_drat(clauses, proof)
        theirs = check_drat(clauses, proof)
        compared += 1
        if mine.valid != theirs.valid:
            disagreements += 1
            print(f"DISAGREEMENT trial {trial}: clauses={clauses} proof={proof} "
                  f"nova={mine.valid} ({mine.reason}) om_lab={theirs.valid} ({theirs.reason})")
    assert compared == 300
    assert disagreements == 0


# ---------------------------------------------------------------------------
# Third opinion: DRAT-trim (only when the binary is available)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("OM_DRAT_TRIM"),
    reason="set OM_DRAT_TRIM=/path/to/drat-trim to run the third-opinion cross-check",
)
def test_drat_trim_agrees_with_both_checkers():
    """DRAT-trim is a third, independently maintained checker. On the
    fixtures below it must agree with both Python checkers; a
    disagreement would have to be investigated, not settled by vote."""
    binary = os.environ["OM_DRAT_TRIM"]
    fixtures = [
        (3, [[1, 2, 3], [-1, 2, 3], [1, -2, 3], [1, 2, -3],
            [-1, -2, 3], [-1, 2, -3], [1, -2, -3], [-1, -2, -3]],
         ["1 0", "2 0", "0"], True),
        (3, [[1], [-1, 2], [-2]], ["d 1 0", "2 0", "0"], True),
        (3, [[1, 2], [-1, 2], [1, -2], [-1, -2], [3, 1], [-3, 1]],
         ["d -1 -2 0", "3 0", "0"], False),
        (5, [[1, 2, 3], [-1, 4, 5]], ["1 0", "0"], False),
    ]
    for n, clauses, proof, expected in fixtures:
        a = check_drat(clauses, proof).valid
        b = nova_check_drat(clauses, proof).valid
        c = run_drat_trim(binary, n, clauses, proof)["verdict"]
        assert a == b == expected
        assert (c == "VERIFIED") == expected, f"DRAT-trim disagrees on {clauses} {proof}"
