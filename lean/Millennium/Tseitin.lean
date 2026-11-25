-- lean/Millennium/Tseitin.lean
/-
  Operation Millennium
  Discovery Round 01 — Tseitin parity and CNF semantics

  Author: Ace — Galactic AI Team
  Base: dev 3901e30
  Target: Lean 4.24.0 / Mathlib v4.24.0

  Mathematical status:
    Classical parity argument: Proved in ordinary mathematics.
    Lean implementation: submitted for independent build verification.

  No Lean-Verified claim is made before successful CI and axiom audit.

  Scope:
    Finite parity systems over ZMod 2.
    Exact three-input XOR encodings in CNF.
    Semantic unsatisfiability of correctly encoded odd-charge
    Tseitin formulas.

  No proof-complexity lower bound or general complexity-class
  separation is asserted.
-/

import Mathlib
import Millennium.Sat

open scoped BigOperators

namespace Millennium

/-! ## Part A: Finite parity systems -/

/--
Sum a function over a finite type, retaining only its value
at a specified element.
-/
private theorem sum_at
    {I : Type*} [Fintype I] [DecidableEq I]
    (i : I) (f : I → ZMod 2) :
    (∑ j : I, if j = i then f j else 0) = f i := by
  calc
    (∑ j : I, if j = i then f j else 0) =
        (if i = i then f i else 0) := by
      apply Finset.sum_eq_single i
      · intro j _ hji
        simp [hji]
      · intro hi
        exact (hi (Finset.mem_univ i)).elim
    _ = f i := by simp

/--
The parity at a vertex is the sum of all incident edge
contributions in ZMod 2.

Each edge has two endpoints. Both endpoint incidences are
counted, including when the endpoints coincide.

Endpoint equality is written with the queried vertex on
the left; this is equivalent to the opposite orientation.
-/
def vertexParity
    {V E : Type*} [Fintype E] [DecidableEq V]
    (u v : E → V)
    (x : E → ZMod 2)
    (w : V) : ZMod 2 :=
  ∑ e : E,
    (if w = u e then x e else 0) +
    (if w = v e then x e else 0)

/--
Every edge contributes its value twice when summing
the parities of all vertices.

Since the coefficient ring has characteristic two,
the total vertex parity is zero.

No connectedness or regularity assumption is necessary.
-/
theorem sum_vertexParity_eq_zero
    {V E : Type*}
    [Fintype V] [Fintype E] [DecidableEq V]
    (u v : E → V)
    (x : E → ZMod 2) :
    (∑ w : V, vertexParity u v x w) = 0 := by
  unfold vertexParity
  rw [Finset.sum_comm]
  apply Finset.sum_eq_zero
  intro e _
  rw [Finset.sum_add_distrib]
  rw [sum_at (u e) (fun _ : V => x e)]
  rw [sum_at (v e) (fun _ : V => x e)]
  have htwo : (2 : ZMod 2) = 0 := by decide
  rw [← two_mul, htwo, zero_mul]

/--
An odd-total-charge parity system has no satisfying
edge assignment.

This theorem concerns finite parity equations, not
a particular SAT solver or proof system.
-/
theorem odd_charge_unsat
    {V E : Type*}
    [Fintype V] [Fintype E] [DecidableEq V]
    (u v : E → V)
    (charge : V → ZMod 2)
    (hodd : (∑ w : V, charge w) = 1) :
    ¬ ∃ x : E → ZMod 2,
      ∀ w : V, vertexParity u v x w = charge w := by
  intro ⟨x, hx⟩
  have hzero : (∑ w : V, charge w) = 0 := by
    calc
      (∑ w : V, charge w) =
          ∑ w : V, vertexParity u v x w := by
        apply Finset.sum_congr rfl
        intro w _
        exact (hx w).symm
      _ = 0 := sum_vertexParity_eq_zero u v x
  have hne : (1 : ZMod 2) ≠ 0 := by decide
  exact hne (hodd.symm.trans hzero)

