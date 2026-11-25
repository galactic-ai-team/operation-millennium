
-- lean/Millennium/FrogBound.lean
import Mathlib

/-!
# Finite-horizon frog bound

Operation Millennium, Phase 5.

Author: Ace — Galactic AI Team

Source:
Itsykson and Smirnov, ECCC TR26-332,
Lemma 4.4, Sections 4 and 4.1.

Claim level:
The mathematical argument is Proved.
This Lean implementation is UNVERIFIED until
the repository build and axiom audit succeed.

We use ordered lists of natural-number positions.

A legal move affects either one active frog
or two distinct active frogs. The two successors
represent the outcomes of a fresh fair coin.

Stuttering is permitted. This handles exchanges
in the spanning-tree process that involve no
tracked edges, as well as absorbing states.

A strategy is a full binary decision tree of
fixed depth. Subsequent moves may depend on
the entire previous sequence of coin outcomes.

The main result is the integer inequality

    3^k * successful_histories <= 2^(d+k).

No probability-measure infrastructure is needed.

This file does not formalize the infinite-horizon
limit, spanning-tree packing, or the complete
resolution lower-bound theorem.
-/

namespace Millennium
namespace FrogBound

/-- Ordered frog positions. -/
abbrev FrogState := List Nat

/-- Product potential of the frog positions. -/
def potential (s : FrogState) : Nat :=
  s.prod

/--
A legal pair of successor states.

For `single` and `pair`, the parameter `x`
represents an active position `x + 1`,
where `x <= 1`.

Consequently the active positions are 1 and 2,
and their successor positions remain in 0..3.

The list decompositions ensure that the two
frogs in `pair` are distinct.

`flip` exchanges the names of the coin outcomes
without changing their probabilities.
-/
inductive LegalSplit :
    FrogState → FrogState → FrogState → Prop where
  | stay (s : FrogState) :
      LegalSplit s s s
  | single
      (pre post : FrogState)
      (x : Nat)
      (hx : x ≤ 1) :
      LegalSplit
        (pre ++ [x + 1] ++ post)
        (pre ++ [x] ++ post)
        (pre ++ [x + 2] ++ post)
  | pair
      (pre mid post : FrogState)
      (x y : Nat)
      (hx : x ≤ 1)
      (hy : y ≤ 1) :
      LegalSplit
        (pre ++ [x + 1] ++ mid ++
          [y + 1] ++ post)
        (pre ++ [x] ++ mid ++
          [y + 2] ++ post)
        (pre ++ [x + 2] ++ mid ++
          [y] ++ post)
  | flip
      {s l r : FrogState}
      (h : LegalSplit s l r) :
      LegalSplit s r l

/--
A legal move preserves the number of frogs
in both successor states.
-/
theorem legalSplit_length
    {s l r : FrogState}
    (h : LegalSplit s l r) :
    l.length = s.length ∧
      r.length = s.length := by
  induction h with
  | stay s =>
      simp
  | single pre post x hx =>
      simp
  | pair pre mid post x y hx hy =>
      simp
  | flip h ih =>
      exact ⟨ih.2, ih.1⟩

/--
The fundamental one-step potential inequality.

For a single active frog, the arithmetic mean
of the successor potentials equals the current
potential.

For two active frogs, the arithmetic mean
decreases by the product of the unchanged
coordinates.

The proof works entirely in natural numbers.
-/
theorem legalSplit_potential
    {s l r : FrogState}
    (h : LegalSplit s l r) :
    potential l + potential r ≤
      2 * potential s := by
  induction h with
  | stay s =>
      omega
  | single pre post x hx =>
      simp only [
        potential,
        List.prod_append,
        List.prod_cons,
        List.prod_nil,
        mul_one
      ]
      apply le_of_eq
      ring
  | pair pre mid post x y hx hy =>
      simp only [
        potential,
        List.prod_append,
        List.prod_cons,
        List.prod_nil,
        mul_one
      ]
      ring_nf <;> omega
  | flip h ih =>
      simpa [Nat.add_comm] using ih

/--
An adaptive strategy of exactly `d` coin flips,
starting in state `s`.

The two child strategies can choose different
moves, so decisions may depend on the full
previous history.

Every root-to-leaf history has exactly `d`
binary outcomes.
-/
inductive Strategy : Nat → FrogState → Type where
  | stop (s : FrogState) :
      Strategy 0 s
  | step
      {d : Nat}
      {s l r : FrogState}
      (legal : LegalSplit s l r)
      (left : Strategy d l)
      (right : Strategy d r) :
      Strategy (d + 1) s

/--
Sum of the potentials over every terminal
coin history, including repeated terminal
states reached by different histories.
-/
def totalPotential :
    {d : Nat} →
    {s : FrogState} →
    Strategy d s → Nat
  | _, _, .stop s =>
      potential s
  | _, _, .step _ left right =>
      totalPotential left +
        totalPotential right

/--
Number of terminal coin histories.

