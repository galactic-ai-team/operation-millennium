/-
  Operation Millennium — Phase 4 Adversarial Review of PR #7
  Independent Concrete Instantiations & Adversarial Edge-Case Tests

  Author: Gemini — Galactic AI Team
  Target: dev @ e55d5db (Millennium.Tseitin)
  Toolchain: Lean 4.24.0 / Mathlib v4.24.0
  Status: SUBMITTED FOR BUILD EXECUTION (NOT RUN by author)

  Covers:
    1. Concrete K4 odd-charge instantiation discharging
       TripleIncidenceMatches, coverage, and applying tseitinCNF_odd_unsat.
    2. Concrete K4 even-charge satisfiable fixture (two nontrivial witnesses
       exercising both rhs = true and rhs = false clauses).
    3. Adversarial test: non-injective idx makes even-charge connected K4 UNSAT.
    4. Adversarial test: self-loop 3-regular multigraph instantiation and
       inspection of duplicate-literal / tautological clauses in xor3CNF.
    5. Adversarial test: disconnected K4 ⊔ K4 with even global charge (0)
       yet two odd components is UNSAT outside hOdd.
    6. Adversarial test: variable index 0 polarity collision in tseitinFixtureLiteral.
    7. Explicit #print axioms audit for PR #7 theorems and test theorems.
-/

import Mathlib
import Millennium.Sat
import Millennium.Tseitin

open scoped BigOperators

namespace Millennium.Tests.TseitinAdversarial

/-! ## 1. Helper: Converse local-to-global CNF evaluation -/

/--
If an assignment satisfies every local XOR block in the vertex list,
then it satisfies the concatenated Tseitin CNF.
-/
theorem evalCNF_tseitin_of_local
    {V E : Type*}
    (idx : E → Nat)
    (a b c : V → E)
    (charge : V → Bool)
    (σ : Assignment) :
    ∀ (vertices : List V),
      (∀ w ∈ vertices,
        evalCNF
          (xor3CNF (idx (a w)) (idx (b w)) (idx (c w)) (charge w)) σ = true) →
      evalCNF (tseitinCNF idx a b c charge vertices) σ = true := by
  intro vertices
  induction vertices with
  | nil =>
      intro _
      simp [tseitinCNF, evalCNF]
  | cons v vs ih =>
      intro h
      rw [tseitinCNF, evalCNF_append]
      have hv :
          evalCNF
            (xor3CNF (idx (a v)) (idx (b v)) (idx (c v)) (charge v)) σ = true :=
        h v (by simp)
      have hvs : evalCNF (tseitinCNF idx a b c charge vs) σ = true :=
        ih (fun w hw => h w (by simp [hw]))
      rw [hv, hvs]
      rfl

/-! ## 2. Concrete K4 Graph (Fin 4 vertices, Fin 6 edges) -/

/-
  Edges of K4:
    0 : (0, 1)    1 : (0, 2)    2 : (0, 3)
    3 : (1, 2)    4 : (1, 3)    5 : (2, 3)
  Incident triples:
    v0 : (0, 1, 2)
    v1 : (0, 3, 4)
    v2 : (1, 3, 5)
    v3 : (2, 4, 5)
-/

def k4U (e : Fin 6) : Fin 4 :=
  match e.val with
  | 0 => 0
  | 1 => 0
  | 2 => 0
  | 3 => 1
  | 4 => 1
  | _ => 2

def k4V (e : Fin 6) : Fin 4 :=
  match e.val with
  | 0 => 1
  | 1 => 2
  | 2 => 3
  | 3 => 2
  | 4 => 3
  | _ => 3

def k4A (w : Fin 4) : Fin 6 :=
  match w.val with
  | 0 => 0
  | 1 => 0
  | 2 => 1
  | _ => 2

def k4B (w : Fin 4) : Fin 6 :=
  match w.val with
  | 0 => 1
  | 1 => 3
  | 2 => 3
  | _ => 4

