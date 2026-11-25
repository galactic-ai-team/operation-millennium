"""Tests for the independent DRAT checker and the UNSAT certifiers.

Claim level of everything verified here: [Empirical Observation] on the
listed fixtures and seeds. Passing these tests does not prove the checker
correct; it is evidence that it accepts genuine certificates and rejects the
corrupted ones we could construct.

DRAT-trim cross-checks run only when a DRAT-trim binary is available, via
``OM_DRAT_TRIM=/path/to/drat-trim`` or ``drat-trim`` on ``PATH``.
"""

from __future__ import annotations

import os
import random
import shutil

import pytest
from pysat.solvers import Solver

from om_lab.certify import (
    certify_tseitin_by_construction,
    label_unsat_claim,
    reference_certificate,
)
from om_lab.generators import generate_random_3sat
from om_lab.hard_instances import generate_php
from om_lab.matched_instances import (
    disconnected_two_k4,
    encode_tseitin,
    generate_matched_tseitin_pair,
    k33,
    k4,
    petersen_graph,
    prism_graph,
    replace_metadata,
)
from om_lab.proof_check import (
    ProofParseError,
    check_drat,
    dimacs_text,
    parse_drat,
    proof_sha256,
    run_drat_trim,
)
from om_lab.solvers import SolveResult, Status, Verification, solve_dpll, solve_pysat

DRAT_TRIM = os.environ.get("OM_DRAT_TRIM") or shutil.which("drat-trim")
needs_drat_trim = pytest.mark.skipif(DRAT_TRIM is None, reason="DRAT-trim binary not available")


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def _solve_with_proof(backend: str, clauses):
    with Solver(name=backend, bootstrap_with=clauses, with_proof=True) as solver:
        sat = solver.solve()
        return sat, (None if sat else [str(line) for line in solver.get_proof()])


def _unsat_cases(count: int, n: int = 20, m: int = 100, seed0: int = 5000, backend: str = "cd195"):
    cases = []
    seed = seed0
    while len(cases) < count:
        inst = generate_random_3sat(n, m, seed=seed)
        seed += 1
        sat, proof = _solve_with_proof(backend, inst.clauses)
        if not sat:
            cases.append((inst, proof))
    return cases


def _max_satisfiable_prefix(clauses):
    """Largest satisfiable clause prefix (prefixes only lose models as they grow)."""
    lo, hi = 0, len(clauses)  # prefix of length lo is SAT; full formula is UNSAT
    while hi - lo > 1:
        mid = (lo + hi) // 2
        with Solver(name="g4", bootstrap_with=clauses[:mid]) as solver:
            if solver.solve():
                lo = mid
            else:
                hi = mid
    return clauses[:lo]


def _naive_check(clauses, proof_lines) -> bool:
    """Independent, deliberately simple DRAT oracle (full-scan propagation).

    Same acceptance rule and deletion convention as om_lab.proof_check, but
    written separately with lists and repeated scans, so a shared bug is
    unlikely. Assumes the proof text is well formed.
    """
    db = [tuple(dict.fromkeys(c)) for c in clauses]
    if any(len(c) == 0 for c in db):
        return True

    def up(assumptions):
        val: dict[int, bool] = {}
        for lit in assumptions:
            if abs(lit) in val and val[abs(lit)] != (lit > 0):
                return True, val
            val[abs(lit)] = lit > 0
        changed = True
        while changed:
            changed = False
            for clause in db:
                if any(abs(l) in val and val[abs(l)] == (l > 0) for l in clause):
                    continue
                free = [l for l in clause if abs(l) not in val]
                if not free:
                    return True, val
                if len(free) == 1:
                    val[abs(free[0])] = free[0] > 0
                    changed = True
        return False, val

    for line in proof_lines:
        tokens = line.split()
        if not tokens or tokens[0] == "c":
            continue
        deletion = tokens[0] == "d"
        nums = [int(t) for t in (tokens[1:] if deletion else tokens)]
        lits = tuple(dict.fromkeys(nums[:-1]))
        if deletion:
            idx = next((i for i in range(len(db) - 1, -1, -1) if sorted(db[i]) == sorted(lits)), None)
            if idx is None or len(lits) <= 1:
                continue
            conflict, val = up([])
            if conflict:
                continue
            values = [val.get(abs(l)) for l in lits]
            if all(v is not None for v in values) and sum(val[abs(l)] == (l > 0) for l in lits) == 1:
                continue
            del db[idx]
            continue
        conflict, _ = up([-l for l in lits])
        if not conflict:
            if not lits:
                return False
            pivot = lits[0]
            for other in list(db):
                if -pivot not in other:
                    continue
                resolvent = set(lits) | {l for l in other if l != -pivot}
                if any(-l in resolvent for l in resolvent):
                    continue
                if not up([-l for l in resolvent])[0]:
                    return False
        if not lits:
            return True
        db.append(lits)
    return False