Histories are counted with multiplicity,
even when both coin outcomes lead to the
same state.
-/
def historyCount :
    {d : Nat} →
    {s : FrogState} →
    Strategy d s → Nat
  | _, _, .stop _ =>
      1
  | _, _, .step _ left right =>
      historyCount left +
        historyCount right

/--
Number of successful terminal histories:
all `k` frogs have reached position 3.

Using equality to `List.replicate k 3`
makes the target frog count explicit.
-/
def successCount (k : Nat) :
    {d : Nat} →
    {s : FrogState} →
    Strategy d s → Nat
  | _, _, .stop s =>
      if s = List.replicate k 3 then
        1
      else
        0
  | _, _, .step _ left right =>
      successCount k left +
        successCount k right

/-- A full depth-d strategy has exactly 2^d histories. -/
theorem historyCount_eq_pow
    {d : Nat}
    {s : FrogState}
    (t : Strategy d s) :
    historyCount t = 2 ^ d := by
  induction t with
  | stop s =>
      simp [historyCount]
  | @step d s l r h left right ihl ihr =>
      change
        historyCount left +
          historyCount right = 2 ^ (d + 1)
      rw [ihl, ihr, pow_succ]
      omega

/--
Finite-horizon supermartingale inequality,
expressed as an unnormalized sum.

The sum of all terminal potentials is bounded
by the initial potential multiplied by the
number of equally likely coin histories.
-/
theorem totalPotential_le
    {d : Nat}
    {s : FrogState}
    (t : Strategy d s) :
    totalPotential t ≤
      2 ^ d * potential s := by
  induction t with
  | stop s =>
      simp [totalPotential]
  | @step d s l r h left right ihl ihr =>
      change
        totalPotential left +
          totalPotential right ≤
            2 ^ (d + 1) * potential s
      calc
        totalPotential left +
            totalPotential right
            ≤ 2 ^ d * potential l +
                2 ^ d * potential r :=
          Nat.add_le_add ihl ihr
        _ = 2 ^ d *
              (potential l + potential r) := by
          ring
        _ ≤ 2 ^ d * (2 * potential s) :=
          Nat.mul_le_mul_left _
            (legalSplit_potential h)
        _ = 2 ^ (d + 1) * potential s := by
          rw [pow_succ]
          ring

/--
If every initial position is at most 2,
the product potential is at most 2^k.

This slightly weaker hypothesis suffices
for the potential bound.
-/
theorem potential_le_two_pow
    (s : FrogState) :
    (∀ x ∈ s, x ≤ 2) →
      potential s ≤ 2 ^ s.length := by
  induction s with
  | nil =>
      intro _
      simp [potential]
  | cons x xs ih =>
      intro h
      have hx : x ≤ 2 :=
        h x (by simp)
      have ht : ∀ y ∈ xs, y ≤ 2 := by
        intro y hy
        exact h y (by simp [hy])
      calc
        potential (x :: xs) =
            x * potential xs := by
          simp [potential]
        _ ≤ 2 * 2 ^ xs.length :=
          Nat.mul_le_mul hx (ih ht)
        _ = 2 ^ (x :: xs).length := by
          simp [
            List.length_cons,
            pow_succ,
            Nat.mul_comm
          ]

/-- The potential of a successful state is 3^k. -/
theorem potential_success_state
    (k : Nat) :
    potential (List.replicate k 3) =
      3 ^ k := by
  induction k with
  | zero =>
      simp [potential]
  | succ k ih =>
      rw [List.replicate_succ]
      change
        3 * potential (List.replicate k 3) =
          3 ^ (k + 1)
      rw [ih, pow_succ]
      exact Nat.mul_comm _ _

/--
Every successful history contributes exactly
3^k to the total potential. All other
histories contribute a nonnegative amount.
-/
theorem successCount_weighted_le
    (k : Nat)
    {d : Nat}
    {s : FrogState}
    (t : Strategy d s) :
    3 ^ k * successCount k t ≤
      totalPotential t := by
  induction t with
  | stop s =>
      by_cases h : s = List.replicate k 3
      · simp [
          successCount,
          totalPotential,
          h,
          potential_success_state
        ]
      · simp [
          successCount,
          totalPotential,
          h
        ]
  | @step d s l r h left right ihl ihr =>
      change
        3 ^ k *
            (successCount k left +
              successCount k right) ≤
          totalPotential left +
            totalPotential right
      rw [Nat.mul_add]
      exact Nat.add_le_add ihl ihr

/--
General finite-horizon bound in terms of the
actual initial potential.

This is stronger than replacing the initial
potential with its worst-case bound 2^k.
-/
theorem weighted_success_bound
    {d : Nat}
    {s : FrogState}
    (t : Strategy d s) :
    3 ^ s.length *
        successCount s.length t ≤
      2 ^ d * potential s := by
  exact le_trans
    (successCount_weighted_le s.length t)
    (totalPotential_le t)

/--
Finite-horizon frog inequality from
ECCC TR26-332, Lemma 4.4.