/-! ## Part B: Exact incidence-to-triple correspondence -/

/--
A triple of edge identifiers at every vertex correctly
represents the endpoint incidence multiset.

The equality is in Nat, not ZMod 2. This ensures exact
multiplicities rather than merely parity agreement.

For a simple 3-regular graph, a, b and c enumerate the
three distinct edges incident to each vertex.

The definition also supports multigraphs and self-loops,
provided their incidences are counted correctly.
-/
def TripleIncidenceMatches
    {V E : Type*}
    [DecidableEq V] [DecidableEq E]
    (u v : E → V)
    (a b c : V → E) : Prop :=
  ∀ (w : V) (e : E),
    (if w = u e then (1 : Nat) else 0) +
      (if w = v e then 1 else 0) =
    (if e = a w then (1 : Nat) else 0) +
      (if e = b w then 1 else 0) +
      (if e = c w then 1 else 0)

/--
Converting an incidence indicator to ZMod 2 and multiplying
by an edge value is equivalent to selecting that value
when the incidence holds.
-/
private theorem count_weight
    (p : Prop) [Decidable p]
    (z : ZMod 2) :
    (↑(if p then (1 : Nat) else 0) : ZMod 2) * z =
      (if p then z else 0) := by
  by_cases hp : p <;> simp [hp]

/--
Under the exact incidence correspondence, vertex parity
is the sum of the three enumerated edge values.
-/
theorem vertexParity_eq_triple
    {V E : Type*}
    [Fintype E]
    [DecidableEq V] [DecidableEq E]
    (u v : E → V)
    (a b c : V → E)
    (x : E → ZMod 2)
    (hInc : TripleIncidenceMatches u v a b c)
    (w : V) :
    vertexParity u v x w =
      x (a w) + x (b w) + x (c w) := by
  calc
    vertexParity u v x w =
        ∑ e : E,
          (if e = a w then x e else 0) +
          (if e = b w then x e else 0) +
          (if e = c w then x e else 0) := by
      unfold vertexParity
      apply Finset.sum_congr rfl
      intro e _
      have h :=
        congrArg
          (fun n : Nat => (n : ZMod 2) * x e)
          (hInc w e)
      simpa only [Nat.cast_add, add_mul, count_weight]
        using h
    _ = x (a w) + x (b w) + x (c w) := by
      simp only [Finset.sum_add_distrib, sum_at]

/-! ## Part C: Three-input XOR and CNF semantics -/

/-- Boolean parity of three values. -/
def xor3Parity (p q r : Bool) : Bool :=
  (p != q) != r

/-- Interpret a Boolean as an element of ZMod 2. -/
def bitValue : Bool → ZMod 2
  | false => 0
  | true => 1

/--
Boolean XOR parity agrees with addition modulo two.
The proof exhausts all eight Boolean triples.
-/
theorem xor3Parity_bitValue
    (p q r : Bool) :
    bitValue (xor3Parity p q r) =
      bitValue p + bitValue q + bitValue r := by
  cases p <;> cases q <;> cases r <;> decide

/--
Checking the requested Boolean parity is equivalent to
checking the corresponding equation in ZMod 2.

This is an exhaustive proof over the sixteen possible
combinations of three Boolean inputs and one charge bit.
-/
theorem xor3Parity_check_iff
    (p q r rhs : Bool) :
    ((xor3Parity p q r == rhs) = true) ↔
      bitValue p + bitValue q + bitValue r =
        bitValue rhs := by
  cases p <;> cases q <;> cases r <;>
    cases rhs <;> decide

/--
Four-clause CNF encoding of a XOR b XOR c = rhs.

Clause order agrees with the Python _xor3_clauses
implementation in lab/om_lab/hard_instances.py
at the reviewed base commit.

