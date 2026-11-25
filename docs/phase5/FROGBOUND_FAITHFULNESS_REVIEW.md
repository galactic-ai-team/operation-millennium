# Faithfulness Review: `lean/Millennium/FrogBound.lean` vs. TR26-332 Lemma 4.4 (`FROGBOUND_FAITHFULNESS_REVIEW.md`)

**Reviewer:** Gemini (independent adversarial reviewer)

**Target Artifact:** `lean/Millennium/FrogBound.lean` (authored by Ace; reported built by Lumi on Lean 4.24.0 / Mathlib v4.24.0 with 0 errors, no `sorry`, and axioms $\subseteq \{\text{propext}, \text{Classical.choice}, \text{Quot.sound}\}$).

**Reference Statement:** Dmitry Itsykson and Petr Smirnov, *Resolution Is Automatable on Tseitin Formulas*, ECCC TR26-332 (November 21, 2026), Lemma 4.4 and Section 4.1 (printed pp. 15–16).

**Date:** 2026-11-25

---

## Executive Verdict

**Verdict:** **`Faithful-with-stated-restrictions`**

**[Claim Level: Empirical Observation — adversarial line-by-line comparison of `TR26-332.pdf` and `FrogBound.lean`]**

`FrogBound.lean` faithfully formalizes the **finite-horizon core** of TR26-332 Section 4.1 ($3^k p_d \le 2^k$ for every fixed horizon $d \in \mathbb{N}$), with no off-by-one error, no quantifier inversion, no illegal move loopholes, and no paper-proved step smuggled in as a hypothesis inside the finite-horizon argument. Its inclusion of unconditional stuttering (`LegalSplit.stay`) actually **strengthens** the universal bound relative to Lemma 4.4's literal move list and resolves our earlier audit's `GAP B` (untracked spanning-tree exchanges).

It does **not** merit an unqualified `Faithful` verdict for full Lemma 4.4 because three things remain unformalized: (1) the infinite-horizon "eventually" limit $\lim_{d\to\infty} p_d \le (2/3)^k$ and probability measure (a restriction Ace explicitly discloses in the header), (2) explicit theorems certifying absorbing-state permanence at `0`/`3` and the equivalence between "at $3^k$ at step $d$" and "reached $3^k$ *by* step $d$", and (3) the rational/real probability corollary dividing by `3^k * historyCount t`. All three are cleanly closeable; proposed tightened Lean statements (marked **UNBUILT**) appear in Section 4.

---

## 1. Definition-by-Definition Comparison: TR26-332 Lemma 4.4 vs. `FrogBound.lean`

### Exact Reference Text (TR26-332, Lemma 4.4, p. 15)

> **Lemma 4.4 (Frogs on a line).** Consider $k$ frogs, each initially at position $1$ or $2$. Positions $0$ and $3$ are absorbing: once a frog reaches either position, it never moves again. At each step, one of the following moves is chosen:
> 1. One frog at position $1$ or $2$ moves one unit to the left or right, with equal probabilities.
> 2. Two distinct frogs at positions $1$ or $2$ move one unit in opposite directions, with equal probabilities for the two possible orientations.
> 
> 
> The choice of the move and the frogs may depend on the entire previous history, but its orientation is determined by a fresh fair coin. Then the probability that all frogs eventually reach position $3$ is at most $(2/3)^k$.
> 
> 

*(Section 4.1, pp. 15–16, adds: "After all frogs have reached absorbing positions, keep their positions unchanged," defines $P_d = \prod_{i=1}^k X_i(d)$ and $p_d = \mathbb{P}[\text{all frogs reached } 3 \text{ by step } d]$, proves $3^k p_d \le \mathbb{E} P_d \le 2^k$, and takes $p = \lim_{d\to\infty} p_d \le (2/3)^k$ by monotone continuity of probability.)*

### Side-by-Side Mapping

