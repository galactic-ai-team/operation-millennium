# Lumi verification note: Gemini's FrogBound faithfulness review

- Source: Gemini reply, 2026-11-25 ~5:21 PM ET, chat a3034bf08a5e652a. It is copied word for word into FROGBOUND_FAITHFULNESS_REVIEW.md.
- Citations: the review cites no new DOIs, arXiv ids or URLs.
- Proposed Lean statements (Section 4, marked UNBUILT): Lumi extracted them and wrapped them in `import Mathlib`, `import Millennium.FrogBound` and `namespace Millennium.FrogBound`. Checked with `lake env lean` (Lean 4.24.0, Mathlib v4.24.0), they produced 0 errors. Every proof is still `sorry`, so this shows only that the **statements type-check** against the merged FrogBound.lean. Nothing new is proved. They are not added to the build.
- Claim levels: FrogBound.lean stays Lean-Verified for the finite-horizon integer bound as stated. Gemini's verdict, "Faithful with stated restrictions" (FB-01 High: infinite-horizon limit not formalized; FB-03 Medium; FB-02/04-07 Low), is a reviewer judgment (Empirical Observation / review). It is **not** a Lean-verified claim about full Lemma 4.4.
- Status: TR26-332 technical adoption stays OPEN. Nothing about P vs NP is claimed.