def k4C (w : Fin 4) : Fin 6 :=
  match w.val with
  | 0 => 2
  | 1 => 4
  | 2 => 5
  | _ => 5

/-- Positive, injective 1-indexed DIMACS variable map (1..6). -/
def k4Idx (e : Fin 6) : Nat := e.val + 1

def k4Vertices : List (Fin 4) := [0, 1, 2, 3]

theorem k4Idx_pos (e : Fin 6) : 0 < k4Idx e :=
  Nat.succ_pos e.val

theorem k4Idx_injective : Function.Injective k4Idx := by
  intro e1 e2 h
  exact Fin.ext (Nat.succ.inj h)

theorem k4_incidence_matches :
    TripleIncidenceMatches k4U k4V k4A k4B k4C := by
  intro w e
  fin_cases w <;> fin_cases e <;> decide

theorem k4_cover : ∀ w : Fin 4, w ∈ k4Vertices := by
  intro w
  fin_cases w <;> simp [k4Vertices]

/-! ## 3. Concrete K4 Odd-Charge Unsatisfiability Instantiation -/

/-- Odd total charge on K4: vertex 0 has charge 1; vertices 1, 2, 3 have charge 0. -/
def k4OddCharge (w : Fin 4) : Bool := w == 0

theorem k4_odd_charge_sum :
    (∑ w : Fin 4, bitValue (k4OddCharge w)) = 1 := by
  rw [Fin.sum_univ_four]
  decide

/-- Nonvacuous application of tseitinCNF_odd_unsat to K4. -/
theorem k4_odd_tseitin_unsat :
    ¬ ∃ σ : Assignment,
      evalCNF
        (tseitinCNF k4Idx k4A k4B k4C k4OddCharge k4Vertices) σ = true :=
  tseitinCNF_odd_unsat
    k4U k4V k4Idx k4A k4B k4C k4OddCharge k4Vertices
    k4_cover k4_incidence_matches k4_odd_charge_sum

/-! ## 4. Concrete K4 Even-Charge Satisfiable Fixtures -/

/--
Nontrivial even total charge on K4: vertices 0 and 1 have charge true,
vertices 2 and 3 have charge false (exercises both rhs=true and rhs=false).
-/
def k4EvenCharge (w : Fin 4) : Bool := (w == 0) || (w == 1)

theorem k4_even_charge_sum :
    (∑ w : Fin 4, bitValue (k4EvenCharge w)) = 0 := by
  rw [Fin.sum_univ_four]
  decide

/-- Witness 1: edge 0 = (0,1) (var 1) is true; all other edges false. -/
def k4EvenWitness1 : Assignment := fun n => n == 1

/-- Witness 2: path 0-2-1, i.e., edges 1 (var 2) and 3 (var 4) are true; others false. -/
def k4EvenWitness2 : Assignment := fun n => (n == 2) || (n == 4)

theorem k4_even_tseitin_sat_witness1 :
    evalCNF
      (tseitinCNF k4Idx k4A k4B k4C k4EvenCharge k4Vertices)
      k4EvenWitness1 = true := by
  apply evalCNF_tseitin_of_local
  intro w _
  rw [xor3CNF_correct]
  fin_cases w <;> decide

theorem k4_even_tseitin_sat_witness2 :
    evalCNF
      (tseitinCNF k4Idx k4A k4B k4C k4EvenCharge k4Vertices)
      k4EvenWitness2 = true := by
  apply evalCNF_tseitin_of_local
  intro w _
  rw [xor3CNF_correct]
  fin_cases w <;> decide

theorem k4_even_tseitin_sat :
    ∃ σ : Assignment,
      evalCNF
        (tseitinCNF k4Idx k4A k4B k4C k4EvenCharge k4Vertices) σ = true :=
  ⟨k4EvenWitness1, k4_even_tseitin_sat_witness1⟩

/-! ## 5. Adversarial Case A (GEMINI-R7-02): Non-injective idx breaks even-charge SAT -/

def badConstIdx (_ : Fin 6) : Nat := 1

