# Phase 1 Literature Map (Verified Primary Citations)

> **Citation policy:** Every reference below has been verified against primary records or authoritative mathematical bibliographies. Unverified citations are forbidden under [`docs/RULES.md`](../RULES.md).

---

## 1. Official Millennium Problem Statement

- **Stephen A. Cook**, *"The P versus NP Problem"*, Clay Mathematics Institute (official problem description, 2000; published in *The Millennium Prize Problems*, J. Carlson, A. Jaffe, and A. Wiles, eds., Clay Mathematics Institute and American Mathematical Society, 2006).
  - Primary PDF: https://www.claymath.org/wp-content/uploads/2022/06/pvsnp.pdf
  - **Core content:** Defines deterministic polynomial-time languages ($\mathbf{P}$) and polynomial-time checkable relations ($\mathbf{NP}$) via Turing machines: $L \in \mathbf{NP}$ iff there exist $k \in \mathbb{N}$ and a polynomial-time checking relation $R$ such that $w \in L \iff \exists y\,(|y| \le |w|^k \land R(w, y))$. Notes that $\mathbf{P} \subseteq \mathbf{NP}$ is immediate and the question is whether $\mathbf{P} = \mathbf{NP}$, equivalent to whether $\text{SAT} \in \mathbf{P}$.

---

## 2. Foundations of NP-Completeness

