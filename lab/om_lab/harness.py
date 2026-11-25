"""Experiment harness for running solvers over generated instances and logging JSONL."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Iterable, Sequence

from om_lab.generators import CNFInstance
from om_lab.solvers import SolveResult, solve_dpll, solve_pysat


@dataclass(frozen=True)
class ExperimentRecord:
    """Single logged solver run on a CNF instance."""

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


def run_cnf_harness(
    instances: Iterable[CNFInstance],
    solvers: Sequence[Callable[[int, list[list[int]]], SolveResult]] | None = None,
) -> list[ExperimentRecord]:
    """Run one or more solvers on an iterable of CNF instances."""
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
            if not res.verified:
                raise AssertionError(
                    f"Solver {res.solver_name} returned an unverified SAT model!"
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