theorem k4_even_noninjective_idx_unsat :
    ¬ ∃ σ : Assignment,
      evalCNF
        (tseitinCNF badConstIdx k4A k4B k4C k4EvenCharge k4Vertices)
        σ = true := by
  intro ⟨σ, hσ⟩
  have h0 :=
    eval_tseitinCNF_local
      badConstIdx k4A k4B k4C k4EvenCharge σ k4Vertices hσ 0 (by simp [k4Vertices])
  have h2 :=
    eval_tseitinCNF_local
      badConstIdx k4A k4B k4C k4EvenCharge σ k4Vertices hσ 2 (by simp [k4Vertices])
  rw [xor3CNF_correct] at h0 h2
  simp only [badConstIdx] at h0 h2
  cases hb : σ 1 with
  | false =>
      rw [hb] at h0
      exact absurd h0 (by decide)
  | true =>
      rw [hb] at h2
      exact absurd h2 (by decide)

/-! ## 6. Adversarial Case B (GEMINI-R7-03): Self-loop 3-regular multigraph -/

/-
  2 vertices (Fin 2), 3 edges (Fin 3):
    e0 : self-loop at 0
    e1 : bridge (0, 1)
    e2 : self-loop at 1
  Every vertex has degree 2 + 1 = 3.
-/

def slU (e : Fin 3) : Fin 2 :=
  match e.val with
  | 0 => 0
  | 1 => 0
  | _ => 1

def slV (e : Fin 3) : Fin 2 :=
  match e.val with
  | 0 => 0
  | 1 => 1
  | _ => 1

def slA (w : Fin 2) : Fin 3 :=
  match w.val with
  | 0 => 0
  | _ => 2

def slB (w : Fin 2) : Fin 3 :=
  match w.val with
  | 0 => 0
  | _ => 2

def slC (_ : Fin 2) : Fin 3 := 1

def slIdx (e : Fin 3) : Nat := e.val + 1
def slVertices : List (Fin 2) := [0, 1]
def slOddCharge (w : Fin 2) : Bool := w == 0

theorem sl_incidence_matches :
    TripleIncidenceMatches slU slV slA slB slC := by
  intro w e
  fin_cases w <;> fin_cases e <;> decide

theorem sl_cover : ∀ w : Fin 2, w ∈ slVertices := by
  intro w
  fin_cases w <;> simp [slVertices]

theorem sl_odd_charge_sum :
    (∑ w : Fin 2, bitValue (slOddCharge w)) = 1 := by
  rw [Fin.sum_univ_two]
  decide

theorem selfLoop_odd_tseitin_unsat :
    ¬ ∃ σ : Assignment,
      evalCNF
        (tseitinCNF slIdx slA slB slC slOddCharge slVertices) σ = true :=
  tseitinCNF_odd_unsat
    slU slV slIdx slA slB slC slOddCharge slVertices
    sl_cover sl_incidence_matches sl_odd_charge_sum

/-- Exhibits duplicate literals and tautological clauses emitted for self-loop vertex 0. -/
theorem selfLoop_vertex0_tautologies :
    tseitinFixtureCNF
      (xor3CNF (slIdx (slA 0)) (slIdx (slB 0)) (slIdx (slC 0)) true) =
    [
      [1, 1, 2],
      [1, -1, -2],
      [-1, 1, -2],
      [-1, -1, 2]
    ] := by
  decide

/-! ## 7. Adversarial Case C (GEMINI-R7-04): Disconnected K4 ⊔ K4, even global charge, UNSAT -/

def discU (p : Fin 2 × Fin 6) : Fin 2 × Fin 4 := (p.1, k4U p.2)
def discV (p : Fin 2 × Fin 6) : Fin 2 × Fin 4 := (p.1, k4V p.2)
def discA (p : Fin 2 × Fin 4) : Fin 2 × Fin 6 := (p.1, k4A p.2)
def discB (p : Fin 2 × Fin 4) : Fin 2 × Fin 6 := (p.1, k4B p.2)
def discC (p : Fin 2 × Fin 4) : Fin 2 × Fin 6 := (p.1, k4C p.2)

