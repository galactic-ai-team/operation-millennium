"""Random 3-SAT phase transition experiment around clause/variable ratio ~4.26."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from om_lab.generators import generate_random_3sat
from om_lab.harness import ExperimentRecord, run_cnf_harness, write_jsonl
from om_lab.solvers import solve_dpll, solve_pysat

DEFAULT_RATIOS = [3.0, 3.5, 3.8, 4.0, 4.2, 4.26, 4.4, 4.6, 5.0, 5.5]


@dataclass(frozen=True)
class RatioSummary:
    ratio: float
    n_clauses: int
    trials: int
    sat_fraction: float
    dpll_median_decisions: float
    dpll_median_time_s: float
    pysat_median_time_s: float


def run_phase_transition(
    n_vars: int = 30,
    trials: int = 20,
    ratios: list[float] | None = None,
    base_seed: int = 2026,
    out_dir: str | Path = "results",
) -> tuple[list[RatioSummary], Path, Path]:
    """Run random 3-SAT sweep across ratios, log JSONL, and generate plot PNG."""
    ratio_list = ratios if ratios is not None else list(DEFAULT_RATIOS)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    all_records: list[ExperimentRecord] = []
    summaries: list[RatioSummary] = []

    for r_idx, ratio in enumerate(ratio_list):
        n_clauses = max(1, round(ratio * n_vars))
        instances = [
            generate_random_3sat(
                n_vars=n_vars,
                n_clauses=n_clauses,
                seed=base_seed + r_idx * 10_000 + t,
            )
            for t in range(trials)
        ]
        records = run_cnf_harness(
            instances,
            solvers=[
                lambda n, c: solve_pysat(n, c, solver_name="cd195"),
                lambda n, c: solve_dpll(n, c),
            ],
        )
        all_records.extend(records)

        pysat_recs = [rec for rec in records if rec.solver.startswith("pysat:")]
        dpll_recs = [rec for rec in records if rec.solver == "dpll"]

        # Consistency check between PySAT and DPLL
        for p_rec, d_rec in zip(pysat_recs, dpll_recs):
            if p_rec.satisfiable != d_rec.satisfiable:
                raise AssertionError(
                    f"Solver disagreement on seed={p_rec.seed}: "
                    f"pysat={p_rec.satisfiable} vs dpll={d_rec.satisfiable}"
                )

        sat_frac = sum(1 for rec in pysat_recs if rec.satisfiable) / len(pysat_recs)
        summaries.append(
            RatioSummary(
                ratio=ratio,
                n_clauses=n_clauses,
                trials=trials,
                sat_fraction=sat_frac,
                dpll_median_decisions=float(
                    statistics.median(rec.decisions for rec in dpll_recs)
                ),
                dpll_median_time_s=float(
                    statistics.median(rec.elapsed_s for rec in dpll_recs)
                ),
                pysat_median_time_s=float(
                    statistics.median(rec.elapsed_s for rec in pysat_recs)
                ),
            )
        )

    jsonl_path = write_jsonl(all_records, out_path / "phase_transition.jsonl")
    plot_path = _save_plot(summaries, n_vars=n_vars, trials=trials, path=out_path / "phase_transition.png")
    return summaries, jsonl_path, plot_path


def _save_plot(
    summaries: list[RatioSummary], n_vars: int, trials: int, path: Path
) -> Path:
    xs = [s.ratio for s in summaries]
    sat_probs = [s.sat_fraction for s in summaries]
    dpll_decisions = [s.dpll_median_decisions for s in summaries]
    dpll_times_ms = [s.dpll_median_time_s * 1000.0 for s in summaries]
    pysat_times_ms = [s.pysat_median_time_s * 1000.0 for s in summaries]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)

    ax1.plot(xs, sat_probs, marker="o", linewidth=2, color="#1f77b4", label="P(SAT)")
    ax1.axvline(4.26, color="#d62728", linestyle="--", linewidth=1.4, label="α ≈ 4.26")
    ax1.set_ylabel("Fraction Satisfiable")
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_title(
        f"Random 3-SAT Phase Transition (n={n_vars} vars, {trials} trials/ratio)"
    )
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best")

    ax2.plot(
        xs,
        dpll_decisions,
        marker="s",
        linewidth=2,
        color="#ff7f0e",
        label="DPLL median decisions",
    )
    ax2.axvline(4.26, color="#d62728", linestyle="--", linewidth=1.4)
    ax2.set_xlabel("Clause-to-Variable Ratio (α = m / n)")
    ax2.set_ylabel("DPLL Median Decisions", color="#ff7f0e")
    ax2.grid(True, alpha=0.3)

    ax2_t = ax2.twinx()
    ax2_t.plot(
        xs,
        dpll_times_ms,
        marker="^",
        linestyle=":",
        color="#2ca02c",
        label="DPLL median (ms)",
    )
    ax2_t.plot(
        xs,
        pysat_times_ms,
        marker="v",
        linestyle=":",
        color="#9467bd",
        label="PySAT cd195 median (ms)",
    )
    ax2_t.set_ylabel("Median Solve Time (ms)")

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_t.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize="small")

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run random 3-SAT phase transition experiment."
    )
    parser.add_argument("--n-vars", type=int, default=30)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out-dir", type=str, default="results")
    args = parser.parse_args()

    summaries, jsonl_path, plot_path = run_phase_transition(
        n_vars=args.n_vars,
        trials=args.trials,
        base_seed=args.seed,
        out_dir=args.out_dir,
    )
    for s in summaries:
        print(
            f"ratio={s.ratio:4.2f} m={s.n_clauses:3d} "
            f"P(SAT)={s.sat_fraction:5.2f} "
            f"dpll_med_dec={s.dpll_median_decisions:6.1f} "
            f"pysat_med_ms={s.pysat_median_time_s*1000:6.3f}"
        )
    print(f"Wrote JSONL log: {jsonl_path}")
    print(f"Wrote plot PNG:  {plot_path}")


if __name__ == "__main__":
    main()