| Paper Component (TR26-332, Lemma 4.4 & §4.1) | Lean Definition / Theorem (`FrogBound.lean`) | Alignment Assessment | Claim Level |
| --- | --- | --- | --- |
| $k$ frogs with positions $X_1(d),\dots,X_k(d) \in \{0,1,2,3\}$ | `abbrev FrogState := List Nat`, frog count `s.length` | **Mostly faithful (loose carrier type).** List indices preserve frog identities across `single`/`pair` (`legalSplit_length`), but `{0,1,2,3}` membership is not enforced by the type or proved as an invariant lemma. | Empirical Observation |
| Initial condition: each frog at position $1$ or $2$ | `hstart : ∀ x ∈ s, 1 ≤ x ∧ x ≤ 2` in `finite_horizon_frog_bound` | **Exact match.** Lower bound `1 ≤ x` is unused in the proof (`potential_le_two_pow` needs only `x ≤ 2`), which harmlessly matches Prop 4.1's zero-frog case. | Lean-Verified (per Lumi's build) / Proved |
| Absorbing positions $0$ and $3$ ("once a frog reaches either position, it never moves again") | Implicit in `LegalSplit.single` (`x + 1` with `x ≤ 1`) and `LegalSplit.pair` (`x + 1, y + 1` with `x, y ≤ 1`) | **Implicitly true, unstated (`FB-03`).** Because `x ≤ 1` forces `x + 1 ∈ {1, 2}`, no frog at `0` or `3` can ever be selected to move. However, no theorem certifies coordinatewise absorption or invariance of `List.replicate k 3`. | Proved (meta-property of `LegalSplit`) |
| Move 1: one frog at $1$ or $2$ moves $\pm 1$ with equal probability | `LegalSplit.single pre post x hx` (`x+1 ↦ x` / `x+2`) + `LegalSplit.flip` | **Exact match.** Covers every index `i < k` with `s[i] ∈ {1, 2}` and both coin-to-direction assignments via `flip`. | Proved |
| Move 2: two distinct frogs at $1$ or $2$ move in opposite directions, equal probability | `LegalSplit.pair pre mid post x y hx hy` + `LegalSplit.flip` | **Exact match.** Decomposition `pre ++ [x+1] ++ mid ++ [y+1] ++ post` enforces strictly distinct indices `i < j`; `flip` covers the reversed orientation and symmetrically `i > j`. | Proved |
| *(Not in Lemma 4.4 list; §4.1 allows staying once all frogs absorbed; Prop 4.1 ignores untracked exchanges)* | `LegalSplit.stay s : LegalSplit s s s` (permitted at any state) | **Intentional strengthening (`FB-04`).** Strictly enlarges the universally quantified strategy class and closes `GAP B` (untracked tree exchanges). | Proved |
| History-dependent move selection + fresh fair coin orientation | `inductive Strategy : Nat → FrogState → Type` (`stop` / `step legal left right`) | **Faithful for deterministic coin-history policies (`FB-05`).** Distinct child trees `left` and `right` allow arbitrary dependence on the entire prior sequence of binary coin outcomes (including stutter outcomes), while choosing `legal` before branching enforces non-anticipation. | Proved |
| Product potential $P_d = \prod_{i=1}^k X_i(d)$ and $\mathbb{E} P_d \le P_0 \le 2^k$ | `potential s := s.prod`, `totalPotential`, `totalPotential_le : totalPotential t ≤ 2 ^ d * potential s` | **Exact finite-horizon match.** `totalPotential t` equals $2^d \mathbb{E}[P_d]$ for the uniform distribution over the $2^d$ coin histories (`historyCount_eq_pow`). | Lean-Verified (per Lumi's build) / Proved |
| Event "all frogs reached position $3$ by step $d$" and probability $p_d$ | `successCount (s.length) t` checking `s = List.replicate k 3` at depth-$d$ leaves | **Extensionally equivalent at fixed $d$, equivalence unproved (`FB-03`).** Matches "by step $d$" only because `List.replicate k 3` is absorbing under `LegalSplit`, a lemma not proved in the file. | Proved |
| Finite-horizon bound $p_d \le (2/3)^k$ | `finite_horizon_frog_bound : 3 ^ s.length * successCount s.length t ≤ 2 ^ (d + s.length)` | **Algebraically equivalent integer form (`FB-02`).** Equivalent to `(successCount / historyCount : ℚ) ≤ (2/3)^k` since `historyCount t = 2^d > 0` and `3^k > 0`. | Lean-Verified (per Lumi's build) / Proved |
| Asymptotic conclusion: $\mathbb{P}[\text{all frogs eventually reach } 3] = \lim_{d\to\infty} p_d \le (2/3)^k$ | **Not formalized** (explicitly disclaimed in header docstring) | **Primary scope gap (`FB-01`).** No infinite process, no monotone sequence $p_d$, no limit / `iSup`, and no probability measure on infinite coin sequences. | Empirical Observation |

*(Sources for comparison table: TR26-332 pp. 15–16 and `FrogBound.lean` lines 1–363)*.

---

## 2. Adversarial Gap & Invariant Audit

### 2.1 Flagged Gaps

| Gap ID | Category | Severity | Direction | Finding | Claim Level |
| --- | --- | --- | --- | --- | --- |
| **`FB-01`** | Finite-horizon vs. asymptotic ("eventually") | **High** (for full Lem 4.4) | Scope restriction (stated) | `finite_horizon_frog_bound` proves only a fixed-depth-$d$ bound; it omits an infinite-horizon process definition, monotonicity of $p_d$, the limit $\lim_{d\to\infty} p_d \le (2/3)^k$, and continuity of probability on $\mathbb{N} \to \mathrm{Bool}$. Explicitly disclaimed in `FrogBound.lean` lines 38–40. | Empirical Observation |
| **`FB-02`** | Integer vs. real/rational probability | **Low** | Equivalent reformulation | Main theorem states `3 ^ k * successCount k t ≤ 2 ^ (d + k)` over `Nat` and omits `historyCount t` from its signature. Algebraically equivalent to `(successCount / historyCount : ℚ) ≤ (2/3)^k` via `historyCount_eq_pow`, but the probability form is left as a prose comment (lines 336–337). | Proved |
| **`FB-03`** | Unproved absorbing-state & state-bound invariants | **Medium** | Omitted specification lemma | `FrogState := List Nat` permits arbitrary `Nat` values, and `successCount` tests `s = List.replicate k 3` *at the leaf* rather than "reached $3^k$ at some step $\le d$." While `LegalSplit` genuinely keeps `{0,1,2,3}` invariant and fixes every frog at `0` or `3` (making "at step $d$" equivalent to "by step $d$"), none of these three properties is stated or machine-checked in `FrogBound.lean`. | Proved (of `LegalSplit`) / Empirical Observation (omission) |
| **`FB-04`** | Added move (`LegalSplit.stay`) | **Low** | Strengthening | `LegalSplit.stay` allows stuttering even when active frogs remain, whereas Lemma 4.4 lists only moves (1) and (2) (with staying mentioned in §4.1 only after all frogs are absorbed). Because `t` is universally quantified, this strictly strengthens the theorem and repairs `GAP B` for Prop 4.1. | Proved |
| **`FB-05`** | Fixed-depth deterministic trees vs. variable stopping times & external randomness | **Low** | Minor modeling nuance | (a) `Strategy d s` has uniform depth $d$; any bounded variable-depth stopping tree embeds via `stay`-padding without changing leaf probabilities, though this embedding is unproved. (b) `Strategy` models deterministic coin-history dependence (sufficient for Prop 4.1's fixed-rule exchanges), not external non-binary randomization (which reduces to deterministic strategies by averaging). (c) Unbounded a.s.-finite stopping time $\tau$ belongs to Claim 4.3 / Prop 4.1, not Lemma 4.4. | Proved |
| **`FB-06`** | Unused `1 ≤ x` hypothesis & $k=0$ boundary | **Low** | Informational | `finite_horizon_frog_bound` takes `hstart : ∀ x ∈ s, 1 ≤ x ∧ x ≤ 2` but uses only `x ≤ 2`; harmless and faithful to Lemma 4.4's text. For `k = 0` (`s = []`), `hstart` holds vacuously and the bound gives `1 * 2^d ≤ 2^d` (matching $(2/3)^0 = 1$, tested by `emptyOneStep`). | Lean-Verified (per Lumi's build) / Proved |
| **`FB-07`** | Scope boundary & file hygiene | **Low** | Documentation / hygiene | (a) Prop 4.1's reduction from spanning-tree exchanges $(T_1,T_2,T_3)$ to frog moves (`a_e = | {i : e ∈ T_i} |

*(Sources for gap table: TR26-332 pp. 14–16 and `FrogBound.lean` lines 1–478)*.

### 2.2 Explicit Checks That Passed Cleanly (No Gap Found)

* **Off-by-one horizon check (`OK`).** At `d = 0`, `Strategy 0 s` takes 0 moves (`stop s`), has `historyCount = 1 = 2^0`, and gives `3^k * successCount ≤ 2^k` (for $k \ge 1$ and $s \subseteq \{1,2\}$, `successCount = 0`). At `d`, exactly `d` moves / `d` fair coin flips occur, with `historyCount = 2^d` and denominator `2^d`, matching Section 4.1's $X_i(d)$, $P_d$, and $p_d$ with zero off-by-one shift. **[Claim Level: Proved]**


* **Quantifier order check (`OK`).** `finite_horizon_frog_bound` universally quantifies over `d : Nat`, `s : FrogState`, `t : Strategy d s`, and `hstart` (note that quantifying `t` *inside* `d` even permits horizon-aware strategies, strictly stronger than truncations of a single horizon-independent process). No existential quantifier weakens the claim. **[Claim Level: Proved]**


* **Non-anticipation check (`OK`).** In `Strategy.step legal left right`, the move `legal : LegalSplit s l r` is fixed before branching into `left` and `right`, matching Lemma 4.4's requirement that "its orientation is determined by a fresh fair coin". **[Claim Level: Proved]**


* **No paper-proved conclusions assumed as hypotheses (`OK`).** Within the finite-horizon theorem, `legalSplit_potential`, `totalPotential_le`, `potential_le_two_pow`, `potential_success_state`, and `successCount_weighted_le` are all proved from first principles rather than assumed. **[Claim Level: Lean-Verified (per Lumi's build)]**


* **Two-frog distinctness & full move coverage (`OK`).** `LegalSplit.pair` splits `s` as `pre ++ [x+1] ++ mid ++ [y+1] ++ post`, guaranteeing the two moved indices satisfy `i = pre.length < pre.length + 1 + mid.length = j`, while `LegalSplit.flip` provides both orientations. Every legal single-frog or two-frog move from Lemma 4.4 is representable. **[Claim Level: Proved]**



---

## 3. Summary of Severities & Acceptance Recommendation

* **High:** `FB-01` (asymptotic "eventually" limit not formalized — stated restriction).
* **Medium:** `FB-03` (absorbing-state invariance and "at step $d$ $\iff$ by step $d$" equivalence unproved in Lean).
* **Low:** `FB-02`, `FB-04`, `FB-05`, `FB-06`, `FB-07`.

**Recommendation:** Accept `FrogBound.lean` as a **Lean-Verified finite-horizon frog lemma** (faithful with stated restrictions), and open a small follow-up PR adding Tier 1 (absorbing invariants + rational/real probability bound) and Tier 2a (`InfiniteProcess` + monotone `probBy` + `⨆ d, probBy P d ≤ (2/3)^k`) below. That closes `FB-01`, `FB-02`, and `FB-03` completely without requiring heavy product-measure boilerplate (with an optional Tier 2b hook if we later connect to `MeasureTheory.Measure.infinitePi` on `ℕ → Bool`).

**[Claim Level: Conjecture — engineering recommendation]**

---

## 4. Proposed Tightened Lean Statements (**UNBUILT**)

> **STATUS: UNBUILT — NOT COMPILED WITH `lake build`.**
> All Lean code below is proposed specification/theorem code only. Mathematical truth of the statements is **[Claim Level: Proved]**; Lean 4.24.0 / Mathlib v4.24.0 type-checking and compilability are **[Claim Level: Conjecture]** until Lumi runs `lake build`.

```lean
-- Proposed additions inside `namespace Millennium.FrogBound`
-- STATUS: UNBUILT (not compiled with `lake build`)

/-! ### Tier 1: State bounds, coordinatewise absorption, and rational probability form -/

/--
Closes FB-03 (part 1): If every frog starts in `0..3`,
a legal move keeps every frog in `0..3`.
-/
theorem legalSplit_le_three
    {s l r : FrogState}
    (h : LegalSplit s l r)
    (hs : ∀ x ∈ s, x ≤ 3) :
    (∀ x ∈ l, x ≤ 3) ∧ (∀ x ∈ r, x ≤ 3) := by
  sorry -- UNBUILT

/--
Closes FB-03 (part 2): Positions `0` and `3` are absorbing
coordinatewise — if frog `i` is at `0` or `3`, neither coin
outcome changes frog `i`'s position.
-/
theorem legalSplit_absorbing_coord
    {s l r : FrogState}
    (h : LegalSplit s l r)
    (i : Nat)
    (habs : s[i]? = some 0 ∨ s[i]? = some 3) :
    l[i]? = s[i]? ∧ r[i]? = s[i]? := by
  sorry -- UNBUILT

/--
Closes FB-03 (part 3): The all-3 state is absorbing as a whole.
Once reached at any step `m ≤ d`, every descendant at depth `d`
remains `List.replicate k 3`, so checking leaves at depth `d` is
equivalent to "reached all-3 by step `d`".
-/
theorem legalSplit_all_three_fixed
    {k : Nat} {l r : FrogState}
    (h : LegalSplit (List.replicate k 3) l r) :
    l = List.replicate k 3 ∧ r = List.replicate k 3 := by
  sorry -- UNBUILT

/--
Closes FB-02: Explicit rational probability form matching
TR26-332 Section 4.1 (`p_d ≤ (2/3)^k`), using `historyCount t`.
-/
theorem finite_horizon_frog_prob_bound_rat
    {d : Nat}
    {s : FrogState}
    (t : Strategy d s)
    (hstart : ∀ x ∈ s, 1 ≤ x ∧ x ≤ 2) :
    (successCount s.length t : ℚ) / (historyCount t : ℚ) ≤
      ((2 : ℚ) / 3) ^ s.length := by
  sorry -- UNBUILT

/-! ### Tier 2a: Infinite-horizon adaptive process and limit bound `lim_{d→∞} p_d ≤ (2/3)^k` -/

/--
Closes FB-01 (process model): An infinite-horizon adaptive frog
process starting at `s₀`.

For every finite coin history `h : List Bool` (length = step count),
`state h` is the frog configuration after history `h`, and `step h`
certifies that the next move is a `LegalSplit` chosen solely from `h`
before flipping the fresh fair coin (`false` / `true`).
-/
structure InfiniteProcess (s₀ : FrogState) where
  state : List Bool → FrogState
  init : state [] = s₀
  step : ∀ h : List Bool,
    LegalSplit (state h) (state (h ++ [false])) (state (h ++ [true]))

/-- Depth-`d` truncation of `P` starting from coin history `h`. -/
def InfiniteProcess.truncateFrom
    {s₀ : FrogState}
    (P : InfiniteProcess s₀) :
    (h : List Bool) → (d : Nat) → Strategy d (P.state h)
  | h, 0 => .stop (P.state h)
  | h, d + 1 =>
      .step (P.step h)
        (P.truncateFrom (h ++ [false]) d)
        (P.truncateFrom (h ++ [true]) d)

/-- Depth-`d` truncation of `P` from the initial state `s₀`. -/
def InfiniteProcess.truncate
    {s₀ : FrogState}
    (P : InfiniteProcess s₀)
    (d : Nat) : Strategy d s₀ :=
  P.init ▸ P.truncateFrom [] d

/-- Probability `p_d` that all frogs have reached `3` by step `d`. -/
noncomputable def InfiniteProcess.probBy
    {s₀ : FrogState}
    (P : InfiniteProcess s₀)
    (d : Nat) : ℝ :=
  (successCount s₀.length (P.truncate d) : ℝ) / (2 : ℝ) ^ d

/--
By `legalSplit_all_three_fixed`, the sequence `p_d` is monotone
nondecreasing in `d` (matching TR26-332 Section 4.1: "these events
increase with d").
-/
theorem InfiniteProcess.probBy_mono
    {s₀ : FrogState}
    (P : InfiniteProcess s₀) :
    Monotone P.probBy := by
  sorry -- UNBUILT

/--
Closes FB-01 (limit form of TR26-332 Lemma 4.4 / Section 4.1):
For any infinite-horizon adaptive frog process starting in `{1, 2}^k`,
`p_d` converges to `⨆ d, p_d` and its limit is at most `(2 / 3) ^ k`.
-/
theorem infinite_horizon_frog_limit_bound
    {s₀ : FrogState}
    (P : InfiniteProcess s₀)
    (hstart : ∀ x ∈ s₀, 1 ≤ x ∧ x ≤ 2) :
    Filter.Tendsto P.probBy Filter.atTop (nhds (⨆ d : Nat, P.probBy d)) ∧
      (⨆ d : Nat, P.probBy d) ≤ ((2 : ℝ) / 3) ^ s₀.length := by
  sorry -- UNBUILT

```

*(Note on optional Tier 2b — true Cantor-space event measure: once `InfiniteProcess` and `infinite_horizon_frog_limit_bound` exist, connecting `⨆ d, P.probBy d` to the measure of `{ω : ℕ → Bool | ∃ d, P.state (List.ofFn (fun i : Fin d => ω i)) = List.replicate s₀.length 3}` under the fair Bernoulli product measure on `ℕ → Bool` is a single application of upward continuity of measure `MeasureTheory.measure_iUnion_eq_iSup` plus cylinder-set counting.)* **[Claim Level: Proved (mathematical bridge) / Conjecture (Mathlib API wiring)]**

---

— **Gemini | Galactic AI Team | Operation Millennium**