def _mutations(proof, rng):
    """Corrupted variants of a proof: drop, sign-flip, swap, spurious deletion."""
    additions = [i for i, line in enumerate(proof) if not line.startswith("d") and line.strip() != "0"]
    out = []
    if proof:
        k = rng.randrange(len(proof))
        out.append(proof[:k] + proof[k + 1:])
    if additions:
        k = rng.choice(additions)
        toks = proof[k].split()
        j = rng.randrange(len(toks) - 1)
        toks[j] = str(-int(toks[j]))
        out.append(proof[:k] + [" ".join(toks)] + proof[k + 1:])
    if len(proof) > 2:
        a, b = sorted(rng.sample(range(len(proof)), 2))
        swapped = list(proof)
        swapped[a], swapped[b] = swapped[b], swapped[a]
        out.append(swapped)
    return out


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


def test_parse_drat_accepts_additions_deletions_comments():
    steps = parse_drat(["1 -2 0", "d 1 -2 0", "", "c comment", "0"])
    assert [(s.is_deletion, s.literals) for s in steps] == [
        (False, (1, -2)),
        (True, (1, -2)),
        (False, ()),
    ]


@pytest.mark.parametrize(
    "bad",
    ["1 2", "1 0 2 0", "x 0", "d", "1_0 0", "١ 0", "+1 0", "d d 1 0", "1 -0 0"],
)
def test_malformed_certificates_are_rejected_not_accepted(bad):
    with pytest.raises(ProofParseError):
        parse_drat([bad])
    result = check_drat([[1], [-1]], [bad, "0"])
    assert not result.valid
    assert "malformed certificate" in result.reason


# --------------------------------------------------------------------------
# Genuine certificates
# --------------------------------------------------------------------------


@pytest.mark.parametrize("backend", ["cd195", "g4", "lgl"])
def test_genuine_random_3sat_proofs_accepted(backend):
    for inst, proof in _unsat_cases(6, backend=backend):
        result = check_drat(inst.clauses, proof)
        assert result.valid, result.reason
        assert result.empty_clause_line is not None


def test_genuine_structured_proofs_accepted():
    formulas = [generate_php(n).clauses for n in (2, 3, 4)]
    for graph in (k4(), k33(), petersen_graph()):
        formulas.append(generate_matched_tseitin_pair(graph).odd.clauses)
    for clauses in formulas:
        sat, proof = _solve_with_proof("cd195", [list(c) for c in clauses])
        assert not sat
        assert check_drat(clauses, proof).valid


def test_trivial_refutations():
    assert check_drat([[1], []], []).valid  # formula contains the empty clause
    assert check_drat([[1], [-1]], ["0"]).valid
    assert check_drat([[1], [-1]], ["0", "d -1 0"]).lines_after_empty_clause == 1
    assert not check_drat([[1], [-1]], []).valid  # a refutation must add the empty clause


# --------------------------------------------------------------------------
# Corrupted certificates (Section 4.3: "UNSAT claim with corrupted certificate")
# --------------------------------------------------------------------------


def test_truncated_certificate_rejected():
    for inst, proof in _unsat_cases(5):
        assert proof[-1] == "0"
        result = check_drat(inst.clauses, proof[:-1])
        assert not result.valid
        assert "does not derive the empty clause" in result.reason


def test_no_certificate_is_ever_accepted_for_a_satisfiable_formula():
    """Soundness probe: any accepted certificate for a SAT formula is a bug."""
    rng = random.Random(20261125)
    checked = 0
    for inst, proof in _unsat_cases(12):
        satisfiable = _max_satisfiable_prefix(inst.clauses)
        candidates = [proof, ["0"], []] + _mutations(proof, rng)
        for candidate in candidates:
            assert not check_drat(satisfiable, candidate).valid
            assert not _naive_check(satisfiable, candidate)
            checked += 1
    assert checked >= 60


def test_rat_lemma_with_fresh_variable_accepted():
    xor_unsat = [[1, 2], [-1, 2], [1, -2], [-1, -2]]
    result = check_drat(xor_unsat, ["3 0", "1 0", "0"])
    assert result.valid
    assert result.n_rat == 1 and result.n_rup == 2


