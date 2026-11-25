/-
  Operation Millennium — Phase 5 Warm-Up
  Minimal formalization of Boolean CNF formulas, SAT certificates,
  and basic soundness / unsatisfiability lemmas in Lean 4.
-/

namespace Millennium

/-- A propositional literal: positive (`pos v`) or negative (`neg v`) variable index. -/
inductive Literal where
  | pos (var : Nat)
  | neg (var : Nat)
  deriving DecidableEq, Repr

/-- A CNF clause is a disjunction of literals. -/
abbrev Clause := List Literal

/-- A CNF formula is a conjunction of clauses. -/
abbrev CNF := List Clause

/-- A truth assignment maps variable indices to Booleans. -/
abbrev Assignment := Nat → Bool

/-- Evaluate a single literal under an assignment. -/
def evalLiteral (σ : Assignment) : Literal → Bool
  | .pos v => σ v
  | .neg v => !(σ v)

/-- Evaluate a clause (disjunction): true iff at least one literal evaluates to true. -/
def evalClause (c : Clause) (σ : Assignment) : Bool :=
  match c with
  | [] => false
  | l :: ls => evalLiteral σ l || evalClause ls σ

/-- Evaluate a CNF formula (conjunction): true iff every clause evaluates to true. -/
def evalCNF (φ : CNF) (σ : Assignment) : Bool :=
  match φ with
  | [] => true
  | c :: cs => evalClause c σ && evalCNF cs σ

/-- Certificate checker: verifies that assignment `σ` satisfies `φ`. -/
def verifyCertificate (φ : CNF) (σ : Assignment) : Bool :=
  evalCNF φ σ

/-- Warm-up theorem 1: The empty CNF formula is satisfied by every assignment. -/
theorem evalCNF_empty (σ : Assignment) : evalCNF [] σ = true := rfl

/-- Warm-up theorem 2: Certificate soundness. -/
theorem verifyCertificate_sound (φ : CNF) (σ : Assignment)
    (h : verifyCertificate φ σ = true) : evalCNF φ σ = true :=
  h

/-- Warm-up theorem 3: Any CNF containing the empty clause is unsatisfiable. -/
theorem mem_empty_clause_unsat (φ : CNF) (hmem : ([] : Clause) ∈ φ) (σ : Assignment) :
    evalCNF φ σ = false := by
  induction φ with
  | nil =>
    cases hmem
  | cons c cs ih =>
    simp only [List.mem_cons] at hmem
    rcases hmem with rfl | htail
    · simp [evalCNF, evalClause]
    · simp [evalCNF, ih htail]

/-- Corollary: A CNF containing the empty clause has no satisfying assignment. -/
theorem no_sat_if_empty_clause (φ : CNF) (hmem : ([] : Clause) ∈ φ) :
    ¬ ∃ σ : Assignment, evalCNF φ σ = true := by
  intro ⟨σ, hsat⟩
  have hfalse := mem_empty_clause_unsat φ hmem σ
  rw [hsat] at hfalse
  contradiction

end Millennium
