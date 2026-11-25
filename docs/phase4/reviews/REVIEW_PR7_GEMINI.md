<!-- docs/phase4/reviews/REVIEW_PR7_GEMINI.md -->

# Phase 4 — Independent Adversarial Review of PR #7 (`lean/Millennium/Tseitin.lean`)

- **Reviewer:** Gemini — Galactic AI Team
- **Artifact Author:** Ace — Galactic AI Team
- **Coordinator:** Lumi
- **Research Director:** Stephon
- **Date:** 2026-11-25
- **Exact Commits Reviewed / Executed:**
  - Original PR #7 source inspected at `dev @ e55d5db` (original PR #7 base `3901e30`; earlier Phase 4 brief base `7fd74bd`)
  - Clean CI build, axiom audit, and adversarial test execution verified at `dev @ 1905067` (PR #17 merge + `lean.yml` test compilation)
- **Reviewed Artifacts:**
  - `lean/Millennium/Tseitin.lean`
  - `lean/Millennium/Sat.lean`
  - `lean/Millennium.lean`
  - `lean/lakefile.toml`
  - `lean/lean-toolchain` (`leanprover/lean4:v4.24.0`)
  - `docs/phase3/TSEITIN_PROOF_SPEC.md`
- **Independent Test Artifact Executed in CI:** `lean/Millennium/Tests/TseitinAdversarial.lean`
- **Overall Disposition:** **`PASS` (with documented scoped limitations and two non-blocking LOW follow-up notes)**
  - **Gate A (Gemini independently reviews Ace's PR #7):** **COMPLETE (`PASS`)**
  - **Gate C (Lean / PR #7 half):** **PASS** (clean build passed, actual `#print axioms` retained, zero `sorry`/`sorryAx`/custom axioms, concrete `K4` odd & even instantiations succeeded, componentwise parity limitation documented).
  - **Gate C (Literature half — T12 and T1–T19 scope audit):** **REMAINS OPEN** pending independent re-review and approval of repaired `docs/phase3/WIDTH_TSEITIN_LITERATURE.md`.

---

## 1. Execution & Verification Summary (`dev @ 1905067`)

All previously blocked execution checks from the initial static review have been executed by Lumi/CI at the pinned toolchain (`leanprover/lean4:v4.24.0`, Mathlib `v4.24.0`) and inspected by Gemini:

1. **Inspection of `lean/Millennium/Sat.lean`:** Complete. `Literal.pos v` evaluates to `σ v`, `Literal.neg v` evaluates to `!(σ v)`, `evalClause` and `evalCNF` use direct structural recursion (`[] => false` for clause, `[] => true` for CNF), and zero `sorry`, `admit`, `axiom`, `opaque`, `unsafe`, or `native_decide` appear anywhere in `Sat.lean`.
2. **Clean Lean Build (`lake build`):** Passed (`Build completed successfully (7354 jobs).`).
3. **Adversarial Test Suite Compilation (`lake env lean Millennium/Tests/TseitinAdversarial.lean`):** Passed with zero errors. All 6 audited test theorems and all auxiliary lemmas compiled cleanly.
4. **Sorry / Axiom Guard Checks:** `! grep -rn "sorry" Millennium/` and `! grep -n "sorryAx" ../lean-build.log` both passed. Every audited theorem depends only on a subset of the three permitted standard Lean axioms `{propext, Classical.choice, Quot.sound}` (with `xor3CNF_correct`, `xor3CNF_dimacs_true`, and `xor3CNF_dimacs_false` using zero axioms), and zero `Lean.ofReduceBool` or custom axioms appear.
5. **Cross-Language Python Fixture Check (`om_lab.hard_instances._xor3_clauses`):** Executed by Lumi against the installed repository package; printed `PASS: Both fixtures and all 16 truth-table cases matched om_lab.hard_instances._xor3_clauses`.

---

## 2. Retained Raw Axiom Audit Outputs (Gate C Evidence)

### 2.1 Clean CI Build Output (`Millennium/Tseitin.lean` — `lake_build_axioms.txt`)

```text
info: Millennium/Tseitin.lean:504:0: 'Millennium.sum_vertexParity_eq_zero' depends on axioms: [propext, Classical.choice, Quot.sound]
info: Millennium/Tseitin.lean:505:0: 'Millennium.odd_charge_unsat' depends on axioms: [propext, Classical.choice, Quot.sound]
info: Millennium/Tseitin.lean:506:0: 'Millennium.vertexParity_eq_triple' depends on axioms: [propext, Classical.choice, Quot.sound]
info: Millennium/Tseitin.lean:507:0: 'Millennium.xor3Parity_bitValue' depends on axioms: [propext, Classical.choice, Quot.sound]
info: Millennium/Tseitin.lean:508:0: 'Millennium.xor3Parity_check_iff' depends on axioms: [propext, Classical.choice, Quot.sound]
info: Millennium/Tseitin.lean:509:0: 'Millennium.xor3CNF_correct' does not depend on any axioms
info: Millennium/Tseitin.lean:510:0: 'Millennium.xor3CNF_correct_mod2' depends on axioms: [propext, Classical.choice, Quot.sound]
info: Millennium/Tseitin.lean:511:0: 'Millennium.evalCNF_append' depends on axioms: [propext]
info: Millennium/Tseitin.lean:512:0: 'Millennium.eval_tseitinCNF_local' depends on axioms: [propext]
info: Millennium/Tseitin.lean:513:0: 'Millennium.tseitinCNF_odd_unsat' depends on axioms: [propext, Classical.choice, Quot.sound]
info: Millennium/Tseitin.lean:514:0: 'Millennium.xor3CNF_dimacs_true' does not depend on any axioms
info: Millennium/Tseitin.lean:515:0: 'Millennium.xor3CNF_dimacs_false' does not depend on any axioms
Build completed successfully (7354 jobs).
```

### 2.2 Independent Adversarial Test Output (`Millennium/Tests/TseitinAdversarial.lean` — `tests_compile_output.txt`)

```text
== lake env lean Millennium/Tests/TseitinAdversarial.lean
'Millennium.sum_vertexParity_eq_zero' depends on axioms: [propext, Classical.choice, Quot.sound]
'Millennium.odd_charge_unsat' depends on axioms: [propext, Classical.choice, Quot.sound]
'Millennium.vertexParity_eq_triple' depends on axioms: [propext, Classical.choice, Quot.sound]
'Millennium.xor3Parity_bitValue' depends on axioms: [propext, Classical.choice, Quot.sound]
'Millennium.xor3Parity_check_iff' depends on axioms: [propext, Classical.choice, Quot.sound]
'Millennium.xor3CNF_correct' does not depend on any axioms
'Millennium.xor3CNF_correct_mod2' depends on axioms: [propext, Classical.choice, Quot.sound]
'Millennium.evalCNF_append' depends on axioms: [propext]
'Millennium.eval_tseitinCNF_local' depends on axioms: [propext]
'Millennium.tseitinCNF_odd_unsat' depends on axioms: [propext, Classical.choice, Quot.sound]
'Millennium.xor3CNF_dimacs_true' does not depend on any axioms
'Millennium.xor3CNF_dimacs_false' does not depend on any axioms
'Millennium.Tests.TseitinAdversarial.k4_odd_tseitin_unsat' depends on axioms: [propext, Classical.choice, Quot.sound]
'Millennium.Tests.TseitinAdversarial.k4_even_tseitin_sat' depends on axioms: [propext, Classical.choice, Quot.sound]
'Millennium.Tests.TseitinAdversarial.k4_even_tseitin_sat_witness2' depends on axioms: [propext,
 Classical.choice,
 Quot.sound]
'Millennium.Tests.TseitinAdversarial.k4_even_noninjective_idx_unsat' depends on axioms: [propext, Quot.sound]
'Millennium.Tests.TseitinAdversarial.selfLoop_odd_tseitin_unsat' depends on axioms: [propext,
 Classical.choice,
 Quot.sound]
'Millennium.Tests.TseitinAdversarial.disconnected_even_global_unsat' depends on axioms: [propext,
 Classical.choice,
 Quot.sound]
```

*(Precision note: `selfLoop_vertex0_tautologies` and `fixture_zero_index_collision` also compiled cleanly inside `TseitinAdversarial.lean`, though no separate `#print axioms` command was emitted for those two `decide` lemmas; their claim levels below reflect that exact distinction.)*

---

## 3. Updated Finding Disposition & Claim-Level Upgrade Ledger

| ID | Axis / Target | Severity | Prior Claim Level -> Updated Claim Level | Prior -> Updated Disposition | Resolution / Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GEMINI-R7-01` | Clean build, `#print axioms`, & `Sat.lean` inspection | **HIGH** | `Empirical Observation` -> **`Lean-Verified`** (theorems) / **`Empirical Observation`** (CI log) | `OPEN` -> **`PASS`** | Closed at `dev @ 1905067`. `Sat.lean` inspected; `lake build` passed (7354 jobs); all 12 PR #7 theorems + 6 test theorems audited with permitted axioms only and zero `sorryAx`. |
| `GEMINI-R7-02` | Repeated / non-injective variable IDs (`idx`) | **MEDIUM** | `Proved` -> **`Lean-Verified`** (scoped limitation) | `OPEN` -> **`PASS`** (Scoped Limitation) | Witness `k4_even_noninjective_idx_unsat` compiled and audited (`[propext, Quot.sound]`). Sound for one-way UNSAT; injectivity and positivity remain mandatory for future SAT / generator-equivalence theorems (documented in spec Sec. 10 & `Tseitin.lean`). |
| `GEMINI-R7-03` | Self-loops & duplicate/tautological clauses in `xor3CNF` | **LOW** | `Proved` -> **`Lean-Verified`** (`selfLoop_odd_tseitin_unsat`) / **`Proved` + `Empirical Observation`** (`selfLoop_vertex0_tautologies`) | `OPEN` -> **`PASS`** (Scoped Limitation) | `selfLoop_odd_tseitin_unsat` audited (`[propext, Classical.choice, Quot.sound]`); `selfLoop_vertex0_tautologies` compiled cleanly (`decide`, no `#print axioms` line). Soundness unaffected; DIMACS simplification scope noted. |
| `GEMINI-R7-04` | Global vs. componentwise charge docstring in `.lean` | **LOW** | `Proved` -> **`Lean-Verified`** (`disconnected_even_global_unsat`) | **`OPEN`** (Non-blocking hygiene) | Witness `disconnected_even_global_unsat` audited (`[propext, Classical.choice, Quot.sound]`). Gate C componentwise documentation requirement is satisfied via `TSEITIN_PROOF_SPEC.md` Sec. 4 & 12; adding a 2-line docstring note directly in `Tseitin.lean` remains an optional non-blocking cleanup. |
| `GEMINI-R7-05` | Variable index `0` polarity collision in `tseitinFixtureLiteral` | **LOW** | `Proved` -> **`Proved` + `Empirical Observation`** | `OPEN` -> **`PASS`** (Scoped Limitation) | `fixture_zero_index_collision` compiled cleanly in CI (no `#print axioms` line, so not promoted to `Lean-Verified`). Limitation already explicitly documented in `Tseitin.lean` docstring. |
| `GEMINI-R7-06` | `#print axioms` in library module & broad `import Mathlib` | **LOW** | `Empirical Observation` (unchanged) | **`OPEN`** (Non-blocking hygiene) | Confirmed in `lake_build_axioms.txt` (lines 504–515 emit 12 info messages on import). Non-blocking for mathematical integrity or Gate C. |
| `GEMINI-R7-07` | Full 8-axis soundness of all 12 exported PR #7 theorems | **INFO** | `Proved` -> **`Lean-Verified`** | `PASS` (Static) -> **`PASS` (`Lean-Verified`)** | All 12 exported theorems in `Millennium.Tseitin` + `Sat.lean` semantics verified by Lean 4.24.0 kernel with permitted standard axioms only and concrete `K4` odd & even instantiations (`k4_odd_tseitin_unsat`, `k4_even_tseitin_sat`, `k4_even_tseitin_sat_witness2`). |
| `GEMINI-R7-08` | Python `_xor3_clauses` fixture parity against repo package | **INFO** | `Empirical Observation` (unchanged) | `OPEN` -> **`PASS`** | Executed by Lumi against `om_lab.hard_instances._xor3_clauses`: both clause lists and all 16 truth-table cases passed. |

---

## 4. Finalized 8-Axis Audit Summary

1. **Exact `Nat` incidence multiplicities (`TripleIncidenceMatches`):** **`PASS` (`Lean-Verified`)** — `vertexParity_eq_triple` and `k4_incidence_matches` kernel-checked; `Nat` equality prevents mod-2 cancellation and enforces degree 3 (counting self-loops as 2).
2. **Vertex-list coverage (`hCover`):** **`PASS` (`Lean-Verified`)** — `hCover` prevents vacuous empty-list UNSAT; duplicate vertices preserve one-way UNSAT soundness (`vertices.Nodup` required only for future clause-count/generator equivalence).
3. **Finite endpoint maps (`u, v : E -> V`):** **`PASS` (`Lean-Verified`)** — total functions eliminate dangling half-edges and enforce `sum_vertexParity_eq_zero` over `ZMod 2`.
4. **Self-loops and parallel edges:** **`PASS` (`Lean-Verified` soundness; scoped limitation `GEMINI-R7-03`)** — parallel edges are separated by `E`; self-loops satisfy `TripleIncidenceMatches` and `tseitinCNF_odd_unsat` (`selfLoop_odd_tseitin_unsat`), while `xor3CNF` emits duplicate literals and tautological clauses for repeated variables.
5. **Repeated variable IDs (`idx`):** **`PASS` (`Lean-Verified` scoped limitation `GEMINI-R7-02`)** — non-injective `idx` preserves one-way UNSAT soundness, but turns satisfiable even-charge $K_4$ into an unsatisfiable CNF (`k4_even_noninjective_idx_unsat`); injectivity and positivity remain required for faithful DIMACS/SAT correspondence.
6. **Empty types (`V`, `E`, `vertices`):** **`PASS` (`Proved` / `Lean-Verified`)** — empty `V` makes `hOdd` false (vacuously consistent with satisfiable empty CNF); empty `E` with nonempty odd `V` works non-vacuously in `odd_charge_unsat` and has no 3-regular triple map `a : V -> Empty`; empty `vertices` fails `hCover` for nonempty `V`.
7. **Global vs. componentwise charge:** **`PASS` for Gate C (`Lean-Verified` witness `disconnected_even_global_unsat`; minor `.lean` docstring note `GEMINI-R7-04` left `OPEN`)** — global odd charge is sufficient but not necessary on disconnected graphs; accurately scoped in `TSEITIN_PROOF_SPEC.md` Sec. 4 & 12.
8. **Boolean-to-`ZMod 2` correspondence & `Sat.lean` semantics:** **`PASS` (`Lean-Verified` + Python `Empirical Observation`)** — `Sat.lean` polarity verified directly; `xor3CNF_correct`, `xor3CNF_dimacs_true`, and `xor3CNF_dimacs_false` hold with zero axioms; `k4_even_tseitin_sat` and `k4_even_tseitin_sat_witness2` confirm both `rhs = true` and `rhs = false` clauses on a concrete $K_4$ graph; Python `_xor3_clauses` matches on all 16 truth-table cases.

---

## 5. Gate A–C Status After CI Execution (`dev @ 1905067`)

### Gate A: Independent review coverage
- `[x]` **Gemini independently reviews Ace's PR #7:** **COMPLETE (`PASS`)**. Exact commits recorded (`e55d5db` source; `1905067` CI build & adversarial tests).

### Gate B: Finding disposition
- `[x]` Every finding has a unique ID (`GEMINI-R7-01` through `GEMINI-R7-08`), documented severity, claim level, and disposition.
- `[x]` Zero unresolved HIGH or MEDIUM blockers.
- `[x]` All accepted limitations (`GEMINI-R7-02`, `GEMINI-R7-03`, `GEMINI-R7-05`) and negative/edge-case results (`k4_even_noninjective_idx_unsat`, `disconnected_even_global_unsat`) are explicitly scoped and retained in `lean/Millennium/Tests/TseitinAdversarial.lean`.
- `[x]` No author approved their own work.

### Gate C: Mathematical integrity
- `[x]` **Lean clean build passes:** `lake build` succeeded (7354 jobs, Lean 4.24.0 / Mathlib v4.24.0) and `lake env lean Millennium/Tests/TseitinAdversarial.lean` passed in CI.
- `[x]` **Actual axiom outputs are retained:** Recorded verbatim in Section 2 above.
- `[x]` **No admitted proofs or custom axioms:** Verified via CI grep checks and `#print axioms` (only subsets of `{propext, Classical.choice, Quot.sound}`).
- `[x]` **Concrete graph instantiation succeeds:** `k4_odd_tseitin_unsat`, `k4_even_tseitin_sat`, and `k4_even_tseitin_sat_witness2` all compiled and passed axiom audit.
- `[x]` **Componentwise parity limitation is documented:** Documented in `docs/phase3/TSEITIN_PROOF_SPEC.md` Sections 4 & 12 and formally witnessed by `disconnected_even_global_unsat`.
- `[ ]` **T12 is corrected & Literature-table theorem scope audit is complete:** Repaired `docs/phase3/WIDTH_TSEITIN_LITERATURE.md` submitted separately; remains **`OPEN`** until Ace (or another independent reviewer) approves the repair.

### Authorized Claim Promotion for PR #7 (`Millennium.Tseitin`)
All 12 exported theorems in `lean/Millennium/Tseitin.lean` now satisfy `docs/RULES.md` and `TSEITIN_PROOF_SPEC.md` Section 14 acceptance gates and are eligible for **`Lean-Verified`** status within their stated mathematical scope (classical finite parity inconsistency and 3-XOR CNF semantics; no proof-complexity lower bound or $\mathrm{P} \neq \mathrm{NP}$ claim).