If k frogs start at positions 1 or 2 and
a legal adaptive strategy uses d fair coins,
then

    3^k * successful_histories <= 2^(d+k).

The corresponding probability inequality is
obtained by division by 3^k * 2^d.

This theorem permits stutter steps and
different adaptive choices after every
possible prior coin history.
-/
theorem finite_horizon_frog_bound
    {d : Nat}
    {s : FrogState}
    (t : Strategy d s)
    (hstart : ∀ x ∈ s, 1 ≤ x ∧ x ≤ 2) :
    3 ^ s.length *
        successCount s.length t ≤
      2 ^ (d + s.length) := by
  have hupper : ∀ x ∈ s, x ≤ 2 := by
    intro x hx
    exact (hstart x hx).2
  calc
    3 ^ s.length *
          successCount s.length t
        ≤ 2 ^ d * potential s :=
      weighted_success_bound t
    _ ≤ 2 ^ d * 2 ^ s.length :=
      Nat.mul_le_mul_left _
        (potential_le_two_pow s hupper)
    _ = 2 ^ (d + s.length) :=
      (pow_add 2 d s.length).symm

/-
Concrete executable proof fixtures.

These test the representation and counting
semantics, not merely the final inequality.
-/

section Fixtures

/-- One frog at 2: outcomes 1 and 3. -/
def oneFrogOneStep : Strategy 1 [2] :=
  .step
    (.single [] [] 1 (by decide))
    (.stop [1])
    (.stop [3])

theorem oneFrog_history_count :
    historyCount oneFrogOneStep = 2 := by
  decide

theorem oneFrog_success_count :
    successCount 1 oneFrogOneStep = 1 := by
  decide

theorem oneFrog_total_potential :
    totalPotential oneFrogOneStep = 4 := by
  decide

/--
Two distinct frogs at 1 and 2:
outcomes (0,3) and (2,1).
-/
def twoFrogOppositeStep : Strategy 1 [1, 2] :=
  .step
    (.pair [] [] [] 0 1
      (by decide) (by decide))
    (.stop [0, 3])
    (.stop [2, 1])

theorem twoFrog_history_count :
    historyCount twoFrogOppositeStep = 2 := by
  decide

theorem twoFrog_success_count :
    successCount 2 twoFrogOppositeStep = 0 := by
  decide

theorem twoFrog_total_potential :
    totalPotential twoFrogOppositeStep = 2 := by
  decide

/--
A strategy can adapt after observing a coin.

Starting at 2:
- if the first outcome is 1, move again;
- if the first outcome is 3, stutter.
-/
def adaptiveTwoStep : Strategy 2 [2] :=
  .step
    (.single [] [] 1 (by decide))
    (.step
      (.single [] [] 0 (by decide))
      (.stop [0])
      (.stop [2]))
    (.step
      (.stay [3])
      (.stop [3])
      (.stop [3]))

theorem adaptive_history_count :
    historyCount adaptiveTwoStep = 4 := by
  decide

theorem adaptive_success_count :
    successCount 1 adaptiveTwoStep = 2 := by
  decide

theorem adaptive_total_potential :
    totalPotential adaptiveTwoStep = 8 := by
  decide

/--
Zero frogs: the empty state is vacuously
successful. One stutter gives two histories,
both successful.
-/
def emptyOneStep : Strategy 1 [] :=
  .step
    (.stay [])
    (.stop [])
    (.stop [])

theorem empty_success_count :
    successCount 0 emptyOneStep = 2 := by
  decide

theorem empty_total_potential :
    totalPotential emptyOneStep = 2 := by
  decide

end Fixtures

end FrogBound
end Millennium

-- Explicit axiom audit.

#print axioms Millennium.FrogBound.legalSplit_length
#print axioms Millennium.FrogBound.legalSplit_potential
#print axioms Millennium.FrogBound.historyCount_eq_pow
#print axioms Millennium.FrogBound.totalPotential_le
#print axioms Millennium.FrogBound.potential_le_two_pow
#print axioms Millennium.FrogBound.potential_success_state
#print axioms Millennium.FrogBound.successCount_weighted_le
#print axioms Millennium.FrogBound.weighted_success_bound
#print axioms Millennium.FrogBound.finite_horizon_frog_bound

#print axioms Millennium.FrogBound.oneFrog_history_count
#print axioms Millennium.FrogBound.oneFrog_success_count
#print axioms Millennium.FrogBound.oneFrog_total_potential
#print axioms Millennium.FrogBound.twoFrog_history_count
#print axioms Millennium.FrogBound.twoFrog_success_count
#print axioms Millennium.FrogBound.twoFrog_total_potential
#print axioms Millennium.FrogBound.adaptive_history_count
#print axioms Millennium.FrogBound.adaptive_success_count
#print axioms Millennium.FrogBound.adaptive_total_potential
#print axioms Millennium.FrogBound.empty_success_count
#print axioms Millennium.FrogBound.empty_total_potential