### Cook–Levin Theorem
- **Stephen A. Cook**, *"The Complexity of Theorem-Proving Procedures"*, *Proceedings of the Third Annual ACM Symposium on Theory of Computing (STOC '71)*, pp. 151–158, 1971. DOI: `10.1145/800157.805047`.
  - **Significance:** Introduced NP-completeness (originally via polynomial-time Turing reductions / Cook reductions) and proved that propositional tautologyhood (equivalently satisfiability, SAT, and 3-SAT) captures every problem solvable in nondeterministic polynomial time.
- **Leonid A. Levin**, *"Universal Sequential Search Problems"* (*Universal'nye zadachi perebora*), *Problemy Peredachi Informatsii* (*Problems of Information Transmission*), 9(3):115–116 (English translation pp. 265–266), 1973.
  - **Significance:** Independently discovered universal search problems (*perebor*) in the Soviet Union, establishing completeness for several search problems including tiling and formula satisfiability variants.

### Karp's 21 NP-Complete Problems
- **Richard M. Karp**, *"Reducibility Among Combinatorial Problems"*, in *Complexity of Computer Computations* (R. E. Miller and J. W. Thatcher, eds.), Plenum Press, pp. 85–103, 1972.
  - **Significance:** Formalized polynomial-time many-one reductions (Karp reductions) and proved 21 classic combinatorial problems—including 3-SAT, Clique, Vertex Cover, Chromatic Number ($k$-Coloring), Set Cover, Directed/Undirected Hamilton Circuit, Partition, Knapsack, and Max-Cut—are NP-complete, demonstrating that the P vs NP question sits at the center of combinatorics, graph theory, and optimization.
- **Michael R. Garey and David S. Johnson**, *Computers and Intractability: A Guide to the Theory of NP-Completeness*, W. H. Freeman, 1979.
  - **Significance:** Standard compendium of NP-completeness reductions and problem classifications.

---

## 3. The Three Major Barriers

Any proposed proof of $\mathbf{P} \neq \mathbf{NP}$ (or $\mathbf{P} = \mathbf{NP}$) must explain how it avoids **all three** established mathematical barriers:

### Barrier 1: Relativization (1975)
- **Theodore P. Baker, John Gill, and Robert Solovay**, *"Relativizations of the $\mathcal{P} = ?\mathcal{NP}$ Question"*, *SIAM Journal on Computing*, 4(4):431–442, 1975. DOI: `10.1137/0204037`.
  - **Result:** Constructed oracles $A$ and $B$ such that $\mathbf{P}^A = \mathbf{NP}^A$ (e.g., any PSPACE-complete oracle) and $\mathbf{P}^B \neq \mathbf{NP}^B$.
  - **Implication:** Any proof technique that remains valid when all Turing machines are given access to an arbitrary black-box oracle (such as standard diagonalization and simulation arguments) **cannot** resolve $\mathbf{P}$ vs $\mathbf{NP}$.

### Barrier 2: Natural Proofs (1997)
- **Alexander A. Razborov and Steven Rudich**, *"Natural Proofs"*, *Journal of Computer and System Sciences*, 55(1):24–35, 1997 (preliminary version in *STOC '94*). DOI: `10.1006/jcss.1997.1494`.
  - **Result:** Formalized "natural" combinatorial properties of Boolean functions—properties that are *constructive* (decidable in polynomial time in the truth-table size $2^n$) and *large* (hold for a non-negligible fraction of all $n$-bit Boolean functions)—and proved that any such property useful for proving superpolynomial general circuit lower bounds would yield a subexponential-time distinguisher breaking standard pseudorandom function generators.
  - **Implication:** Assuming strong one-way functions / pseudorandom functions exist, "natural" combinatorial circuit lower-bound arguments cannot separate $\mathbf{NP}$ from $\mathbf{P/poly}$.

### Barrier 3: Algebrization (2008 / 2009)
- **Scott Aaronson and Avi Wigderson**, *"Algebrization: A New Barrier in Complexity Theory"*, *ACM Transactions on Computation Theory (TOCT)*, 1(1):2:1–2:54, 2009 (conference version in *STOC '08*, 2008). DOI: `10.1145/1490270.1490272`.
  - **Result:** Extended relativization to algebraic extensions: even when non-relativizing arithmetization techniques are allowed (which overcame relativization to prove $\mathbf{IP} = \mathbf{PSPACE}$ and $\mathbf{MIP} = \mathbf{NEXP}$), all such "algebrizing" techniques remain unable to prove $\mathbf{P} \neq \mathbf{NP}$, $\mathbf{P} = \mathbf{NP}$, or $\mathbf{NEXP} \not\subseteq \mathbf{P/poly}$.
  - **Implication:** A resolution of $\mathbf{P}$ vs $\mathbf{NP}$ requires **non-algebrizing** techniques that use finer structure of computation than black-box oracles or low-degree polynomial extensions.

---

## 4. Major Active & Historical Programs Beyond the Barriers

### Circuit Lower Bounds via Algorithms (Williams's Program)
- **Ryan Williams**, *"Nonuniform ACC Circuit Lower Bounds"*, *Journal of the ACM (JACM)*, 61(1):2:1–2:32, 2014 (conference version in *CCC 2011*, 2011). DOI: `10.1145/2559903`.
  - **Result:** Proved $\mathbf{NEXP} \not\subseteq \mathbf{ACC}^0$ (non-deterministic exponential time cannot be computed by polynomial-size constant-depth circuits with AND, OR, NOT, and $\text{MOD}_m$ gates).
  - **Why it matters:** Connects *algorithmic* satisfiability speedups (slightly faster than $2^n$ brute force for $\text{ACC}^0$ circuits) to *circuit lower bounds*, bypassing Relativization, Natural Proofs, and Algebrization simultaneously—though still far from separating $\mathbf{NP}$ from $\mathbf{P/poly}$.

### Geometric Complexity Theory (GCT)
- **Ketan D. Mulmuley and Milind Sohoni**, *"Geometric Complexity Theory I: An Approach to the P vs. NP and Related Problems"*, *SIAM Journal on Computing*, 31(2):496–526, 2001. DOI: `10.1137/S009753970038715X`.
  - **Approach:** Formulates algebraic analogues of $\mathbf{P}$ vs $\mathbf{NP}$ (Valiant's $\mathbf{VP}$ vs $\mathbf{VNP}$, separating the permanent from the determinant) in terms of algebraic geometry and representation-theoretic orbit-closure obstructions.
- **Peter Bürgisser, Christian Ikenmeyer, and Greta Panova**, *"No Occurrence Obstructions in Geometric Complexity Theory"*, *Journal of the American Mathematical Society*, 32:163–193, 2019. DOI: `10.1090/jams/908`.
  - **Reality check:** Proved that the simplest class of representation-theoretic obstructions ("occurrence obstructions") cannot separate permanent from determinant in the required regime; multi-multiplicity obstructions remain open and deeply challenging.

### Proof Complexity
- **Stephen A. Cook and Robert A. Reckhow**, *"The Relative Efficiency of Propositional Proof Systems"*, *Journal of Symbolic Logic*, 44(1):36–50, 1979. DOI: `10.2307/2273702`.
  - **Result:** Defined propositional proof systems generally and proved that $\mathbf{NP} = \mathbf{coNP}$ (a prerequisite for $\mathbf{P} = \mathbf{NP}$) holds if and only if there exists a *polynomially bounded* propositional proof system (one in which every tautology has a polynomial-size proof).
- **Armin Haken**, *"The Intractability of Resolution"*, *Theoretical Computer Science*, 39(2–3):297–308, 1985.
  - **Result:** Proved exponential lower bounds on resolution proof length for the propositional pigeonhole principle ($\text{PHP}_n^{n+1}$), establishing the foundational technique for proof-system lower bounds (relevant directly to DPLL/CDCL SAT solvers).

---

## 5. Empirical Hardness & Phase Transitions (Phase 2 Foundation)

- **David G. M. Mitchell, Bart Selman, and Hector J. Levesque**, *"Hard and Easy Distributions of SAT Problems"*, *Proceedings of the Tenth National Conference on Artificial Intelligence (AAAI-92)*, pp. 459–465, 1992.
  - **Result:** Characterized the sharp satisfiability phase transition for random $k$-SAT (for $3$-SAT, concentrated near clause-to-variable ratio $\alpha = m/n \approx 4.26$), showing that typical hard instances for DPLL-style search cluster around this threshold while under-constrained and heavily over-constrained instances are empirically easier.
  - **Caveat (Honesty Rule):** Average-case or random-instance phase transitions do **not** directly establish worst-case complexity separations, but provide an indispensable controlled laboratory for studying solver behavior and proof-search dynamics.

<!-- Phase 1 audit additions contributed by Gemini (literature lane), appended verbatim from Gemini's Operation Millennium chat, 2026-11-25. -->

---

## Seminal Follow-Ups & Modern Frontiers (Phase 1 Audit Additions)

### 1. Ryan Williams Extensions (Tightening $\mathrm{NEXP}$ to $\mathrm{NQP}$)
* **Murray & Williams (2018 / 2020) `[Proved]`:** Extended the Easy Witness Lemma from $\mathrm{NEXP}$ down to nondeterministic quasi-polynomial time ($\mathrm{NQP} = \mathrm{NTIME}[n^{\log^{O(1)} n}]$), proving that for every fixed $k$, $\mathrm{NQP}$ does not have $n^{\log^k n}$-size $\mathrm{ACC}^0 \circ \mathrm{THR}$ circuits.
  * *Citation:* Cody D. Murray and R. Ryan Williams, "Circuit Lower Bounds for Nondeterministic Quasi-Polytime from a New Easy Witness Lemma," *SIAM Journal on Computing*, Vol. 49, Issue 5, pp. STOC18-300–STOC18-322, 2020 (preliminary version: *STOC 2018*, pp. 890–901, DOI: `10.1145/3188745.3188910`). Journal DOI: `10.1137/18M1195887`

### 2. Razborov–Rudich Follow-Ups (Natural Proofs & Learning)
* **Carmosino, Impagliazzo, Kabanets, & Kolokolova (2016) `[Proved]`:** Proved that any Razborov–Rudich natural proof of a circuit lower bound against a sufficiently powerful circuit class (e.g., containing $\mathrm{AC}^0[p]$) yields a generic randomized learning/compression algorithm for that same circuit class—yielding a quasi-polynomial-time learning algorithm for $\mathrm{AC}^0[p]$.
  * *Citation:* Marco L. Carmosino, Russell Impagliazzo, Valentine Kabanets, and Antonina Kolokolova, "Learning Algorithms from Natural Proofs," *31st Conference on Computational Complexity (CCC 2016)*, LIPIcs Vol. 50, pp. 10:1–10:24, 2016. DOI: `10.4230/LIPIcs.CCC.2016.10`

### 3. Hardness vs. Randomness (Derandomization)
* **Impagliazzo & Wigderson (1997) `[Proved]`:** Established that if $\mathrm{E} = \mathrm{DTIME}[2^{O(n)}]$ contains a language requiring Boolean circuits of size $2^{\Omega(n)}$, then $\mathrm{P} = \mathrm{BPP}$. This bridges circuit lower bounds directly to derandomization.
  * *Citation:* Russell Impagliazzo and Avi Wigderson, "$\mathrm{P} = \mathrm{BPP}$ if $\mathrm{E}$ Requires Exponential Circuits: Derandomizing the XOR Lemma," *Proceedings of the Twenty-Ninth Annual ACM Symposium on Theory of Computing (STOC '97)*, pp. 220–229, 1997. DOI: `10.1145/258533.258590`

### 4. Meta-Complexity (MCSP & Time-Bounded Kolmogorov Complexity)
* **Kabanets & Cai (2000) `[Proved]`:** Initiated the modern study of the Minimum Circuit Size Problem (`MCSP`), showing that $\mathrm{MCSP} \in \mathrm{P}$ implies no one-way functions exist, and that proving $\mathrm{NP}$-hardness of `MCSP` via natural reductions would imply major circuit lower bounds.
  * *Citation:* Valentine Kabanets and Jin-Yi Cai, "Circuit Minimization Problem," *Proceedings of the Thirty-Second Annual ACM Symposium on Theory of Computing (STOC 2000)*, pp. 73–79, 2000.
* **Hirahara (2018 / 2023) `[Proved]`:** Presented the first **non-black-box** worst-case to average-case reductions within $\mathrm{NP}$ (from approximation versions of time-bounded Kolmogorov complexity $\mathrm{MINKT}$ to $\mathrm{DistNP}$), bypassing black-box reduction barriers toward excluding Impagliazzo's *Heuristica*.
  * *Citation:* Shuichi Hirahara, "Non-Black-Box Worst-Case to Average-Case Reductions Within $\mathrm{NP}$," *SIAM Journal on Computing*, Vol. 52, Issue 6, 2023 (preliminary version: *FOCS 2018*, pp. 247–258, DOI: `10.1109/FOCS.2018.00032`). Journal DOI: `10.1137/19M124705X`
* **Liu & Pass (2020) `[Proved]`:** Proved an unconditional equivalence between the existence of one-way functions and the mild average-case hardness of $t$-time-bounded Kolmogorov complexity ($K^t$), characterizing symmetric-key cryptography via a natural meta-complexity problem.
  * *Citation:* Yanyi Liu and Rafael Pass, "On One-Way Functions and Kolmogorov Complexity," *2020 IEEE 61st Annual Symposium on Foundations of Computer Science (FOCS 2020)*, pp. 1243–1254, 2020. DOI: `10.1109/FOCS46700.2020.00118`
