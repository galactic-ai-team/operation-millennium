# Phase 2 Laboratory (`om_lab`)

Reproducible Python laboratory for generating NP-complete problem instances, running exact SAT solvers (PySAT CDCL and an instrumented pure-Python DPLL baseline), verifying witnesses, and studying empirical phase transitions.

> **Honesty Rule reminder:** Empirical hardness peaks and solver timings are `[Claim Level: Empirical Observation]` only. They are never proofs of worst-case complexity separations.

## Setup (Free, Local)

```bash
cd lab
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run Tests

```bash
pytest
```

## Run the Random 3-SAT Phase Transition Experiment

Sweeps clause-to-variable ratio $\alpha = m / n$ around the empirical threshold $\alpha_c \approx 4.26$ (Mitchell, Selman, & Levesque, 1992), logs per-trial JSONL results, and writes a two-panel plot to `lab/results/phase_transition.png`:

```bash
python -m om_lab.phase_transition --n-vars 30 --trials 25 --out-dir results
```

## Structural Features & Hardness Analysis

`om_lab.features` computes deterministic structural features of a CNF
instance (clause/variable ratio, literal polarity balance, variable
occurrence degree distribution / entropy, unit-clause density,
variable co-occurrence graph degree stats, and more). It computes no
backbone -- a backbone requires solving; unit-clause density is the
structural proxy included instead.

`om_lab.analyze_hardness` joins those features to harness JSONL logs
(regenerating each `random_3sat` instance from its recorded seed) and
reports Pearson / Spearman correlations with DPLL and PySAT solver
effort around α ≈ 4.26, plus a per-ratio summary and a 90th-percentile
decision-spike comparison:

```bash
# Fresh sweep (default: n=30, 20 trials/ratio, seed 2026)
python -m om_lab.analyze_hardness --out-dir results

# Analyse an existing log instead
python -m om_lab.analyze_hardness --jsonl results/phase_transition.jsonl --out-dir results
```

> **Honesty Rule reminder:** all output of `analyze_hardness` is
> `[Claim Level: Empirical Observation]` only -- finite instances,
> finite seeds, correlation is not causation, and nothing here is a
> proof about worst-case complexity. PySAT conflict counts are *not*
> in the harness JSONL schema, so `--jsonl` mode reports them as
> unavailable; the fresh-sweep mode records them via a separate,
> labelled direct-PySAT pass.