def discIdx (p : Fin 2 × Fin 6) : Nat :=
  match p.1.val with
  | 0 => k4Idx p.2
  | _ => k4Idx p.2 + 6

def discCharge (p : Fin 2 × Fin 4) : Bool := k4OddCharge p.2

def discVertices : List (Fin 2 × Fin 4) :=
  k4Vertices.map (fun w => ((0 : Fin 2), w)) ++
  k4Vertices.map (fun w => ((1 : Fin 2), w))

theorem disc_cover : ∀ p : Fin 2 × Fin 4, p ∈ discVertices := by
  intro ⟨c, w⟩
  fin_cases c <;> fin_cases w <;> simp [discVertices, k4Vertices]

theorem disc_incidence_matches :
    TripleIncidenceMatches discU discV discA discB discC := by
  intro ⟨c1, w⟩ ⟨c2, e⟩
  fin_cases c1 <;> fin_cases c2 <;> fin_cases w <;> fin_cases e <;> decide

/-- Global total charge is 0 (even), so tseitinCNF_odd_unsat does not directly apply. -/
theorem disc_global_charge_even :
    (∑ p : Fin 2 × Fin 4, bitValue (discCharge p)) = 0 := by
  rw [Fintype.sum_prod_type, Fin.sum_univ_two]
  simp only [discCharge, k4_odd_charge_sum]
  decide

/-- Yet the disconnected CNF is UNSAT due to odd charge in component 0. -/
theorem disconnected_even_global_unsat :
    ¬ ∃ σ : Assignment,
      evalCNF
        (tseitinCNF discIdx discA discB discC discCharge discVertices)
        σ = true := by
  intro ⟨σ, hσ⟩
  apply k4_odd_tseitin_unsat
  refine ⟨σ, evalCNF_tseitin_of_local k4Idx k4A k4B k4C k4OddCharge σ k4Vertices ?_⟩
  intro w hw
  have hmem : ((0 : Fin 2), w) ∈ discVertices := by
    simp [discVertices, hw]
  have hloc :=
    eval_tseitinCNF_local
      discIdx discA discB discC discCharge σ discVertices hσ (0, w) hmem
  simpa [discIdx, discA, discB, discC, discCharge] using hloc

/-! ## 8. Adversarial Case D (GEMINI-R7-05): Zero-index fixture polarity collision -/

theorem fixture_zero_index_collision :
    tseitinFixtureLiteral (Literal.pos 0) =
      tseitinFixtureLiteral (Literal.neg 0) := by
  decide

end Millennium.Tests.TseitinAdversarial

/-! ## 9. Independent Axiom Audit -/

#print axioms Millennium.sum_vertexParity_eq_zero
#print axioms Millennium.odd_charge_unsat
#print axioms Millennium.vertexParity_eq_triple
#print axioms Millennium.xor3Parity_bitValue
#print axioms Millennium.xor3Parity_check_iff
#print axioms Millennium.xor3CNF_correct
#print axioms Millennium.xor3CNF_correct_mod2
#print axioms Millennium.evalCNF_append
#print axioms Millennium.eval_tseitinCNF_local
#print axioms Millennium.tseitinCNF_odd_unsat
#print axioms Millennium.xor3CNF_dimacs_true
#print axioms Millennium.xor3CNF_dimacs_false
#print axioms Millennium.Tests.TseitinAdversarial.k4_odd_tseitin_unsat
#print axioms Millennium.Tests.TseitinAdversarial.k4_even_tseitin_sat
#print axioms Millennium.Tests.TseitinAdversarial.k4_even_tseitin_sat_witness2
#print axioms Millennium.Tests.TseitinAdversarial.k4_even_noninjective_idx_unsat
#print axioms Millennium.Tests.TseitinAdversarial.selfLoop_odd_tseitin_unsat
#print axioms Millennium.Tests.TseitinAdversarial.disconnected_even_global_unsat

