# Phase 4 — Structural Counterexamples for Tseitin Matched Pairs

Status: Phase 3 Discovery Round 01 deliverable for Dee.
Claim levels follow `docs/RULES.md`.

## Purpose

This suite attacks the structural assumptions behind matched Tseitin
even-charge / odd-charge comparisons. It does not claim a new theorem and does
not claim a complexity separation. It constructs matched formulas, checks the
expected parity obstruction, independently validates the all-zero witness, and
adds negative cases that must be rejected by the validators.

## Files

- `lab/om_lab/matched_instances.py` — generators, validators, parity checks,
  witness validation, deterministic matched permutations, min-fill width probe,
  and PySAT effort probe.
- `lab/tests/test_matched_instances.py` — pytest suite for positive and negative
  cases.
- `docs/phase4/STRUCTURAL_COUNTEREXAMPLES.md` — this document.

## Matched construction

For a connected simple 3-regular graph `G = (V, E)`:

- The even instance has charge vector `b = 0`.
- The odd instance has the same graph and edge identifiers, but flips one
  vertex charge: `b' = b + e_v`.
- Both instances use the strict 3-CNF encoding of
  `XOR_{e incident to v} x_e = b(v)` at every vertex.
- The unsigned graph representation and edge identifiers are asserted equal
  inside `generate_matched_tseitin_pair`.

The connected comparison registry contains K4, K3,3, the triangular prism,
a small Möbius ladder, and the Petersen graph.

## Parity criterion and claim levels

For a connected graph, the system is satisfiable over GF(2) iff the total
charge is even. This is **Proved** by the standard incidence argument: summing
all vertex equations counts every edge variable twice.

For a disconnected graph, the same argument applies separately to every
component. An even total charge is not sufficient. This is also **Proved**, and
the negative test
`test_disconnected_even_total_charge_can_be_component_odd_and_unsat`
constructs two K4 components, each with odd charge, so the total charge is even
but the formula is UNSAT.

The all-zero assignment is a witness for the all-zero connected even instance.
This is **Proved** by construction and is independently checked clause-by-clause
and vertex-by-vertex by `validate_all_zero_witness`.

The balanced occurrence claim — every edge variable occurs in four positive and
four negative literals — is **Proved** by counting for cubic XOR3 encodings and
is also checked by pytest.

## Width estimates and solver effort

`min_fill_width_estimate` is a deterministic min-fill elimination heuristic on
the primal graph of the CNF. It is **Empirical Observation** only. It is not
exact treewidth, and different deterministic permutations may change the
heuristic estimate even when the underlying graph is isomorphic.

`solver_effort` runs PySAT `cd195` on an instance and records decisions,
propagations, and elapsed time. These records are **Empirical Observation** only.
They are not evidence of a worst-case separation.

## Negative cases

The suite actively checks rejection of:

- disconnected graphs where the caller incorrectly requires connectivity;
- even total charge with odd per-component charge;
- duplicate edges;
- self-loops;
- non-cubic graphs;
- repeated edge identifiers;
- malformed XOR3 encodings;
- incorrect charge metadata.

Rejection is a code contract checked by pytest. It is not a new mathematical
result.

## What this suite does not claim

- It does not claim a new lower bound.
- It does not claim that min-fill width is stable under permutation.
- It does not claim that solver decision counts prove anything about worst-case
  complexity.
- It does not replace the parity proof; it only exercises the implementation.
