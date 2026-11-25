"""Experiment harness for running solvers over generated instances and logging JSONL.

Repaired for OM-C001-R2 (``docs/phase3/DISCOVERY_ROUND_01.md`` Section 4.2):

* every record preserves the explicit ``status`` (SAT / UNSAT / UNKNOWN),
  the ``verification_status``, ``timed_out`` and the ``stop_reason``;
* budget-exhausted runs are logged as UNKNOWN observations instead of
  aborting the run (the old harness raised on every ``verified=False``);
* completed UNSAT returns without a checked certificate are logged as
  ``UNVERIFIED``; they are not silently excluded and not relabelled;
* an invalid SAT witness is still rejected: the harness raises, because a
  solver that returns a model violating the formula is broken.

For the frozen OM-C001-R2 experiment use :mod:`om_lab.width_experiment`,
which adds one-record-per-instance accounting, proof certificates,
deterministic output and the confirmatory freeze guard.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Iterable, Sequence

from om_lab.generators import CNFInstance
from om_lab.solvers import SolveResult, Status, Verification, solve_dpll, solve_pysat


@dataclass(frozen=True)
class ExperimentRecord:
    """Single logged solver run on a CNF instance.

    ``verified`` is True only for an independently checked claim (see
    :mod:`om_lab.solvers`). The four fields added for Section 4.2 have
    defaults so older constructors keep working.
    """

    timestamp_utc: str
    problem: str
    seed: int | None
    n_vars: int
    n_clauses: int
    ratio: float
    solver: str
    satisfiable: bool
    verified: bool
    elapsed_s: float
    decisions: int
    propagations: int
    status: str = ""
    verification_status: str = ""
    timed_out: bool = False
    stop_reason: str | None = None


class InvalidWitnessError(AssertionError):
    """A solver returned a SAT model that does not satisfy the formula."""


def run_cnf_harness(
    instances: Iterable[CNFInstance],
    solvers: Sequence[Callable[[int, list[list[int]]], SolveResult]] | None = None,
) -> list[ExperimentRecord]:
    """Run one or more solvers on an iterable of CNF instances.

    UNKNOWN (budget-exhausted) and UNVERIFIED UNSAT results are retained as
    records. An INVALID SAT witness raises :class:`InvalidWitnessError`.
    """
    if solvers is None:
        solver_fns: list[Callable[[int, list[list[int]]], SolveResult]] = [
            lambda n, c: solve_pysat(n, c),
            lambda n, c: solve_dpll(n, c),
        ]
    else:
        solver_fns = list(solvers)

    records: list[ExperimentRecord] = []
    for inst in instances:
        for fn in solver_fns:
            res = fn(inst.n_vars, inst.clauses)
            if res.status == Status.SAT and res.verification_status == Verification.INVALID:
                raise InvalidWitnessError(
                    f"Solver {res.solver_name} returned a SAT model that fails witness checking"
                )
            seed_val = inst.metadata.get("seed")
            records.append(
                ExperimentRecord(
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    problem=str(inst.metadata.get("problem", "cnf")),
                    seed=seed_val if isinstance(seed_val, int) else None,
                    n_vars=inst.n_vars,
                    n_clauses=inst.n_clauses,
                    ratio=round(inst.ratio, 6),
                    solver=res.solver_name,
                    satisfiable=res.satisfiable,
                    verified=res.verified,
                    elapsed_s=res.elapsed_s,
                    decisions=res.decisions,
                    propagations=res.propagations,
                    status=res.status,
                    verification_status=res.verification_status,
                    timed_out=res.timed_out,
                    stop_reason=res.stop_reason,
                )
            )
    return records


def write_jsonl(records: Iterable[ExperimentRecord], path: str | Path) -> Path:
    """Write experiment records as JSON lines."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(asdict(rec)) + "\n")
    return out_path
