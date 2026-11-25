"""Certification of satisfiability claims (``DISCOVERY_ROUND_01.md`` Section 4.1).

Two independent routes to a certified UNSAT label:

* ``UNSAT_PROOF_CHECKED`` -- a proof-producing reference solver (CaDiCaL
  1.9.5 through PySAT, ``cd195``) emits a DRAT certificate for the original
  formula and :mod:`om_lab.proof_check` (standard library only, no shared
  code with any solver) accepts it. See :func:`reference_certificate`.
* ``UNSAT_KNOWN_BY_CONSTRUCTION`` -- the instance is shown to *be* a
  construction whose unsatisfiability is a justified mathematical statement.
  Implemented for cubic Tseitin parity formulas from
  :mod:`om_lab.matched_instances`: the graph is validated, the CNF is
  re-encoded from (graph, charges, edge ids) and compared clause-for-clause,
  the charge metadata is validated, and at least one connected component
  must have odd total charge. See :func:`certify_tseitin_by_construction`.

Solver agreement without a checked certificate is ``UNSAT_SOLVER_AGREEMENT_ONLY``
(useful cross-checking, not proof evidence), and a lone UNSAT return is
``UNVERIFIED``.

Claim levels: the Tseitin parity criterion is a standard result
(``DISCOVERY_ROUND_01.md`` Section 5.2, labelled there "Proved -- pending
independent team review"); this module does not assert a Lean-Verified
status for it. The correctness of this code is [Claim Level: Empirical
Observation] (tested, not formally verified).
"""

from __future__ import annotations

import operator
from typing import Sequence

from om_lab.solvers import SolveResult, Status, Verification, solve_pysat

__all__ = [
    "REFERENCE_BACKEND",
    "TSEITIN_JUSTIFICATION",
    "certify_tseitin_by_construction",
    "label_unsat_claim",
    "reference_certificate",
]

#: Proof-producing reference backend. Validated together with the checker by
#: ``python -m om_lab.width_experiment validate-certifier`` before any freeze.
REFERENCE_BACKEND = "cd195"

TSEITIN_JUSTIFICATION = (
    "Tseitin parity argument: summing the vertex parity equations of one "
    "connected component counts every edge variable of that component twice, "
    "so the sum of the component's charges must be 0 mod 2; a component with "
    "odd total charge therefore has no satisfying assignment "
    "(docs/phase3/DISCOVERY_ROUND_01.md Section 5.2; om_lab.matched_instances)."
)


def reference_certificate(
    n_vars: int,
    clauses: Sequence[Sequence[int]],
    backend: str = REFERENCE_BACKEND,
) -> tuple[SolveResult, dict]:
    """Run the proof-producing reference solver and summarise the outcome.

    Returns ``(result, summary)``. ``summary`` is JSON-ready and contains no
    timing, so it can enter deterministic experiment records. For UNSAT it
    includes the certificate hash, the checker identity and version, and the
    check result; the proof lines themselves stay in
    ``result.certificate["proof"]``.
    """
    result = solve_pysat(n_vars, clauses, solver_name=backend, certify=True)
    stats = result.solver_stats or {}
    summary: dict = {
        "backend": result.solver_name,
        "status": result.status,
        "verification_status": result.verification_status,
        "decisions": int(stats.get("decisions", 0)),
        "conflicts": int(stats.get("conflicts", 0)),
        "propagations": int(stats.get("propagations", 0)),
        "restarts": int(stats.get("restarts", 0)),
    }
    if result.certificate is not None:
        cert = result.certificate
        summary["certificate"] = {
            key: cert[key]
            for key in (
                "kind",
                "backend",
                "backend_version",
                "proof_sha256",
                "proof_steps",
                "checker",
                "checker_version",
                "checker_sha256",
                "result",
            )
        }
        summary["certificate"]["reason"] = cert["check"]["reason"]
        summary["certificate"]["n_rup"] = cert["check"]["n_rup"]
        summary["certificate"]["n_rat"] = cert["check"]["n_rat"]
    return result, summary


