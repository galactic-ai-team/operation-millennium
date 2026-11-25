# Operation Millennium Rules & Proof Standards

These rules govern every document, experiment, pull request, and agent message in Operation Millennium.

---

## 1. The Honesty Rule

**No agent may declare or imply a breakthrough without a rigorous proof.**

- Solving 1,000,000 test instances in polynomial-looking wall-clock time **is not a proof** of P = NP, nor of a worst-case polynomial bound.
- Failing to find a fast algorithm on benchmark instances **is not a proof** of P ≠ NP.
- Heuristic speedups, neural approximations, or average-case successes do not establish worst-case complexity separations.
- Negative results (disproved conjectures, broken heuristics, barrier hits) are valuable scientific outputs and must be recorded honestly rather than hidden.

---

## 2. Claim Levels

Every mathematical or empirical statement in docs, PRs, and packet updates must declare one of four claim levels:

| Level | Meaning | Required Evidence | Forbidden Language |
|---|---|---|---|
| **Conjecture** | Untested or unproved hypothesis / intuition | Clear statement of quantifiers, domain, and proposed falsification test | "Proved", "Solves", "Shows that" |
| **Empirical Observation** | Measured behavior on finite seeds/instances | Reproducible script, seed list, JSONL logs, solver version, independent witness verification | "Always", "For all $n$", "Polynomial time in general" |
| **Proved** | Complete, step-by-step mathematical proof checked by human/team review | Full proof with explicit definitions, lemmas, edge cases, and completed Barrier Checklist | Claiming machine-verification if not in Lean |
| **Lean-Verified** | Machine-checked proof in Lean 4 + Mathlib | Compiles cleanly with `lake build`, zero `sorry`, `#print axioms` shows only standard Lean axioms (`propext`, `Classical.choice`, `Quot.sound`) | Hiding assumptions inside custom `axiom` declarations |

---

## 3. Adversarial Review Protocol

Before any **Conjecture** is promoted or any **Proved** claim is merged into `dev`:

1. **Counterexample Attempt (Dee + Lab):** Stress-test against planted hard instances, adversarial edge cases (empty formula, unit clauses, high-ratio UNSAT, symmetric structures), and scaling beyond small $n$.
2. **Complexity Leakage Audit (Claude + Ace):** Check whether an alleged polynomial-time algorithm hides exponential blowup in:
   - number representation (bit-length vs unary value),
   - preprocessing / compilation / lookup tables,
   - exponential branching hidden inside subroutine calls or precision requirements.
3. **Barrier Audit (Ace + Gemini):** Run `docs/phase1/BARRIER_CHECKLIST.md` to determine whether the argument relativizes, is a natural proof, or algebrizes. If it falls inside a barrier, explain explicitly how it could possibly work—or reject the approach.
4. **Independent Verification (Lumi):** Re-run code/proofs cleanly from scratch on an uncached commit.

---

## 4. Citation & Literature Integrity

- **Real citations only.** Never invent, guess, or extrapolate paper titles, authors, years, venues, page numbers, or DOIs.
- Every citation added to `docs/phase1/` must be verified against a primary source, publisher record, or authoritative archive.
- If a detail is uncertain, verify first or omit it until verified.

---

## 5. Free Resources, Secrets & Git Hygiene

- **Free resources only:** Use open-source libraries (PySAT, NumPy, Matplotlib, pytest, Lean 4, Mathlib) and free CI/compute tiers. Never incur paid API or cloud charges.
- **No secrets:** Never commit, log, or paste API keys, tokens, passwords, cookies, or private credentials anywhere in git history, CI logs, or agent packets.
- **Branching:**
  - Open PRs against `dev`.
  - Merging into `dev` is permitted once checks and review pass.
  - **Never merge into `main` without Research Director Stephon's explicit approval.**
- **Scope isolation:** Do not modify unrelated repositories (`wgif`, `playground-lm`, etc.) from this project.
