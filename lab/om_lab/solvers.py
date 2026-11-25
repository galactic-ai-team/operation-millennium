"""SAT solvers (PySAT CDCL + instrumented pure-Python DPLL baseline) and verifiers.

Result semantics (repaired for OM-C001-R2; ``docs/phase3/DISCOVERY_ROUND_01.md``
Sections 4.1-4.2 and 10.1)
--------------------------------------------------------------------------
Every :class:`SolveResult` carries an explicit ``status``:

* ``SAT`` -- the solver returned a model;
* ``UNSAT`` -- the solver completed and claims unsatisfiability;
* ``UNKNOWN`` -- a decision or wall-clock budget was exhausted; no
  satisfiability claim is made, and UNKNOWN is never UNSAT;
* ``ERROR`` -- reserved for infrastructure failures recorded by harnesses.

and a ``verification_status`` from the Section 4.1 vocabulary
(:class:`Verification`). ``verified`` is now strict: it is True only when the
claim was independently checked -- a SAT model checked against every clause
(``SAT_WITNESS_CHECKED``), an UNSAT proof certificate checked by
:mod:`om_lab.proof_check` (``UNSAT_PROOF_CHECKED``), or a validated
construction (``UNSAT_KNOWN_BY_CONSTRUCTION``). A completed UNSAT return with
no checked certificate is ``UNVERIFIED`` and ``verified=False``; before this
repair it was reported as ``verified=True``, which Section 10.1 rejects as
independent verification.

The DPLL search itself is unchanged
-----------------------------------
``solve_dpll``'s inner ``simplify`` / ``dpll`` functions are character-for-
character the ed6d557 implementation: unit propagation, first shortest
clause, its first remaining variable, True before False, the branch-attempt
counter (field name ``decisions``), and the budget check at recursive entry.
``lab/tests/test_width_experiment.py`` checks that status, branch attempts,
propagations and models match a vendored verbatim copy of the ed6d557 solver.
The only additions are input validation and result labelling around it.

Input validation
----------------
Both solvers now reject literal ``0`` and literals outside ``1..n_vars``
(``ValueError``) instead of returning a truncated, unverifiable model, and
both materialise their clause input once so witness checking can never run
against an exhausted iterator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import operator
import time
from typing import Iterable, Sequence

import pysat
from pysat.solvers import Solver as PySATSolver

from om_lab.proof_check import (
    CHECKER_NAME,
    CHECKER_VERSION,
    check_drat,
    checker_source_sha256,
    proof_sha256,
)


class Status:
    """Solver outcome vocabulary (Section 4.1)."""

    SAT = "SAT"
    UNSAT = "UNSAT"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"
    ALL = frozenset({SAT, UNSAT, UNKNOWN, ERROR})


class Verification:
    """Verification vocabulary (Section 4.1)."""

    SAT_WITNESS_CHECKED = "SAT_WITNESS_CHECKED"
    UNSAT_PROOF_CHECKED = "UNSAT_PROOF_CHECKED"
    UNSAT_KNOWN_BY_CONSTRUCTION = "UNSAT_KNOWN_BY_CONSTRUCTION"
    UNSAT_SOLVER_AGREEMENT_ONLY = "UNSAT_SOLVER_AGREEMENT_ONLY"
    UNVERIFIED = "UNVERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INVALID = "INVALID"
    ALL = frozenset(
        {
            SAT_WITNESS_CHECKED,
            UNSAT_PROOF_CHECKED,
            UNSAT_KNOWN_BY_CONSTRUCTION,
            UNSAT_SOLVER_AGREEMENT_ONLY,
            UNVERIFIED,
            NOT_APPLICABLE,
            INVALID,
        }
    )
    #: Statuses that count as independent verification of the claim.
    CERTIFIED = frozenset(
        {SAT_WITNESS_CHECKED, UNSAT_PROOF_CHECKED, UNSAT_KNOWN_BY_CONSTRUCTION}
    )


class StopReason:
    """Why a run ended without a satisfiability claim."""

    DECISION_BUDGET = "decision_budget"
    TIME_BUDGET = "time_budget"


#: Which verification statuses are meaningful for each solver status.
ALLOWED_VERIFICATION: dict[str, frozenset[str]] = {
    Status.SAT: frozenset({Verification.SAT_WITNESS_CHECKED, Verification.INVALID}),
    Status.UNSAT: frozenset(
        {
            Verification.UNSAT_PROOF_CHECKED,
            Verification.UNSAT_KNOWN_BY_CONSTRUCTION,
            Verification.UNSAT_SOLVER_AGREEMENT_ONLY,
            Verification.UNVERIFIED,
            Verification.INVALID,
        }
    ),
    Status.UNKNOWN: frozenset({Verification.NOT_APPLICABLE}),
    Status.ERROR: frozenset({Verification.NOT_APPLICABLE}),
}


@dataclass(frozen=True)
class SolveResult:
    """Standardized solver output with instrumentation and verification status.

    ``satisfiable`` and ``timed_out`` are kept for compatibility:
    ``satisfiable == (status == "SAT")`` and ``timed_out`` means a decision
    or wall-clock budget was exhausted (``status == "UNKNOWN"``; see
    ``stop_reason``). Inconsistent combinations raise ``ValueError``.
    """

    solver_name: str
    satisfiable: bool
    model: list[int] | None
    elapsed_s: float
    decisions: int
    propagations: int
    verified: bool
    timed_out: bool = False
    status: str = ""
    verification_status: str = ""
    stop_reason: str | None = None
    certificate: dict | None = field(default=None, compare=False, repr=False)
    solver_stats: dict | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        status = self.status
        if not status:
            if self.timed_out:
                status = Status.UNKNOWN
            else:
                status = Status.SAT if self.satisfiable else Status.UNSAT
        if status not in Status.ALL:
            raise ValueError(f"unknown status {status!r}")
        if self.satisfiable != (status == Status.SAT):
            raise ValueError(f"satisfiable={self.satisfiable} contradicts status {status}")
        if self.timed_out and status != Status.UNKNOWN:
            raise ValueError("timed_out=True requires status UNKNOWN")
        verification = self.verification_status
        if not verification:
            if status == Status.SAT:
                verification = (
                    Verification.SAT_WITNESS_CHECKED if self.verified else Verification.INVALID
                )
            elif status == Status.UNSAT:
                verification = Verification.UNVERIFIED
            else:
                verification = Verification.NOT_APPLICABLE
        if verification not in ALLOWED_VERIFICATION[status]:
            raise ValueError(f"verification_status {verification} is not valid for status {status}")
        if self.verified != (verification in Verification.CERTIFIED):
            raise ValueError(
                f"verified={self.verified} contradicts verification_status {verification} "
                "(verified=True requires an independently checked claim)"
            )
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "verification_status", verification)


def normalize_cnf(n_vars: int, clauses: Iterable[Iterable[int]]) -> list[list[int]]:
    """Materialise and validate a CNF formula.

    Returns a fresh ``list[list[int]]`` preserving clause and literal order.
    Raises ``ValueError`` for a negative ``n_vars``, a literal ``0``, a literal
    outside ``1..n_vars``, or a non-integer (including ``bool``) literal.
    """
    n = operator.index(n_vars)
    if n < 0:
        raise ValueError("n_vars must be non-negative")
    out: list[list[int]] = []
    for idx, clause in enumerate(clauses):
        lits: list[int] = []
        for lit in clause:
            if isinstance(lit, bool):
                raise ValueError(f"clause {idx}: bool literal {lit!r}")
            value = operator.index(lit)
            if value == 0 or abs(value) > n:
                raise ValueError(f"clause {idx}: literal {value} out of range for n_vars={n}")
            lits.append(value)
        out.append(lits)
    return out


def verify_cnf_assignment(clauses: Sequence[Sequence[int]], model: Sequence[int] | None) -> bool:
    """Independently verify that a literal assignment satisfies all CNF clauses.

    A model containing a contradictory pair or the literal ``0`` is malformed
    and rejected. Variables absent from the model satisfy no literal.
    """
    if model is None:
        return False
    assignment: dict[int, bool] = {}
    for lit in model:
        if lit == 0:
            return False
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


def check_sat_witness(clauses: Sequence[Sequence[int]], model: Sequence[int] | None) -> str:
    """``SAT_WITNESS_CHECKED`` if ``model`` satisfies ``clauses``, else ``INVALID``."""
    return (
        Verification.SAT_WITNESS_CHECKED
        if verify_cnf_assignment(clauses, model)
        else Verification.INVALID
    )


def _complete_model(model: Sequence[int], n_vars: int) -> list[int]:
    """Extend a solver model to every variable ``1..n_vars``.

    Variables the backend never saw (they occur in no clause) are set False;
    they are unconstrained, so any value is correct.
    """
    present = {abs(lit) for lit in model}
    out = list(model)
    out.extend(-v for v in range(1, n_vars + 1) if v not in present)
    return out


def solve_pysat(
    n_vars: int,
    clauses: Sequence[Sequence[int]],
    solver_name: str = "cd195",
    certify: bool = False,
) -> SolveResult:
    """Solve a CNF formula using PySAT (default: CaDiCaL 1.9.5 'cd195').

    With ``certify=True`` the backend runs with proof logging. An UNSAT
    result is then checked by :func:`om_lab.proof_check.check_drat`:
    ``UNSAT_PROOF_CHECKED`` if the certificate is valid, ``INVALID`` if not.
    The certificate summary (proof SHA-256, checker identity and version,
    result) is attached as ``result.certificate``; the proof lines are kept
    under ``certificate["proof"]``. Backends without proof logging (for
    example ``m22``) raise ``ValueError`` when ``certify=True``.
    """
    cnf = normalize_cnf(n_vars, clauses)
    n = operator.index(n_vars)
    t0 = time.perf_counter()
    proof: list[str] | None = None
    try:
        with PySATSolver(name=solver_name, bootstrap_with=cnf, with_proof=certify) as solver:
            sat = bool(solver.solve())
            model = list(solver.get_model()) if sat else None
            stats = solver.accum_stats() if hasattr(solver, "accum_stats") else {}
            if certify and not sat:
                proof = [str(line) for line in (solver.get_proof() or [])]
    except NotImplementedError as exc:
        raise ValueError(
            f"PySAT backend {solver_name!r} does not support proof logging: {exc}"
        ) from exc
    elapsed = time.perf_counter() - t0
    decisions = int(stats.get("decisions", 0))
    propagations = int(stats.get("propagations", 0))
    certificate: dict | None = None

    if sat:
        assert model is not None
        model = _complete_model(model, n)
        verification = check_sat_witness(cnf, model)
    elif certify:
        assert proof is not None
        check = check_drat(cnf, proof)
        verification = (
            Verification.UNSAT_PROOF_CHECKED if check.valid else Verification.INVALID
        )
        certificate = {
            "kind": "DRAT",
            "backend": f"pysat:{solver_name}",
            "backend_version": f"python-sat {pysat.__version__}",
            "proof_sha256": proof_sha256(proof),
            "proof_steps": len(proof),
            "checker": CHECKER_NAME,
            "checker_version": CHECKER_VERSION,
            "checker_sha256": checker_source_sha256(),
            "result": "VALID" if check.valid else "INVALID",
            "check": check.to_dict(include_timing=False),
            "proof": proof,
        }
    else:
        verification = Verification.UNVERIFIED

    return SolveResult(
        solver_name=f"pysat:{solver_name}",
        satisfiable=sat,
        model=model,
        elapsed_s=elapsed,
        decisions=decisions,
        propagations=propagations,
        verified=verification in Verification.CERTIFIED,
        timed_out=False,
        status=Status.SAT if sat else Status.UNSAT,
        verification_status=verification,
        certificate=certificate,
        solver_stats={str(k): int(v) for k, v in stats.items()},
    )


class _DPLLBudgetExceeded(Exception):
    """Internal signal: decision or wall-clock budget exhausted."""


def solve_dpll(
    n_vars: int,
    clauses: Sequence[Sequence[int]],
    max_decisions: int | None = None,
    max_seconds: float | None = None,
) -> SolveResult:
    """Pure-Python DPLL baseline with unit propagation and decision/propagation counters.

    ``decisions`` counts branch attempts: it increments for each attempted
    branch value (True, then False). Budgets are checked at recursive entry,
    so with ``max_decisions=B`` an exhausted run reports exactly ``B``
    branch attempts, a completed run at most ``B - 1``, and ``B = 0`` makes
    every run UNKNOWN. Budget exhaustion returns ``status="UNKNOWN"`` with
    ``stop_reason`` ``"decision_budget"`` or ``"time_budget"``. A completed
    UNSAT return is ``UNVERIFIED``: this solver emits no proof certificate.
    """
    validated = normalize_cnf(n_vars, clauses)
    t0 = time.perf_counter()
    deadline = None if max_seconds is None else t0 + max_seconds
    norm_clauses = [list(c) for c in validated]
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
        if max_decisions is not None and stats["decisions"] >= max_decisions:
            raise _DPLLBudgetExceeded
        if deadline is not None and time.perf_counter() > deadline:
            raise _DPLLBudgetExceeded

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

    try:
        solution = dpll(norm_clauses, {})
    except _DPLLBudgetExceeded:
        elapsed = time.perf_counter() - t0
        # The decision check runs before the wall-clock check at every
        # recursive entry, so a reached decision budget identifies the cause.
        if max_decisions is not None and stats["decisions"] >= max_decisions:
            stop_reason = StopReason.DECISION_BUDGET
        else:
            stop_reason = StopReason.TIME_BUDGET
        return SolveResult(
            solver_name="dpll",
            satisfiable=False,
            model=None,
            elapsed_s=elapsed,
            decisions=stats["decisions"],
            propagations=stats["propagations"],
            verified=False,
            timed_out=True,
            status=Status.UNKNOWN,
            verification_status=Verification.NOT_APPLICABLE,
            stop_reason=stop_reason,
        )

    elapsed = time.perf_counter() - t0

    if solution is None:
        return SolveResult(
            solver_name="dpll",
            satisfiable=False,
            model=None,
            elapsed_s=elapsed,
            decisions=stats["decisions"],
            propagations=stats["propagations"],
            verified=False,
            timed_out=False,
            status=Status.UNSAT,
            verification_status=Verification.UNVERIFIED,
        )

    model = [v if solution.get(v, True) else -v for v in range(1, n_vars + 1)]
    verification = check_sat_witness(validated, model)
    return SolveResult(
        solver_name="dpll",
        satisfiable=True,
        model=model,
        elapsed_s=elapsed,
        decisions=stats["decisions"],
        propagations=stats["propagations"],
        verified=verification == Verification.SAT_WITNESS_CHECKED,
        timed_out=False,
        status=Status.SAT,
        verification_status=verification,
    )
