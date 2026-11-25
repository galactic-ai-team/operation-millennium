<!-- docs/phase4/reviews/REVIEW_PR7_GEMINI.md -->

# Phase 4 — Independent Adversarial Review of PR #7 (`lean/Millennium/Tseitin.lean`)

- **Reviewer:** Gemini — Galactic AI Team
- **Artifact Author:** Ace — Galactic AI Team
- **Coordinator:** Lumi
- **Research Director:** Stephon
- **Date:** 2026-11-25
- **Exact Commit Attacked:** `dev @ e55d5db` (attached files from PR #7; original PR #7 base recorded as `3901e30`; earlier Phase 4 brief base `7fd74bd`)
- **Reviewed Artifacts:**
  - `lean/Millennium/Tseitin.lean`
  - `lean/Millennium.lean`
  - `lean/lakefile.toml`
  - `lean/lean-toolchain` (`leanprover/lean4:v4.24.0`)
  - `docs/phase3/TSEITIN_PROOF_SPEC.md`
- **Uninspected Dependency:** `lean/Millennium/Sat.lean` (not attached in review bundle)
- **Independent Test Artifact Delivered:** `lean/Millennium/Tests/TseitinAdversarial.lean`
- **Execution Status:** **NOT RUN** (no Lean 4 / `lake` toolchain or repo Python environment available in reviewer's sandbox)
- **Overall Disposition:** **`OPEN`** (Static mathematical audit: **PASS with scoped limitations**; Gate C Lean build & axiom audit: **NOT RUN — BLOCKING** until executed and retained by Lumi/CI)

---

## 1. Honesty & Execution Disclosure

The following acceptance checks from `ADVERSARIAL_REVIEW_01.md` Section 6.2 and Section 10 Gate C were **NOT RUN** by Gemini and remain **`OPEN`** until Lumi executes them on a Lean 4.24.0 box and returns the raw output:

1. `lake clean && lake build` at pinned toolchain `leanprover/lean4:v4.24.0` / Mathlib `v4.24.0` — **NOT RUN**.
2. Actual `#print axioms` output capture for all 12 exported theorems in `Millennium.Tseitin` — **NOT RUN**.
3. Static inspection and axiom audit of `lean/Millennium/Sat.lean` — **NOT RUN** (file not attached).
4. Compilation of `lean/Millennium/Tests/TseitinAdversarial.lean` (`K4` odd-charge, `K4` even-charge satisfiable witnesses, and adversarial fixtures) — **NOT RUN**.
5. Execution of the `TSEITIN_PROOF_SPEC.md` Section 11 Python fixture script against `om_lab.hard_instances._xor3_clauses` — **NOT RUN**.

Per `docs/RULES.md`, **no `Lean-Verified` claim is granted by this static review**.

---

## 2. Finding Disposition Ledger

| ID | Axis / Target | Severity | Claim Level | Disposition | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GEMINI-R7-01` | Clean build, `#print axioms`, & uninspected `Sat.lean` | **HIGH (Gate C Blocker)** | `Empirical Observation` | `OPEN` | **NOT RUN** — awaiting Lumi execution output & `Sat.lean` |
| `GEMINI-R7-02` | Repeated / non-injective variable IDs (`idx : E → Nat`) | **MEDIUM** | `Proved` | `OPEN` (Scoped Limitation) | Sound for one-way UNSAT; breaks SAT fidelity on even-charge graphs (witnessed in `k4_even_noninjective_idx_unsat`, **NOT RUN**) |
| `GEMINI-R7-03` | Self-loops & strict 3-regularity in `TripleIncidenceMatches` / `xor3CNF` | **LOW** | `Proved` | `OPEN` (Scoped Limitation) | Sound semantically; emits duplicate literals & tautological clauses for self-loops (witnessed in `selfLoop_vertex0_tautologies`, **NOT RUN**) |
| `GEMINI-R7-04` | Global vs. componentwise charge documentation in `.lean` docstrings | **LOW** | `Proved` | `OPEN` | Documented in spec Sec. 4, omitted in `Tseitin.lean` docstrings; disconnected even-global UNSAT witnessed in `disconnected_even_global_unsat` (**NOT RUN**) |
| `GEMINI-R7-05` | Variable index `0` collision in `tseitinFixtureLiteral` | **LOW** | `Proved` | `OPEN` (Scoped Limitation) | Both `Literal.pos 0` and `Literal.neg 0` map to `0 : Int` (acknowledged in docstring; witnessed in `fixture_zero_index_collision`, **NOT RUN**) |
| `GEMINI-R7-06` | `#print axioms` in library module & broad `import Mathlib` | **LOW** | `Empirical Observation` | `OPEN` | Emits 12 axiom diagnostics on every downstream import; minor hygiene/build-time note |
| `GEMINI-R7-07` | Static soundness across all 8 Section 6.2 axes (`Tseitin.lean`) | **INFO** | `Proved` | `PASS` (Static only) | Zero `sorry`/`admit`/`axiom`/`native_decide`; no vacuous hypotheses found statically |
| `GEMINI-R7-08` | Python `_xor3_clauses` fixture parity against repo package | **INFO** | `Empirical Observation` | `OPEN` | **NOT RUN** — command supplied for Lumi |

---

## 3. Static Audit Across All 8 Required Axes

### Axis 1: Exact `Nat` Incidence Multiplicities (`TripleIncidenceMatches`) — `PASS` (Static) `[Proved]`
* **Inspection:** `TripleIncidenceMatches` asserts for all `w : V` and `e : E`:
  $$(1\text{ if }w = u(e)\text{ else }0) + (1\text{ if }w = v(e)\text{ else }0) = (1\text{ if }e = a(w)) + (1\text{ if }e = b(w)) + (1\text{ if }e = c(w))$$
  in `Nat`, not `ZMod 2`.
* **Mathematical check:**
  - Evaluating in `Nat` blocks mod-2 cancellation (multiplicity `0` cannot masquerade as multiplicity `2`).
  - Summing both sides over `e : E` forces every vertex $w \in V$ to have degree **exactly $3$** (counting self-loops with multiplicity $2$), and summing over all $(w, e)$ forces $2|E| = 3|V|$, hence $|V|$ is even `[Proved]`.
  - `vertexParity_eq_triple` maps this `Nat` equality into `ZMod 2` via `Nat.cast_add`, `add_mul`, and `count_weight`, then sums over `e : E` using `sum_at`. The derivation is mathematically sound `[Proved]` (Lean elaboration **NOT RUN**).

### Axis 2: Vertex-List Coverage (`hCover`) — `PASS` (Static, with structural note) `[Proved]`
* **Inspection:** `tseitinCNF_odd_unsat` requires `hCover : ∀ w : V, w ∈ vertices`.
* **Mathematical check:**
  - Dropping `hCover` would allow `vertices = []` (producing the trivially satisfiable empty CNF `[]`), which `hCover` properly blocks for every nonempty `V` `[Proved]`.
  - Duplicate vertices in `vertices` are allowed (`vertices.Nodup` is not assumed). Because `eval_tseitinCNF_local` only extracts local satisfaction for every `w ∈ vertices`, repeating a vertex's 4-clause block preserves one-way unsatisfiability `[Proved]`.
  - *Scoped note:* Without `vertices.Nodup`, `tseitinCNF` can emit more than $4|V|$ clauses; any future structural-equivalence theorem against `generate_tseitin_3sat` must add `vertices.Nodup`.

### Axis 3: Finite Endpoint Maps (`u v : E → V`) — `PASS` (Static) `[Proved]`
* **Inspection:** `u, v : E → V` are total functions into `[Fintype V]` from `[Fintype E]`.
* **Mathematical check:**
  - Totality eliminates "dangling half-edges" outside `V`, guaranteeing that every edge `e : E` contributes `x e + x e = 2 * x e = 0` in `ZMod 2` when summed over `w : V` in `sum_vertexParity_eq_zero` `[Proved]`.
  - Both `vertexParity` and `TripleIncidenceMatches` are symmetric under swapping `u e` and `v e`, so edge orientation is mathematically irrelevant `[Proved]`.

### Axis 4: Self-Loops and Parallel Edges — `PASS` for Soundness / `GEMINI-R7-03` (LOW) `[Proved]`
* **Self-loops (`u e = v e = w`):**
  - In `vertexParity`, a self-loop contributes `x e + x e = 0` in `ZMod 2`.
  - In `TripleIncidenceMatches`, a self-loop contributes `2 : Nat` on the LHS, forcing `e` to appear **twice** in `(a w, b w, c w)` alongside one ordinary edge `e'`.
  - In `xor3CNF (idx e) (idx e) (idx e') rhs`, `xor3Parity (σ i) (σ i) (σ j) = σ j`, so `xor3CNF_correct` remains semantically exact `[Proved]`.
  - **Finding `GEMINI-R7-03`:** For a self-loop `(i, i, j)` with `rhs = true`, `xor3CNF` emits `[[i, i, j], [i, -i, -j], [-i, i, -j], [-i, -i, j]]` — containing duplicate literals and two tautological clauses. This does **not** break soundness of `tseitinCNF_odd_unsat`, but diverges from simplified/strict DIMACS CNF conventions. Witnessed in `selfLoop_odd_tseitin_unsat` and `selfLoop_vertex0_tautologies` (**NOT RUN**).
* **Parallel edges (`e1 ≠ e2` with identical endpoints):**
  - Because `E` is an abstract finite type rather than unordered vertex pairs, parallel edges retain distinct identities in `Finset.univ : Finset E`, `TripleIncidenceMatches`, and `idx`. Fully sound `[Proved]`.

### Axis 5: Repeated Variable IDs (`idx : E → Nat`) — `GEMINI-R7-02` (MEDIUM, Scoped Limitation) `[Proved]`
* **Inspection:** `tseitinCNF_odd_unsat` imposes neither `Function.Injective idx` nor `∀ e, 0 < idx e`.
* **Mathematical check:**
  - **Soundness for UNSAT holds (`Proved`):** Any satisfying assignment `σ : Assignment` induces an edge assignment `x e := bitValue (σ (idx e))` that satisfies all vertex parities even when `idx` collapses distinct edges; `odd_charge_unsat` rules out *every* `x : E → ZMod 2`, so `tseitinCNF_odd_unsat` is not vacuous or unsound.
  - **Finding `GEMINI-R7-02` (Semantic fidelity break on SAT instances, `Proved`):** When `idx` is non-injective, an **even-charge connected 3-regular graph** (mathematically satisfiable as a Tseitin parity system) can become **UNSAT** as a CNF. Specifically, on $K_4$ with even charge `(true, true, false, false)` and `idx := fun _ => 1`, vertex `0` forces `σ 1 = true` while vertex `2` forces `σ 1 = false` — contradiction!
  - Ace explicitly documented this scope limit in `Tseitin.lean` comments and `TSEITIN_PROOF_SPEC.md` Section 10. It is acceptable as a documented limitation of the one-way UNSAT theorem, **provided** `Function.Injective idx` and `∀ e, 0 < idx e` are mandatory hypotheses in any future satisfiability or generator-correspondence theorem. Witnessed in `k4_even_noninjective_idx_unsat` (**NOT RUN**).

### Axis 6: Empty Types (`V = Empty`, `E = Empty`, `vertices = []`) — `PASS` (Static) `[Proved]`
* `V = Empty`, `E = Empty`: `∑ w : Empty, bitValue (charge w) = 0 ≠ 1`, so `hOdd` is false and both UNSAT theorems hold vacuously (matching the fact that the empty graph has even charge 0 and empty CNF is satisfiable) `[Proved]`.
* `V = Empty`, `E` nonempty: no function `u : E → Empty` exists (vacuously safe) `[Proved]`.
* `V` nonempty, `E = Empty`:
  - In `odd_charge_unsat` (Part A), `u, v : Empty → V` exist trivially (`Empty.elim`); for `V = Fin 1, charge _ = 1`, `hOdd` holds and `odd_charge_unsat` **non-vacuously** proves unsatisfiability of an isolated odd-charged vertex `[Proved]`.
  - In `tseitinCNF_odd_unsat` (Part E), no `a : V → Empty` exists (consistent with 3-regularity) `[Proved]`.
* `vertices = []`: for nonempty `V`, `hCover` is false, blocking vacuous unsatisfiability of `[]` `[Proved]`.

### Axis 7: Global vs. Componentwise Charge — `GEMINI-R7-04` (LOW) `[Proved]`
* **Inspection:** Both `odd_charge_unsat` and `tseitinCNF_odd_unsat` prove the one-way implication `(∑ w : V, charge w = 1) → UNSAT`, without claiming an `iff` or requiring connectedness.
* **Mathematical check:** Global odd charge is **sufficient** for UNSAT (by pigeonhole, at least one connected component has odd charge), but **not necessary** on disconnected graphs: $K_4 \sqcup K_4$ with one odd vertex per component has total charge $1 + 1 = 0 \pmod 2$ yet is UNSAT `[Proved]`.
* **Finding `GEMINI-R7-04`:** Ace properly documented this in `TSEITIN_PROOF_SPEC.md` Section 4 & Section 12, satisfying the spec side of Gate C, **but the Lean docstrings on `odd_charge_unsat` and `tseitinCNF_odd_unsat` inside `lean/Millennium/Tseitin.lean` omit this componentwise scope caveat**. Recommend adding a 2-line scope note directly to those Lean docstrings so readers of the Lean file cannot misread it as a complete characterization. Witnessed in `disconnected_even_global_unsat` (**NOT RUN**).

### Axis 8: Boolean-to-`ZMod 2` Correspondence & Fixture Alignment — `PASS` (Static) / `GEMINI-R7-05` (LOW) `[Proved]`
* **Truth-table check:**
  - `bitValue false = 0`, `bitValue true = 1`.
  - `xor3Parity p q r = (p != q) != r` matches `bitValue p + bitValue q + bitValue r` across all 8 triples `[Proved]`.
  - `xor3CNF a b c true` forbids `(F,F,F), (F,T,T), (T,F,T), (T,T,F)` (even parity); `xor3CNF a b c false` forbids `(T,T,T), (T,F,F), (F,T,F), (F,F,T)` (odd parity). Exact match with all 16 combinations `[Proved]`.
  - Because arity 3 is odd, an accidental `pos`/`neg` polarity flip in `Sat.lean`'s `evalLiteral` would negate `xor3Parity` and cause `xor3CNF_correct` to fail compilation `[Proved]`. Nevertheless, `Sat.lean` itself must be inspected and compiled (`GEMINI-R7-01`).
* **Finding `GEMINI-R7-05`:** `tseitinFixtureLiteral` maps both `Literal.pos 0` and `Literal.neg 0` to `0 : Int` (the DIMACS clause terminator). Already noted in `Tseitin.lean`'s docstring; witnessed in `fixture_zero_index_collision` (**NOT RUN**).
* **Static elaboration note (unexecuted):** `xor3CNF_correct` uses `simp only [xor3CNF, evalCNF, evalClause, evalLiteral, ha, hb, hc] <;> rfl`. This compiles cleanly if `evalCNF` and `evalClause` in `Sat.lean` unfold via structural recursion equations (as implied by `evalCNF_append`); if they wrap `List.all`/`List.any` without exposing reductions to `simp only`, `lake build` will catch it immediately.

---

## 4. Detailed Finding Records & Reproduction Steps

### `GEMINI-R7-01` — Unexecuted Lean Build, Axiom Audit, and Uninspected `Sat.lean`
* **Severity:** HIGH (Gate C Blocker)
* **Claim Level:** `Empirical Observation`
* **Disposition:** `OPEN`
* **Details:** No Lean 4.24.0 / `lake` build was executed by Ace (per spec Section 16) or by Gemini (no Lean toolchain in review environment), and `lean/Millennium/Sat.lean` was not attached.
* **Required Closure:** Lumi runs `lake clean && lake build`, `lake build Millennium.Tests.TseitinAdversarial`, and attaches `lean/Millennium/Sat.lean` plus raw `#print axioms` output confirming only `{propext, Classical.choice, Quot.sound}` (or subsets thereof) and zero `sorryAx` / `Lean.ofReduceBool`.

### `GEMINI-R7-02` — Non-Injective `idx` Destroys Satisfiability Fidelity on Even-Charge Connected Graphs
* **Severity:** MEDIUM
* **Claim Level:** `Proved`
* **Disposition:** `OPEN` (Acceptable as scoped limitation for UNSAT-only theorem once `k4_even_noninjective_idx_unsat` compiles; must not be dropped in future SAT/adapter theorems)
* **Reproduction:** Compile `Millennium.Tests.TseitinAdversarial.k4_even_noninjective_idx_unsat` via `cd lean && lake build Millennium.Tests.TseitinAdversarial` (**NOT RUN**).

### `GEMINI-R7-03` — Self-Loop Vertices Produce Duplicate Literals and Tautological Clauses in `xor3CNF`
* **Severity:** LOW
* **Claim Level:** `Proved`
* **Disposition:** `OPEN` (Scoped limitation; document alongside self-loop claim in `TripleIncidenceMatches`)
* **Reproduction:** Compile `Millennium.Tests.TseitinAdversarial.selfLoop_odd_tseitin_unsat` and `selfLoop_vertex0_tautologies` (**NOT RUN**).

### `GEMINI-R7-04` — Componentwise Parity Scope Warning Missing from Lean Source Docstrings
* **Severity:** LOW
* **Claim Level:** `Proved`
* **Disposition:** `OPEN`
* **Reproduction:** Inspect docstrings of `odd_charge_unsat` and `tseitinCNF_odd_unsat` in `lean/Millennium/Tseitin.lean`, and compile `Millennium.Tests.TseitinAdversarial.disconnected_even_global_unsat` (**NOT RUN**).

### `GEMINI-R7-05` — Zero-Index Polarity Collision in `tseitinFixtureLiteral`
* **Severity:** LOW
* **Claim Level:** `Proved`
* **Disposition:** `OPEN` (Scoped limitation already noted in docstring)
* **Reproduction:** Compile `Millennium.Tests.TseitinAdversarial.fixture_zero_index_collision` (**NOT RUN**).

### `GEMINI-R7-06` — `#print axioms` Inside Library Module & Broad `import Mathlib`
* **Severity:** LOW
* **Claim Level:** `Empirical Observation`
* **Disposition:** `OPEN`
* **Details:** Lines 360–371 of `lean/Millennium/Tseitin.lean` run 12 `#print axioms` commands inside the library module itself, printing diagnostics on every import, and line 25 uses full `import Mathlib`. Non-blocking for mathematical validity; consider moving `#print axioms` to a dedicated audit module after Gate C closes.

### `GEMINI-R7-07` — Static Audit of Proof Terms and Absence of Forbidden Primitives
* **Severity:** INFO
* **Claim Level:** `Proved` (for mathematical arguments) / `Empirical Observation` (for source inspection)
* **Disposition:** `PASS` (Static only)
* **Details:** Source inspection of `lean/Millennium/Tseitin.lean` confirms zero occurrences of `sorry`, `admit`, `axiom`, `opaque`, `unsafe`, or `native_decide`. All 12 exported theorems follow standard mathematical derivations consistent with `TSEITIN_PROOF_SPEC.md`.

### `GEMINI-R7-08` — Cross-Language Python `_xor3_clauses` Fixture Verification
* **Severity:** INFO
* **Claim Level:** `Empirical Observation`
* **Disposition:** `OPEN` (**NOT RUN**)
* **Reproduction:** Run the Section 11 Python snippet against installed `om_lab.hard_instances._xor3_clauses`.

---

## 5. Gate A–C Impact Summary

* **Gate A (Gemini independently reviews Ace's PR #7):** Static audit complete; final sign-off **OPEN** pending inspection of `Sat.lean` and execution outputs.
* **Gate B (Unique IDs, severities, dispositions, negative/scoped results retained):** Complete for this review (`GEMINI-R7-01`–`08`).
* **Gate C (Lean clean build, actual axiom outputs retained, no custom axioms/admitted proofs, concrete `K4` instantiation succeeds, componentwise parity limitation documented):** **NOT YET GRANTED** — blocked on `GEMINI-R7-01` (**NOT RUN**).

