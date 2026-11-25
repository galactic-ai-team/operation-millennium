# Operation Millennium Roadmap

Operation Millennium is organized into six sequential and overlapping phases. Every phase produces concrete, verifiable artifacts in the repository.

## Realistic Scope

Settling P vs NP is one of the hardest open problems in mathematics and computer science. Our goal is disciplined scientific hygiene:

- **Realistic outputs:** rigorous literature synthesis, reproducible computational tooling, small empirical findings on solver behavior and phase transitions, explicit counterexamples to flawed heuristics/proofs, and Lean-formalized known theorems.
- **Extraordinary claims:** require extraordinary, complete, machine-checked proof under [`docs/RULES.md`](RULES.md).

---

## Phase 1 — Foundation

**Objective:** Map the landscape of NP-completeness, known proof attempts, and established mathematical barriers so the team does not rediscover known dead ends.

- **Key Owners:** Gemini (literature & alternative techniques), Ace (complexity architecture & barriers), Lumi (integration)
- **Deliverables:**
  - Verified literature map (`docs/phase1/LITERATURE_MAP.md`)
  - Barrier checklist covering Relativization, Natural Proofs, and Algebrization (`docs/phase1/BARRIER_CHECKLIST.md`)
  - Survey notes on failed proof patterns (e.g., hidden exponential blowup in LP/SDP lifts, non-relativizing gaps, diagonalization traps)
- **Exit Criteria:** All core citations verified against primary sources; barrier checklist approved across lanes.

## Phase 2 — Laboratory

**Objective:** Build a clean, deterministic, reproducible Python laboratory for experimenting with NP-complete problems, exact solvers, and empirical hardness regimes.

- **Key Owners:** Claude (algorithms & solver harness), Dee (optimization & counterexamples), Nova (feature extraction & pattern discovery), Lumi (CI & verification)
- **Deliverables:**
  - Deterministic generators for Random 3-SAT, Graph $k$-Coloring (with SAT reduction), and Euclidean/Metric TSP (`lab/om_lab/generators.py`)
  - Solver harness comparing a pure-Python DPLL baseline against PySAT CDCL (`cd195` / CaDiCaL) with independent certificate checking (`lab/om_lab/solvers.py`, `lab/om_lab/harness.py`)
  - Random 3-SAT phase-transition experiment around clause/variable ratio $\alpha \approx 4.26$ with JSONL logs and plot output (`lab/om_lab/phase_transition.py`)
  - Automated `pytest` suite and GitHub Actions CI
- **Exit Criteria:** CI green on `dev`; solver witnesses verified; phase-transition experiment reproducible from seed.

## Phase 3 — Discovery

**Objective:** Formulate original, falsifiable conjectures, restricted-model lower bounds, parameterized/structural algorithms, or empirical phase-structure hypotheses.

- **Key Owners:** All lanes (Stephon directing hypotheses; Ace on complexity/proofs; Claude on algorithms; Gemini on cross-domain techniques; Nova on pattern discovery; Dee on optimization & stress cases)
- **Deliverables:**
  - Structured conjecture notes tagged `[Claim Level: Conjecture]` or `[Claim Level: Empirical Observation]`
  - Reproducible experiment scripts and negative-result logs
- **Exit Criteria:** Every conjecture states exact quantifiers, assumptions, and falsification tests.

## Phase 4 — Adversarial Review

**Objective:** Actively attempt to break every discovery, algorithm, or proof sketch produced in Phase 3.

- **Key Owners:** Dee (counterexample generation), Ace (barrier & proof-gap audit), Lumi (independent verification)
- **Deliverables:**
  - Adversarial review reports per conjecture/PR
  - Counterexample instances added to regression tests
  - Barrier audit (`docs/phase1/BARRIER_CHECKLIST.md`) passed before any proof claim advances
- **Exit Criteria:** No surviving unaddressed counterexamples or hidden barrier violations.

## Phase 5 — Formal Verification

**Objective:** Formalize proved definitions, reductions, and lemmas in Lean 4 + Mathlib so correctness is machine-checked without `sorry` or unverified axioms.

- **Key Owners:** Ace (formal specification), Claude & Gemini (proof engineering), Lumi (build verification)
- **Deliverables:**
  - Lean 4 + Mathlib workspace (`lean/`)
  - Warm-up formalizations (CNF semantics, certificate soundness, empty-clause unsatisfiability)
  - Formalized reductions and bounded theorems from Phase 3/4
- **Exit Criteria:** `lake build` succeeds with zero `sorry`s and standard Lean axioms only.

## Phase 6 — Publication

**Objective:** If—and only if—the team produces a novel, rigorously proved, independently verified result (such as a new restricted bound, structural theorem, or algorithmic advance), prepare a clear preprint/technical report for external academic review.

- **Key Owners:** Stephon (Director), Ace, Gemini, Lumi
- **Deliverables:** Technical paper, reproducibility artifact bundle, and formal Lean companion archive.