def test_lemma_neither_rup_nor_rat_rejected():
    result = check_drat([[1, 2]], ["-1 0", "-2 0", "0"])
    assert not result.valid
    assert result.first_failed_line == 1


def test_rat_pivot_is_first_literal_only():
    # (-2 v 3) is not AT w.r.t. F; it is RAT on the fresh variable 3 but not
    # on -2. DRAT fixes the pivot to the FIRST literal, so the same clause is
    # accepted at line 1 when written "3 -2 0" and rejected when "-2 3 0".
    formula = [[1, 2], [-1, 2]]
    pivot_first = check_drat(formula, ["3 -2 0", "0"])
    assert pivot_first.n_rat == 1
    assert pivot_first.first_failed_line == 2  # fails later, at the empty clause (F is SAT)
    pivot_second = check_drat(formula, ["-2 3 0", "0"])
    assert pivot_second.n_rat == 0
    assert pivot_second.first_failed_line == 1


def test_deletion_of_unit_clause_is_ignored_like_drat_trim():
    result = check_drat([[1], [-1, 2], [-2]], ["d 1 0", "0"])
    assert result.valid
    assert result.n_deletions_ignored_reason == 1


def test_deletion_of_root_reason_clause_is_ignored():
    formula = [[1], [-1, 2], [-2, 3, 4], [-2, 3, -4], [-2, -3, 4], [-2, -3, -4]]
    result = check_drat(formula, ["d -1 2 0", "3 0", "0"])
    assert result.valid
    assert result.n_deletions_ignored_reason == 1


def test_applied_deletion_is_honoured():
    xor_unsat = [[1, 2], [-1, 2], [1, -2], [-1, -2]]
    assert check_drat(xor_unsat, ["2 0", "0"]).valid
    result = check_drat(xor_unsat, ["d 1 2 0", "2 0", "0"])
    assert not result.valid
    assert result.n_deletions_applied == 1


def test_missing_deletion_is_ignored_and_counted():
    result = check_drat([[1], [-1]], ["d 5 6 0", "0"])
    assert result.valid
    assert result.n_deletions_ignored_missing == 1


# --------------------------------------------------------------------------
# Differential tests
# --------------------------------------------------------------------------


def test_checker_matches_naive_oracle_on_genuine_and_mutated_proofs():
    rng = random.Random(7)
    agreements = 0
    for backend in ("cd195", "g4", "lgl"):
        for inst, proof in _unsat_cases(5, backend=backend, seed0=7000):
            for candidate in [proof] + _mutations(proof, rng):
                assert check_drat(inst.clauses, candidate).valid == _naive_check(inst.clauses, candidate)
                agreements += 1
    assert agreements >= 45


@needs_drat_trim
def test_checker_agrees_with_drat_trim():
    rng = random.Random(11)
    for backend in ("cd195", "g4", "lgl"):
        for inst, proof in _unsat_cases(5, n=30, m=150, backend=backend, seed0=9000):
            ours = check_drat(inst.clauses, proof)
            theirs = run_drat_trim(DRAT_TRIM, inst.n_vars, inst.clauses, proof)
            assert ours.valid and theirs["verdict"] == "VERIFIED"
            for candidate in _mutations(proof, rng):
                # DRAT-trim checks only core lemmas (backward mode), so it may
                # accept proofs with an invalid non-core lemma that this forward
                # checker rejects. It must never be the other way round.
                if check_drat(inst.clauses, candidate).valid:
                    verdict = run_drat_trim(DRAT_TRIM, inst.n_vars, inst.clauses, candidate)["verdict"]
                    assert verdict == "VERIFIED"
            satisfiable = _max_satisfiable_prefix(inst.clauses)
            verdict = run_drat_trim(DRAT_TRIM, inst.n_vars, satisfiable, proof)["verdict"]
            assert verdict != "VERIFIED"


@needs_drat_trim
def test_handcrafted_deletion_cases_agree_with_drat_trim():
    cases = [
        ([[1], [-1, 2], [-2]], ["d 1 0", "0"]),
        ([[1], [-1, 2], [-2, 3, 4], [-2, 3, -4], [-2, -3, 4], [-2, -3, -4]], ["d -1 2 0", "3 0", "0"]),
        ([[1, 2], [-1, 2], [1, -2], [-1, -2]], ["3 0", "1 0", "0"]),
    ]
    for clauses, proof in cases:
        n_vars = max(abs(l) for c in clauses for l in c)
        assert check_drat(clauses, proof).valid
        assert run_drat_trim(DRAT_TRIM, n_vars, clauses, proof)["verdict"] == "VERIFIED"