The theorem below does not require distinct indices.
For a simple 3-regular graph, the three incident
edge indices are distinct.
-/
def xor3CNF (a b c : Nat) (rhs : Bool) : CNF :=
  match rhs with
  | true =>
      [
        [Literal.pos a, Literal.pos b, Literal.pos c],
        [Literal.pos a, Literal.neg b, Literal.neg c],
        [Literal.neg a, Literal.pos b, Literal.neg c],
        [Literal.neg a, Literal.neg b, Literal.pos c]
      ]
  | false =>
      [
        [Literal.neg a, Literal.neg b, Literal.neg c],
        [Literal.neg a, Literal.pos b, Literal.pos c],
        [Literal.pos a, Literal.neg b, Literal.pos c],
        [Literal.pos a, Literal.pos b, Literal.neg c]
      ]

/--
The four-clause encoding evaluates to true exactly when
the requested XOR equation holds.

The proof uses the existing Millennium.evalCNF,
Millennium.evalClause and Millennium.evalLiteral.
-/
theorem xor3CNF_correct
    (σ : Assignment)
    (a b c : Nat)
    (rhs : Bool) :
    evalCNF (xor3CNF a b c rhs) σ =
      (xor3Parity (σ a) (σ b) (σ c) == rhs) := by
  cases ha : σ a <;>
    cases hb : σ b <;>
    cases hc : σ c <;>
    cases rhs <;>
    simp only [
      xor3CNF,
      evalCNF,
      evalClause,
      evalLiteral,
      ha,
      hb,
      hc
    ] <;> rfl

/--
Arithmetic formulation of the local CNF encoding theorem.
-/
theorem xor3CNF_correct_mod2
    (σ : Assignment)
    (a b c : Nat)
    (rhs : Bool) :
    evalCNF (xor3CNF a b c rhs) σ = true ↔
      bitValue (σ a) +
        bitValue (σ b) +
        bitValue (σ c) =
      bitValue rhs := by
  rw [xor3CNF_correct]
  exact xor3Parity_check_iff
    (σ a) (σ b) (σ c) rhs

/-! ## Part D: Composition of vertex constraints -/

/--
Evaluating the concatenation of two CNFs is equivalent
to conjunction of their evaluations.
-/
theorem evalCNF_append
    (φ ψ : CNF)
    (σ : Assignment) :
    evalCNF (φ ++ ψ) σ =
      (evalCNF φ σ && evalCNF ψ σ) := by
  induction φ with
  | nil =>
      simp [evalCNF]
  | cons cl rest ih =>
      cases h : evalClause cl σ <;>
        simp [evalCNF, ih, h]

/-- Local Boolean conjunction lemma. -/
private theorem bool_and_true_iff
    (p q : Bool) :
    ((p && q) = true) ↔
      p = true ∧ q = true := by
  cases p <;> cases q <;> decide

/--
Construct a Tseitin CNF by concatenating one XOR encoding
per vertex in the supplied vertex list.

idx explicitly maps abstract graph edges to the natural
variable indices used by Millennium.Literal.

Coverage of the vertex list is required separately in
the final unsatisfiability theorem.
-/
def tseitinCNF
    {V E : Type*}
    (idx : E → Nat)
    (a b c : V → E)
    (charge : V → Bool) :
    List V → CNF
  | [] => []
  | w :: ws =>
      xor3CNF
        (idx (a w))
        (idx (b w))
        (idx (c w))
        (charge w)
      ++ tseitinCNF idx a b c charge ws

/--
A satisfying assignment of the concatenated Tseitin CNF
satisfies the local XOR encoding at every listed vertex.

Duplicate vertices are permitted: repeating a conjunct
does not invalidate this implication.
-/
theorem eval_tseitinCNF_local
    {V E : Type*}
    (idx : E → Nat)
    (a b c : V → E)
    (charge : V → Bool)
    (σ : Assignment) :
    ∀ (vertices : List V),
      evalCNF
        (tseitinCNF idx a b c charge vertices) σ = true →
      ∀ w ∈ vertices,
        evalCNF
          (xor3CNF
            (idx (a w))
            (idx (b w))
            (idx (c w))
            (charge w)) σ = true := by
  intro vertices
  induction vertices with
  | nil =>
      intro _ w hw
      simp at hw
  | cons v vs ih =>
      intro h w hw
      rw [tseitinCNF, evalCNF_append,
        bool_and_true_iff] at h
      rcases List.mem_cons.mp hw with heq | htail
      · subst w
        exact h.1
      · exact ih h.2 w htail

