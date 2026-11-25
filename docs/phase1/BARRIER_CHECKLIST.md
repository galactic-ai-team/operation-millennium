# Barrier Checklist (Phases 3 & 4)

Every proposed proof strategy, lower-bound argument, or separation conjecture in Operation Millennium must answer all three barrier checks below before advancing past Phase 3.

## 1. Relativization Check (Baker–Gill–Solovay 1975)
- [ ] Does the argument still go through if every Turing machine / algorithm in the proof is replaced by an oracle machine $M^A$ for an arbitrary oracle $A \subseteq \{0,1\}^*$?
- [ ] **If YES:** The argument relativizes and **cannot** prove $\mathbf{P} \neq \mathbf{NP}$ or $\mathbf{P} = \mathbf{NP}$. Identify the exact non-relativizing step (e.g., gate-by-gate inspection of circuits, arithmetization, diagonalization against uniform code size) or reject the approach.

## 2. Natural Proofs Check (Razborov–Rudich 1997)
Applies to any circuit lower bound or Boolean-function hardness argument:
- [ ] **Constructivity:** Can the distinguishing property of hard functions be decided in polynomial time in the truth-table size $2^n$ (i.e., $2^{O(n)}$)?
- [ ] **Largeness:** Does the property hold for at least a $2^{-O(n)}$ fraction of all $n$-variable Boolean functions?
- [ ] **Usefulness:** Does holding the property imply superpolynomial circuit lower bounds?
- [ ] **If all three hold:** Under standard cryptographic assumptions (existence of pseudorandom functions), the proof is barred. Explain which condition fails (e.g., non-constructivity or non-largeness like a uniform diagonalization / algorithmic connection) or reject the approach.

## 3. Algebrization Check (Aaronson–Wigderson 2009)
- [ ] Does the argument still go through when machines are given oracle access both to $A$ and to a low-degree polynomial extension $\widetilde{A}$ over a finite field/ring?
- [ ] **If YES:** Standard arithmetization alone cannot resolve $\mathbf{P}$ vs $\mathbf{NP}$ or $\mathbf{NEXP} \not\subseteq \mathbf{P/poly}$. Identify what non-algebrizing ingredient is used (e.g., non-black-box circuit evaluation as in Williams's $\text{NEXP} \not\subseteq \mathbf{ACC}^0$ proof).

## 4. Complexity Leakage & Scope Check
- [ ] For any alleged fast algorithm or reduction: is running time polynomial in the **bit-length** of the input (not unary value, not exponential hidden tables, not exponential precision)?
- [ ] Claim level explicitly labeled per [`docs/RULES.md`](../RULES.md)?
