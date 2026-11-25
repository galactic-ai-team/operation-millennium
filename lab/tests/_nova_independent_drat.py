"""Independently written DRAT checker (Nova, Phase 4 attack on PR #10).

Written from the DRAT definition in Wetzler, Heule & Hunt (SAT 2014) and
Heule's format note (arXiv:1610.06229), NOT from ``om_lab.proof_check``.
Deliberately naive so its correctness is easy to see by reading it:

* clause database: a plain list of frozensets (a multiset);
* unit propagation: a fixpoint scan over the whole database, no watched
  literals, no occurrence lists;
* RAT: for the lemma's first literal, every database clause containing
  its negation is resolved and the resolvent is checked by unit
  propagation;
* deletion convention: the documented DRAT-trim default, implemented
  independently -- a deletion of a missing clause, a unit clause, or a
  clause that is a possible root-level reason is ignored and counted;
  any other deletion removes one copy.

This module imports nothing from ``om_lab`` and nothing outside the
standard library. It is a test oracle, not production code: it is slow
on purpose and must never be used to certify a real experiment run.

[Claim Level: Empirical Observation] for every verdict it produces.
The soundness of DRAT itself is established literature; the claim that
*this* implementation is correct rests on the differential tests in
``test_nova_drat_attack.py``, not on a formal proof.
"""

from __future__ import annotations

import re

__all__ = ["NovaDratResult", "nova_check_drat", "nova_check_drat_strict"]

_INT_TOKEN = re.compile(r"^-?(0|[1-9][0-9]*)$")


class NovaDratResult:
    """Outcome of the independent check (plain object, no om_lab types)."""

    def __init__(self, valid, reason, n_rup=0, n_rat=0, n_deletions_applied=0,
                 n_deletions_ignored=0, empty_clause_line=None, first_failed_line=None):
        self.valid = valid
        self.reason = reason
        self.n_rup = n_rup
        self.n_rat = n_rat
        self.n_deletions_applied = n_deletions_applied
        self.n_deletions_ignored = n_deletions_ignored
        self.empty_clause_line = empty_clause_line
        self.first_failed_line = first_failed_line

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"NovaDratResult(valid={self.valid}, reason={self.reason!r})"


def _parse_proof(proof_lines):
    """Strict DRAT parsing. Returns a list of (is_deletion, literals, line_no).

    Raises ValueError on the first malformed line.
    """
    steps = []
    for line_no, raw in enumerate(proof_lines, start=1):
        if isinstance(raw, (bytes, bytearray)):
            try:
                raw = raw.decode("ascii")
            except UnicodeDecodeError as exc:
                raise ValueError(f"line {line_no}: non-ASCII bytes") from exc
        if not isinstance(raw, str):
            raise ValueError(f"line {line_no}: expected text, got {type(raw).__name__}")
        text = raw.strip()
        if not text:
            continue
        tokens = text.split()
        if tokens[0] == "c":
            continue
        is_deletion = tokens[0] == "d"
        body = tokens[1:] if is_deletion else tokens
        if not body:
            raise ValueError(f"line {line_no}: deletion without literals or terminator")
        for tok in body:
            if not _INT_TOKEN.match(tok):
                raise ValueError(f"line {line_no}: invalid token {tok!r}")
        values = [int(tok) for tok in body]
        if values[-1] != 0:
            raise ValueError(f"line {line_no}: missing terminating 0")
        literals = tuple(values[:-1])
        if any(lit == 0 for lit in literals):
            raise ValueError(f"line {line_no}: literal 0 before end of line")
        steps.append((is_deletion, literals, line_no))
    return steps


def _propagate(db, assumptions):
    """Naive fixpoint unit propagation.

    ``db`` is a list of frozensets. ``assumptions`` are literals to set
    true. Returns ``(conflict, assignment)`` where assignment maps
    variable -> bool. Deterministic: the verdict does not depend on scan
    order, because unit propagation is confluent.
    """
    assignment = {}
    for lit in assumptions:
        var = abs(lit)
        want = lit > 0
        if var in assignment:
            if assignment[var] != want:
                return True, assignment
        else:
            assignment[var] = want
    changed = True
    while changed:
        changed = False
        for clause in db:
            satisfied = False
            open_lits = []
            for lit in clause:
                value = assignment.get(abs(lit))
                if value is None:
                    open_lits.append(lit)
                elif value == (lit > 0):
                    satisfied = True
                    break
            if satisfied:
                continue
            if not open_lits:
                return True, assignment
            if len(open_lits) == 1:
                lit = open_lits[0]
                var = abs(lit)
                if var not in assignment:
                    assignment[var] = lit > 0
                    changed = True
    return False, assignment