def certify_tseitin_by_construction(instance) -> dict:
    """Certify an odd-charge Tseitin instance as UNSAT by construction.

    ``instance`` is a :class:`om_lab.matched_instances.TseitinInstance`.
    Returns ``{"verification_status", "justification", "checks", "reason"}``:

    * ``UNSAT_KNOWN_BY_CONSTRUCTION`` only if every validation passes and
      some component has odd total charge;
    * ``NOT_APPLICABLE`` if the instance is a valid construction but every
      component has even charge (no UNSAT claim follows from construction);
    * ``INVALID`` if the instance does not match the construction it claims
      (invalid graph, clauses differing from a fresh encoding, or metadata
      inconsistent with the charges), or if it is not a well-formed integer
      CNF. That last case covers float or bool edge identifiers, which
      ``encode_tseitin`` accepted at ``f398de6``
      (``docs/phase4/reviews/REVIEW_PR8_CLAUDE.md`` CLAUDE-R8-07).
    """
    from om_lab.matched_instances import (
        encode_tseitin,
        parity_obstruction,
        validate_graph,
        validate_metadata,
    )
    from om_lab.solvers import normalize_cnf

    checks: dict[str, object] = {}
    try:
        # Integer CNF over 1..n_vars, with integer edge identifiers; raises
        # TypeError/ValueError for float or bool identifiers and literals.
        if isinstance(instance.n_vars, bool) or any(isinstance(e, bool) for e in instance.edge_ids):
            raise ValueError("bool used as an integer identifier")
        for edge_id in instance.edge_ids:
            operator.index(edge_id)
        normalize_cnf(instance.n_vars, instance.clauses)
        checks["well_formed_integer_cnf"] = True
        validate_graph(instance.graph, require_connected=False, require_cubic=True)
        checks["graph_simple_cubic"] = True
        rebuilt = encode_tseitin(instance.graph, instance.charges, instance.edge_ids)
        checks["clauses_match_fresh_encoding"] = tuple(map(tuple, rebuilt.clauses)) == tuple(
            map(tuple, instance.clauses)
        )
        checks["n_vars_match"] = rebuilt.n_vars == instance.n_vars
        checks["metadata_valid"] = bool(validate_metadata(instance))
    except (ValueError, TypeError, AssertionError) as exc:
        return {
            "verification_status": Verification.INVALID,
            "justification": None,
            "checks": checks,
            "reason": f"instance does not match the Tseitin construction: {exc}",
        }
    if not all(checks.values()):
        failed = sorted(name for name, ok in checks.items() if not ok)
        return {
            "verification_status": Verification.INVALID,
            "justification": None,
            "checks": checks,
            "reason": f"instance does not match the Tseitin construction: {failed}",
        }
    obstruction = parity_obstruction(instance)
    checks["odd_charge_components"] = [list(comp) for comp in obstruction]
    if not obstruction:
        return {
            "verification_status": Verification.NOT_APPLICABLE,
            "justification": None,
            "checks": checks,
            "reason": "every component has even charge; no UNSAT claim follows from the construction",
        }
    return {
        "verification_status": Verification.UNSAT_KNOWN_BY_CONSTRUCTION,
        "justification": TSEITIN_JUSTIFICATION,
        "checks": checks,
        "reason": "validated odd-charge Tseitin construction",
    }


def label_unsat_claim(primary: SolveResult, reference: SolveResult | None) -> str:
    """Verification label for a primary UNSAT claim given a reference run.

    * reference UNSAT with a valid checked certificate -> ``UNSAT_PROOF_CHECKED``
    * reference UNSAT with a rejected certificate -> ``INVALID``
    * reference SAT with a checked witness -> ``INVALID`` (claim refuted)
    * reference SAT with an unchecked or invalid witness -> ``UNVERIFIED``
    * reference UNSAT without a certificate -> ``UNSAT_SOLVER_AGREEMENT_ONLY``
    * no reference -> ``UNVERIFIED``
    """
    if primary.status != Status.UNSAT:
        raise ValueError("label_unsat_claim applies to UNSAT claims only")
    if reference is None:
        return Verification.UNVERIFIED
    if reference.status == Status.SAT:
        # Only a *checked* model refutes the claim.
        if reference.verification_status == Verification.SAT_WITNESS_CHECKED:
            return Verification.INVALID
        return Verification.UNVERIFIED
    if reference.status != Status.UNSAT:
        return Verification.UNVERIFIED
    if reference.verification_status == Verification.UNSAT_PROOF_CHECKED:
        return Verification.UNSAT_PROOF_CHECKED
    if reference.verification_status == Verification.INVALID:
        return Verification.INVALID
    return Verification.UNSAT_SOLVER_AGREEMENT_ONLY
