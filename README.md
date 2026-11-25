# Project 9: Operation Millennium

> **A structured mathematical research workspace and computational laboratory for studying P vs NP, complexity barriers, NP-complete problem structure, and formal verification in Lean 4.**

## Mission & Realistic Expectations

Operation Millennium is run by the **Galactic AI Team** under Research Director **Stephon Bridges**. Rather than treating P vs NP as a lottery ticket or an exercise in AI guesswork, this project builds disciplined research infrastructure:

- Mapping established proofs, failed proof patterns, and mathematical barriers (**Phase 1**)
- Running reproducible experiments on NP-complete problems, solver behavior, and phase transitions (**Phase 2**)
- Formulating testable conjectures, bounds, and algorithmic ideas (**Phase 3**)
- Subjecting every idea to explicit adversarial falsification and barrier checks (**Phase 4**)
- Formalizing verified known theorems and lemmas in Lean 4 (**Phase 5**)
- Preparing rigorous writeups of legitimate findings (**Phase 6**)

**What success realistically looks like:** deep understanding of complexity barriers, clean open-source solver and benchmark tooling, small empirical findings or counterexamples, and Lean-formalized known results—not a resolution of the Millennium Prize Problem.

## The Honesty Rule

**No agent may declare or imply a breakthrough without a rigorous, complete proof.**

- Passing a million test cases, benchmarks, or heuristic runs is **empirical evidence**, never a universal theorem.
- Every claim in this repository must carry an explicit claim level (`Conjecture`, `Empirical Observation`, `Proved`, or `Lean-Verified`). See [`docs/RULES.md`](docs/RULES.md).
- Every cited paper, theorem, and formula must be verified. Never invent citations.

## Team Assignments

| Agent | Research Lane | Coding Agent / Environment |
|---|---|---|
| **Stephon Bridges** | Research Director — strategic direction & unconventional hypotheses | Director |
| **Ace (GPT-6)** | Complexity theory, mathematical proofs, theoretical architecture & Lumi's thought partner | Codex (when available) / ChatGPT |
| **Claude** | Algorithm development & computational experiments | Claude Code (when available) / Claude |
| **Gemini** | Mathematical literature & alternative proof techniques | Antigravity / Gemini CLI (when available) / Gemini |
| **Nova** | AI-driven mathematical discovery & pattern recognition | Muse |
| **Dee (DeepSeek)** | Computational optimization & counterexample generation | DeepSeek |
| **Lumi** | Research coordination, independent verification & integration | Orchestrator / Coordinator |

## Six-Phase Roadmap

1. **Phase 1 — Foundation:** Study existing results, failed proofs, and established barriers (Relativization, Natural Proofs, Algebrization). See [`docs/phase1/`](docs/phase1/).
2. **Phase 2 — Laboratory:** Build a reproducible Python lab for NP-complete instance generation, solver benchmarking (PySAT + DPLL), and phase-transition experiments. See [`lab/`](lab/).
3. **Phase 3 — Discovery:** Develop original conjectures, bounds, reductions, and algorithmic hypotheses.
4. **Phase 4 — Adversarial Review:** Actively attempt to disprove each other's conjectures with counterexamples, complexity-leakage audits, and barrier checks.
5. **Phase 5 — Formal Verification:** Translate proved lemmas and results into machine-verifiable Lean 4 + Mathlib proofs. See [`lean/`](lean/).
6. **Phase 6 — Publication:** Package any independently verified, novel result for academic review.

Full roadmap details: [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Branching & Contribution Policy

- `main`: Protected baseline. **Never merge to `main` without Stephon's explicit approval.**
- `dev`: Active integration branch. All PRs target `dev`.
- Free resources only. Never commit tokens, keys, passwords, or secrets.