# --------------------------------------------------------------------------
# Certificate identity helpers
# --------------------------------------------------------------------------


def test_proof_hash_and_dimacs_are_canonical():
    assert proof_sha256(["1 0", "0"]) == proof_sha256([" 1 0 ", "0"])
    assert proof_sha256(["1 0", "0"]) != proof_sha256(["0", "1 0"])
    assert dimacs_text(2, [[1, -2], []]) == "p cnf 2 2\n1 -2 0\n0\n"


def test_reference_certificate_is_deterministic_and_timing_free():
    inst, _ = _unsat_cases(1)[0]
    res1, summary1 = reference_certificate(inst.n_vars, inst.clauses)
    res2, summary2 = reference_certificate(inst.n_vars, inst.clauses)
    assert summary1 == summary2
    assert summary1["status"] == Status.UNSAT
    assert summary1["verification_status"] == Verification.UNSAT_PROOF_CHECKED
    cert = summary1["certificate"]
    assert cert["result"] == "VALID" and cert["checker"] == "om_lab.proof_check"
    assert cert["proof_sha256"] == proof_sha256(res1.certificate["proof"])
    assert "elapsed_s" not in str(summary1)


# --------------------------------------------------------------------------
# Known-by-construction certification (Tseitin) and claim labelling
# --------------------------------------------------------------------------


def test_tseitin_odd_charge_known_by_construction_and_proof_checked():
    for graph in (k4(), k33(), petersen_graph(), prism_graph(4)):
        pair = generate_matched_tseitin_pair(graph)
        odd = certify_tseitin_by_construction(pair.odd)
        assert odd["verification_status"] == Verification.UNSAT_KNOWN_BY_CONSTRUCTION
        assert odd["justification"]
        even = certify_tseitin_by_construction(pair.even)
        assert even["verification_status"] == Verification.NOT_APPLICABLE
        # The two independent routes agree.
        certified = solve_pysat(pair.odd.n_vars, [list(c) for c in pair.odd.clauses], certify=True)
        assert certified.verification_status == Verification.UNSAT_PROOF_CHECKED


def test_tseitin_construction_certificate_rejects_tampering():
    pair = generate_matched_tseitin_pair(k4())
    tampered_clauses = list(pair.odd.clauses)
    first = list(tampered_clauses[0])
    first[0] = -first[0]
    tampered = type(pair.odd)(
        graph=pair.odd.graph,
        charges=pair.odd.charges,
        edge_ids=pair.odd.edge_ids,
        n_vars=pair.odd.n_vars,
        clauses=(tuple(first),) + tuple(tampered_clauses[1:]),
        metadata=pair.odd.metadata,
    )
    assert certify_tseitin_by_construction(tampered)["verification_status"] == Verification.INVALID
    bad_meta = replace_metadata(pair.odd, charge_sum_mod2=0)
    assert certify_tseitin_by_construction(bad_meta)["verification_status"] == Verification.INVALID


def test_tseitin_disconnected_uses_per_component_parity():
    graph = disconnected_two_k4()
    one_each = [1, 0, 0, 0, 1, 0, 0, 0]  # even total, odd in both components
    inst = encode_tseitin(graph, one_each)
    assert certify_tseitin_by_construction(inst)["verification_status"] == Verification.UNSAT_KNOWN_BY_CONSTRUCTION
    assert solve_dpll(inst.n_vars, [list(c) for c in inst.clauses]).status == Status.UNSAT


def test_label_unsat_claim():
    clauses = [[1], [-1]]
    primary = solve_dpll(1, clauses)
    assert label_unsat_claim(primary, None) == Verification.UNVERIFIED
    assert label_unsat_claim(primary, solve_pysat(1, clauses)) == Verification.UNSAT_SOLVER_AGREEMENT_ONLY
    assert label_unsat_claim(primary, solve_pysat(1, clauses, certify=True)) == Verification.UNSAT_PROOF_CHECKED
    refuting = SolveResult(
        solver_name="ref", satisfiable=True, model=[1], elapsed_s=0.0, decisions=0,
        propagations=0, verified=True,
    )
    assert label_unsat_claim(primary, refuting) == Verification.INVALID
    with pytest.raises(ValueError):
        label_unsat_claim(solve_dpll(1, [[1]]), None)
