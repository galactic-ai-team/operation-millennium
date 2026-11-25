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
