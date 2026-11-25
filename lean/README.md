# Phase 5 Formal Verification Workspace (`lean/`)

Lean 4 + Mathlib project skeleton for Operation Millennium.

## Local Setup (Free)

1. Install `elan` (Lean version manager): https://leanprover-community.github.io/get_started.html
2. Fetch prebuilt Mathlib oleans and build:
   ```bash
   cd lean
   lake exe cache get
   lake build
   ```

## Contents

- `lean-toolchain`: pinned to `leanprover/lean4:v4.24.0`
- `lakefile.toml`: declares library `Millennium` and pins `mathlib` to `v4.24.0`
- `Millennium/Sat.lean`: formal definitions of `Literal`, `Clause`, `CNF`, `Assignment`, `verifyCertificate`, and warm-up theorems (`evalCNF_empty`, `verifyCertificate_sound`, `mem_empty_clause_unsat`, `no_sat_if_empty_clause`) with zero `sorry`s.