/-! ## Part E: Final integration theorem -/

/--
A correctly encoded finite Tseitin CNF with odd total
charge has no satisfying Boolean assignment.

Assumptions:

* V and E are finite types.
* Every edge has two specified endpoints.
* Each vertex's triple matches its exact incidence
  multiset.
* The supplied vertex list covers every vertex.
* The total charge is one in ZMod 2.

The variable map idx need not be injective for this
one-way unsatisfiability theorem: any hypothetical
satisfying CNF assignment still induces an edge assignment.

A faithful DIMACS representation should impose stronger
indexing requirements externally, including positivity
and injectivity.
-/
theorem tseitinCNF_odd_unsat
    {V E : Type*}
    [Fintype V] [Fintype E]
    [DecidableEq V] [DecidableEq E]
    (u v : E → V)
    (idx : E → Nat)
    (a b c : V → E)
    (charge : V → Bool)
    (vertices : List V)
    (hCover : ∀ w : V, w ∈ vertices)
    (hInc : TripleIncidenceMatches u v a b c)
    (hOdd : (∑ w : V, bitValue (charge w)) = 1) :
    ¬ ∃ σ : Assignment,
      evalCNF
        (tseitinCNF idx a b c charge vertices) σ = true := by
  intro ⟨σ, hσ⟩
  apply odd_charge_unsat
    u v
    (fun w => bitValue (charge w))
    hOdd
  refine ⟨fun e => bitValue (σ (idx e)), ?_⟩
  intro w
  have hlocal :=
    eval_tseitinCNF_local
      idx a b c charge σ vertices hσ w (hCover w)
  have hbits :=
    (xor3CNF_correct_mod2
      σ
      (idx (a w))
      (idx (b w))
      (idx (c w))
      (charge w)).mp hlocal
  calc
    vertexParity u v
        (fun e => bitValue (σ (idx e))) w =
      bitValue (σ (idx (a w))) +
        bitValue (σ (idx (b w))) +
        bitValue (σ (idx (c w))) :=
      vertexParity_eq_triple
        u v a b c
        (fun e => bitValue (σ (idx e)))
        hInc w
    _ = bitValue (charge w) := hbits

/-! ## Part F: Cross-language fixture checks -/

/--
Convert a literal to its signed integer representation.

This helper is for fixed positive-index fixture comparison.
It is not a validated DIMACS serializer: variable index
zero is not rejected here.
-/
def tseitinFixtureLiteral : Literal → Int
  | Literal.pos v => Int.ofNat v
  | Literal.neg v => -(Int.ofNat v)

/-- Convert a CNF to signed integer fixture lists. -/
def tseitinFixtureCNF (φ : CNF) : List (List Int) :=
  φ.map (fun cl => cl.map tseitinFixtureLiteral)

/--
Expected Python fixture for _xor3_clauses(1, 2, 3, 1).
-/
theorem xor3CNF_dimacs_true :
    tseitinFixtureCNF (xor3CNF 1 2 3 true) =
      [
        [1, 2, 3],
        [1, -2, -3],
        [-1, 2, -3],
        [-1, -2, 3]
      ] := by
  decide

/--
Expected Python fixture for _xor3_clauses(1, 2, 3, 0).
-/
theorem xor3CNF_dimacs_false :
    tseitinFixtureCNF (xor3CNF 1 2 3 false) =
      [
        [-1, -2, -3],
        [-1, 2, 3],
        [1, -2, 3],
        [1, 2, -3]
      ] := by
  decide

end Millennium

/-! ## Part G: Explicit axiom audit -/

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