def _is_rup(db, lemma):
    """AT/RUP: assuming every literal of the lemma false yields a conflict."""
    conflict, _ = _propagate(db, [-lit for lit in lemma])
    return conflict


def _is_rat(db, lemma):
    """RAT on the lemma's first literal against the current database."""
    if not lemma:
        return False
    pivot = lemma[0]
    for clause in db:
        if -pivot not in clause:
            continue
        resolvent = set(lemma)
        resolvent.update(lit for lit in clause if lit != -pivot)
        if any(-lit in resolvent for lit in resolvent):
            continue  # tautological resolvent: no constraint
        if not _is_rup(db, tuple(resolvent)):
            return False
    return True


def _is_possible_root_reason(db, clause):
    """True iff under root-level unit propagation the clause has exactly
    one true literal and all others false (and none unassigned)."""
    conflict, assignment = _propagate(db, ())
    if conflict:
        return False
    n_true = 0
    for lit in clause:
        value = assignment.get(abs(lit))
        if value is None:
            return False
        if value == (lit > 0):
            n_true += 1
            if n_true > 1:
                return False
    return n_true == 1


def nova_check_drat(clauses, proof_lines, *, strict_deletions=False):
    """Check a text-DRAT refutation with the independent naive checker.

    ``strict_deletions=True`` applies every deletion unconditionally
    (the strict DRAT semantics). The default follows the documented
    DRAT-trim convention: deletions of missing clauses, unit clauses
    and possible root-level reasons are ignored and counted. Ignoring a
    deletion is sound (it only ever keeps more clauses in the database);
    the strict mode is provided to demonstrate the expected disagreement
    direction on proofs that delete a root reason and then rely on it.
    """
    db = []
    for clause in clauses:
        lits = []
        for lit in clause:
            if isinstance(lit, bool):
                raise ValueError(f"invalid literal {lit!r} in formula")
            value = int(lit)
            if value == 0:
                raise ValueError("literal 0 in formula")
            lits.append(value)
        db.append(frozenset(lits))
    if any(not clause for clause in db):
        return NovaDratResult(True, "formula contains the empty clause (trivially UNSAT; proof not needed)")

    try:
        steps = _parse_proof(proof_lines)
    except ValueError as exc:
        return NovaDratResult(False, f"malformed certificate: {exc}")

    n_rup = 0
    n_rat = 0
    n_applied = 0
    n_ignored = 0
    for is_deletion, literals, line_no in steps:
        lemma = frozenset(literals)
        if is_deletion:
            if lemma not in db:
                n_ignored += 1
                continue
            if not strict_deletions:
                if len(lemma) <= 1:
                    n_ignored += 1
                    continue
                root_conflict, _ = _propagate(db, ())
                if root_conflict or _is_possible_root_reason(db, lemma):
                    n_ignored += 1
                    continue
            db.remove(lemma)
            n_applied += 1
            continue
        if _is_rup(db, tuple(lemma)):
            n_rup += 1
        elif lemma and _is_rat(db, tuple(lemma)):
            n_rat += 1
        else:
            kind = "empty clause" if not lemma else "lemma"
            return NovaDratResult(
                False,
                f"line {line_no}: {kind} is neither AT (RUP) nor RAT on its first literal",
                n_rup=n_rup, n_rat=n_rat, n_deletions_applied=n_applied,
                n_deletions_ignored=n_ignored, first_failed_line=line_no,
            )
        if not lemma:
            return NovaDratResult(
                True, "empty clause derived", n_rup=n_rup, n_rat=n_rat,
                n_deletions_applied=n_applied, n_deletions_ignored=n_ignored,
                empty_clause_line=line_no,
            )
        db.append(lemma)
    return NovaDratResult(
        False, "certificate does not derive the empty clause",
        n_rup=n_rup, n_rat=n_rat, n_deletions_applied=n_applied,
        n_deletions_ignored=n_ignored,
    )


def nova_check_drat_strict(clauses, proof_lines):
    """The same checker with every deletion applied unconditionally."""
    return nova_check_drat(clauses, proof_lines, strict_deletions=True)
