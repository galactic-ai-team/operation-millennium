"""Empirical benchmark: pure DPLL vs PySAT cd195 on PHP_n^(n+1).

**Claim level: Empirical Observation.**  Decision counts and timings on finite
instances do not establish a worst-case separation.  The only proved statement
used here is that PHP_n^(n+1) is unsatisfiable for every n (Haken 1985).

Run:

    python -m om_lab.benchmark_php --n-min 3 --n-max 7 --out results/php_benchmark.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .hard_instances import generate_php
from .solvers import solve_dpll, solve_pysat


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-min", type=int, default=3)
    parser.add_argument("--n-max", type=int, default=7)
    parser.add_argument("--out", type=Path, default=Path("results/php_benchmark.jsonl"))
    parser.add_argument("--dpll-max-decisions", type=int, default=200_000)
    parser.add_argument("--dpll-max-seconds", type=float, default=30.0)
    parser.add_argument("--pysat-solver", type=str, default="cd195")
    args = parser.parse_args(argv)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    print(
        f"{'n':>3}  {'vars':>6}  {'clauses':>8}  "
        f"{'dpll_dec':>10}  {'dpll_s':>9}  {'pysat_dec':>10}  {'pysat_s':>9}  "
        f"{'dpll_timeout':>13}  {'pysat_sat':>10}"
    )

    for n in range(args.n_min, args.n_max + 1):
        inst = generate_php(n)
        dpll_res = solve_dpll(
            inst.n_vars,
            inst.clauses,
            max_decisions=args.dpll_max_decisions,
            max_seconds=args.dpll_max_seconds,
        )
        pysat_res = solve_pysat(
            inst.n_vars,
            inst.clauses,
            solver_name=args.pysat_solver,
        )

        row = {
            "family": "PHP",
            "n": n,
            "n_vars": inst.n_vars,
            "n_clauses": inst.n_clauses,
            "dpll": {
                "satisfiable": dpll_res.satisfiable,
                "decisions": dpll_res.decisions,
                "propagations": dpll_res.propagations,
                "elapsed_s": dpll_res.elapsed_s,
                "timed_out": dpll_res.timed_out,
                "verified": dpll_res.verified,
            },
            "pysat": {
                "solver": pysat_res.solver_name,
                "satisfiable": pysat_res.satisfiable,
                "decisions": pysat_res.decisions,
                "propagations": pysat_res.propagations,
                "elapsed_s": pysat_res.elapsed_s,
                "verified": pysat_res.verified,
            },
            "claim_level": "Empirical Observation",
        }
        rows.append(row)
        print(
            f"{n:>3}  {inst.n_vars:>6}  {inst.n_clauses:>8}  "
            f"{dpll_res.decisions:>10}  {dpll_res.elapsed_s:>9.4f}  "
            f"{pysat_res.decisions:>10}  {pysat_res.elapsed_s:>9.4f}  "
            f"{str(dpll_res.timed_out):>13}  {str(pysat_res.satisfiable):>10}"
        )

    with args.out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    print(f"\nWrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

