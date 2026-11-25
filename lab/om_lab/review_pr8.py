"""Adversarial review harness for Dee's PR #8 (``om_lab.matched_instances``).

Claude, Phase 4 Adversarial Review 01, ``docs/phase4/ADVERSARIAL_REVIEW_01.md``
Section 6.1. Attacked code: ``lab/om_lab/matched_instances.py`` at the PR #8
merge commit ``c8e61a7``, byte-identical at ``dev`` ``f398de6``. The review is
``docs/phase4/reviews/REVIEW_PR8_CLAUDE.md``.

Independence
------------
* Graphs are rebuilt here from their definitions and compared with Dee's
  constructors. Dee's constructors are not trusted.
* Satisfiability is decided by :mod:`om_lab.parity_oracle`, using GF(2)
  elimination over equations derived from endpoints and charges, and by a
  SAT solver run to completion (CaDiCaL ``cd195``). Dee's component-parity
  function ``is_parity_satisfiable`` is only ever a value being compared,
  never a reference.
* Each CNF is decoded back into XOR constraints from its clauses alone and
  compared with the system implied by the declared graph, charges and edge
  map.

Every number this module produces is **[Claim Level: Empirical
Observation]** on the finite graphs, charge vectors and seeds listed here.

CLI (from ``lab/``)::

    python -m om_lab.review_pr8 --out-dir /tmp/review_pr8
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field, replace
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import statistics
import sys
from typing import Callable, Iterable, Sequence

import om_lab.matched_instances as mi
from om_lab.parity_oracle import (
    check_refutation,
    check_witness,
    decode_xor_cnf,
    edge_witness_to_model,
    expected_constraints,
    model_to_edge_witness,
    solve_decoded,
    tseitin_oracle,
)
from om_lab.solvers import Status, solve_dpll, solve_pysat, verify_cnf_assignment
from om_lab.width_features import primal_min_fill_width

ATTACKED_COMMIT = "c8e61a7"  # PR #8 merge commit; target files unchanged at dev f398de6
GATE_B_PR24_COMMIT = "98d5208"  # PR #24 final Gate B check (first pass attacked Dee's repair at 03b626d)
REGISTERED_MOEBIUS_VERTEX_COUNTS = (4, 6, 8, 10, 12, 16, 20, 24, 32)  # DISCOVERY_ROUND_01 s5.4
REGISTERED_PERMUTATION_SEEDS = tuple(range(100, 120))  # ADVERSARIAL_REVIEW_01 A2
PERMUTATION_SUITE_BUDGET = 10_000  # project branch budget (OM-C001-R2 B), used for Y_j in A6
SEED_SUITE_SEEDS = tuple(range(32))
SEED_SUITE_PREFIX = "OM-P4-R8"


# ---------------------------------------------------------------------------
# Independent graph constructors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Graph:
    name: str
    n: int
    edges: tuple[tuple[int, int], ...]  # canonical (u < v), sorted

    def to_dee(self) -> mi.SimpleGraph:
        return mi.SimpleGraph(self.n, self.edges)


def _graph(name: str, n: int, edges: Iterable[tuple[int, int]]) -> Graph:
    canon = sorted({(min(u, v), max(u, v)) for u, v in edges})
    return Graph(name, n, tuple(canon))


def g_k4() -> Graph:
    return _graph("K4", 4, itertools.combinations(range(4), 2))


def g_k33() -> Graph:
    return _graph("K3,3", 6, ((i, 3 + j) for i in range(3) for j in range(3)))


def g_prism(k: int) -> Graph:
    """Two k-cycles 0..k-1 and k..2k-1 joined by the rungs (i, k+i)."""
    edges = [(i, (i + 1) % k) for i in range(k)] + [(k + i, k + (i + 1) % k) for i in range(k)]
    edges += [(i, k + i) for i in range(k)]
    return _graph(f"prism{k}", 2 * k, edges)


def g_moebius(k: int) -> Graph:
    """Moebius ladder on 2k vertices: 2k-cycle plus chords (i, i+k); k >= 2 (k=2 is K4)."""
    n = 2 * k
    edges = [(i, (i + 1) % n) for i in range(n)] + [(i, i + k) for i in range(k)]
    return _graph(f"moebius{n}v", n, edges)


def g_petersen() -> Graph:
    """Generalised Petersen graph GP(5, 2): outer 5-cycle, spokes, inner pentagram."""
    edges = [(i, (i + 1) % 5) for i in range(5)] + [(i, i + 5) for i in range(5)]
    edges += [(5 + i, 5 + (i + 2) % 5) for i in range(5)]
    return _graph("petersen", 10, edges)


def g_union(*graphs: Graph) -> Graph:
    offset = 0
    edges: list[tuple[int, int]] = []
    for g in graphs:
        edges.extend((u + offset, v + offset) for u, v in g.edges)
        offset += g.n
    return _graph("+".join(g.name for g in graphs), offset, edges)


def components_of(n: int, edges: Sequence[tuple[int, int]]) -> list[frozenset[int]]:
    adj: list[list[int]] = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = [False] * n
    out = []
    for s in range(n):
        if seen[s]:
            continue
        seen[s] = True
        comp, queue = {s}, [s]
        while queue:
            x = queue.pop()
            for y in adj[x]:
                if not seen[y]:
                    seen[y] = True
                    comp.add(y)
                    queue.append(y)
        out.append(frozenset(comp))
    return out


def girth(g: Graph) -> float:
    """Length of a shortest cycle (BFS from every vertex)."""
    adj: list[list[int]] = [[] for _ in range(g.n)]
    for u, v in g.edges:
        adj[u].append(v)
        adj[v].append(u)
    best = math.inf
    for s in range(g.n):
        dist = {s: 0}
        parent = {s: -1}
        queue = [s]
        for x in queue:
            for y in adj[x]:
                if y not in dist:
                    dist[y] = dist[x] + 1
                    parent[y] = x
                    queue.append(y)
                elif parent[x] != y:
                    best = min(best, dist[x] + dist[y] + 1)
    return best


def exhaustive_graphs() -> list[Graph]:
    """Cubic graphs with at most 10 vertices: every charge vector is enumerated."""
    return [
        g_k4(), g_k33(), g_prism(3), g_moebius(2), g_moebius(3), g_moebius(4), g_moebius(5),
        g_prism(4), g_prism(5), g_petersen(),
        g_union(g_k4(), g_k4()), g_union(g_k4(), g_k33()), g_union(g_k4(), g_prism(3)),
    ]


def seed_suite_graphs() -> list[Graph]:
    """Larger graphs, checked on a fixed documented set of charge vectors."""
    return [
        g_moebius(6), g_moebius(8), g_moebius(10), g_moebius(12), g_moebius(16),
        g_prism(6), g_prism(8),
        g_union(g_k4(), g_k4(), g_k4()), g_union(g_k4(), g_petersen()),
        g_union(g_petersen(), g_petersen()), g_union(g_petersen(), g_moebius(3)),
    ]


def seed_suite_charge_vectors(g: Graph) -> list[tuple[str, tuple[int, ...]]]:
    """Documented charge vectors for one larger graph.

    zero; every single-vertex charge; one charge in each of the first two
    components (if any); two charges inside component 0; and 32 vectors with
    independent fair bits from ``random.Random(f"OM-P4-R8|{name}|{seed}")``,
    seeds 0-31 (string seeding is deterministic across runs).
    """
    out = [("zero", tuple([0] * g.n))]
    for v in range(g.n):
        out.append((f"single:{v}", tuple(int(u == v) for u in range(g.n))))
    comps = sorted((sorted(c) for c in components_of(g.n, g.edges)), key=lambda c: c[0])
    if len(comps) >= 2:
        a, b = comps[0][0], comps[1][0]
        out.append(("one-per-component", tuple(int(u in (a, b)) for u in range(g.n))))
    first = comps[0]
    out.append(("two-in-component-0", tuple(int(u in first[:2]) for u in range(g.n))))
    for seed in SEED_SUITE_SEEDS:
        rng = random.Random(f"{SEED_SUITE_PREFIX}|{g.name}|{seed}")
        out.append((f"seed:{seed}", tuple(rng.getrandbits(1) for _ in range(g.n))))
    return out


def edge_id_variants(g: Graph) -> dict[str, tuple[int, ...]]:
    """Legitimate edge-id maps: default, a shuffled bijection, sparse ids."""
    m = len(g.edges)
    shuffled = list(range(1, m + 1))
    random.Random(f"{SEED_SUITE_PREFIX}|ids|{g.name}").shuffle(shuffled)
    return {
        "default": tuple(range(1, m + 1)),
        "shuffled": tuple(shuffled),
        "sparse": tuple(3 * i + 7 for i in range(m)),
    }


# ---------------------------------------------------------------------------
# Legitimate-instance comparison
# ---------------------------------------------------------------------------


def check_instance(inst: mi.TseitinInstance, *, dpll: bool = False) -> dict:
    """Compare oracle, decoded CNF, SAT solver(s), Dee's label and witnesses."""
    n = inst.graph.n_vertices
    edges = inst.graph.edges
    charges = inst.charges
    edge_vars = inst.edge_ids
    clauses = [list(c) for c in inst.clauses]
    problems: list[str] = []

    oracle = tseitin_oracle(n, edges, charges)
    decoded = decode_xor_cnf(inst.clauses)
    expected = sorted(expected_constraints(n, edges, charges, edge_vars))
    got = sorted((c.variables, c.rhs) for c in decoded.constraints)
    encoding_matches = decoded.exact and got == expected
    if not encoding_matches:
        problems.append("clauses do not encode the declared graph/charges/edge map")
    decoded_consistent = solve_decoded(decoded)[0]

    reference = solve_pysat(inst.n_vars, clauses)
    dee_sat = mi.is_parity_satisfiable(inst)
    statuses = {
        "oracle": oracle.consistent,
        "decoded_cnf": decoded_consistent,
        "pysat": reference.satisfiable,
        "dee_component_parity": dee_sat,
    }
    if dpll:
        statuses["dpll"] = solve_dpll(inst.n_vars, clauses).satisfiable
    if len(set(statuses.values())) != 1:
        problems.append(f"status disagreement {statuses}")

    if oracle.consistent:
        if not check_witness(n, edges, charges, oracle.witness):
            problems.append("oracle witness fails its own check")
        model = edge_witness_to_model(oracle.witness, edge_vars, inst.n_vars)
        if not verify_cnf_assignment(clauses, model):
            problems.append("oracle witness does not satisfy the CNF")
        if not mi.validate_tseitin_assignment(inst, {abs(l): l > 0 for l in model}):
            problems.append("Dee's validator rejects the oracle witness")
    else:
        chosen = set(oracle.refutation)
        if not check_refutation(n, edges, charges, chosen):
            problems.append("oracle refutation fails its check")
        comps = components_of(n, edges)
        if not all(c <= chosen or not (c & chosen) for c in comps):
            problems.append("refutation is not a union of components")
        if not mi.parity_obstruction(inst):
            problems.append("Dee reports no obstruction for an inconsistent system")
    if reference.satisfiable:
        witness = model_to_edge_witness(reference.model, edge_vars)
        if not check_witness(n, edges, charges, witness):
            problems.append("SAT model violates a vertex parity equation")
        if not mi.validate_tseitin_assignment(inst, {abs(l): l > 0 for l in reference.model}):
            problems.append("Dee's validator rejects the SAT model")
    return {"sat": oracle.consistent, "statuses": statuses, "encoding_matches": encoding_matches, "problems": problems}


def sweep(graphs: Sequence[Graph], charges_for: Callable[[Graph], Iterable[tuple[str, tuple[int, ...]]]],
          *, id_variants: Sequence[str] = ("default",), dpll: bool = False) -> dict:
    """Encode with Dee's encoder and check every (graph, charges, edge map) instance."""
    per_graph = {}
    mismatches = []
    total = 0
    for g in graphs:
        dee_graph = g.to_dee()
        counts = Counter()
        for label, ids in edge_id_variants(g).items():
            if label not in id_variants:
                continue
            for vec_label, charges in charges_for(g):
                inst = mi.encode_tseitin(dee_graph, charges, edge_ids=ids)
                result = check_instance(inst, dpll=dpll)
                counts["SAT" if result["sat"] else "UNSAT"] += 1
                total += 1
                if result["problems"]:
                    mismatches.append({"graph": g.name, "edge_ids": label, "charges": vec_label,
                                       "charge_vector": charges, "problems": result["problems"]})
        per_graph[g.name] = {"n_vertices": g.n, "n_edges": len(g.edges), **dict(counts)}
    return {"instances": total, "mismatches": mismatches, "per_graph": per_graph}


def all_charge_vectors(g: Graph) -> Iterable[tuple[str, tuple[int, ...]]]:
    for bits in itertools.product((0, 1), repeat=g.n):
        yield "".join(map(str, bits)), bits


def check_dee_constructors() -> dict:
    """Dee's graph constructors against the definitions rebuilt here."""
    results = {
        "k4": mi.k4().edges == g_k4().edges,
        "k33": mi.k33().edges == g_k33().edges,
        "prism3": mi.prism_graph(3).edges == g_prism(3).edges,
        "petersen_edges_equal_GP(5,2)": mi.petersen_graph().edges == g_petersen().edges,
        "petersen_girth_5": girth(g_petersen()) == 5,
        "two_k4": mi.disconnected_two_k4().edges == g_union(g_k4(), g_k4()).edges,
    }
    for k in range(3, 17):
        results[f"moebius_ladder({k})"] = mi.moebius_ladder(k).edges == g_moebius(k).edges
    try:
        mi.moebius_ladder(2)
        results["moebius_ladder(2) (registered 4-vertex ladder)"] = True
    except ValueError:
        results["moebius_ladder(2) (registered 4-vertex ladder)"] = False
    return results


# ---------------------------------------------------------------------------
# A3 signatures
# ---------------------------------------------------------------------------


def primal_signature(n_vars: int, clauses: Sequence[Sequence[int]]) -> tuple:
    edges = set()
    for clause in clauses:
        vs = sorted({abs(lit) for lit in clause})
        edges.update(itertools.combinations(vs, 2))
    return (tuple(range(1, n_vars + 1)), tuple(sorted(edges)))


def incidence_signature(n_vars: int, clauses: Sequence[Sequence[int]]) -> tuple:
    inc = sorted((abs(lit), pos) for pos, clause in enumerate(clauses) for lit in clause)
    return (tuple(range(1, n_vars + 1)), len(clauses), tuple(inc))


def occurrence_profile(n_vars: int, clauses: Sequence[Sequence[int]]) -> tuple:
    pos = Counter(lit for c in clauses for lit in c if lit > 0)
    neg = Counter(-lit for c in clauses for lit in c if lit < 0)
    return tuple((v, pos[v], neg[v]) for v in range(1, n_vars + 1))


def a3_report(n1: int, c1: Sequence[Sequence[int]], n2: int, c2: Sequence[Sequence[int]]) -> dict:
    """Every A3 requirement for exact labelled equality of two formulas."""
    return {
        "primal_signature": primal_signature(n1, c1) == primal_signature(n2, c2),
        "incidence_signature": incidence_signature(n1, c1) == incidence_signature(n2, c2),
        "variable_count": n1 == n2,
        "clause_count": len(c1) == len(c2),
        "clause_length_multiset": sorted(map(len, c1)) == sorted(map(len, c2)),
        "occurrence_profile": occurrence_profile(n1, c1) == occurrence_profile(n2, c2),
    }


def a3_pair_sweep(graphs: Sequence[Graph], max_bases: int | None = None) -> dict:
    """A3 on every matched pair from Dee's generator: even bases x flip vertices."""
    pairs = 0
    failures = []
    for g in graphs:
        if len(components_of(g.n, g.edges)) != 1:
            continue
        bases = [b for b in itertools.product((0, 1), repeat=g.n) if sum(b) % 2 == 0]
        if max_bases is not None:
            bases = bases[:max_bases]
        for base in bases:
            for flip in range(g.n):
                pair = mi.generate_matched_tseitin_pair(g.to_dee(), base, flip)
                report = a3_report(pair.even.n_vars, pair.even.clauses, pair.odd.n_vars, pair.odd.clauses)
                pairs += 1
                if not all(report.values()):
                    failures.append({"graph": g.name, "base": base, "flip": flip, "report": report})
    return {"pairs": pairs, "failures": failures}


# ---------------------------------------------------------------------------
# A2 registered permutation suite and A6 statistics
# ---------------------------------------------------------------------------


def registered_permutation(n_vars: int, n_clauses: int, seed: int) -> tuple[list[int], list[int]]:
    """A2: ``pi`` shuffles the sorted declared IDs with Random(2*seed); ``rho``
    shuffles clause positions with Random(2*seed + 1).

    ``pi[i]`` is the image of variable ``i + 1``. The permuted formula's
    clause ``j`` is the original clause ``rho[j]``, with literal order and
    signs preserved.
    """
    pi = list(range(1, n_vars + 1))
    random.Random(2 * seed).shuffle(pi)
    rho = list(range(n_clauses))
    random.Random(2 * seed + 1).shuffle(rho)
    return pi, rho


def apply_permutation(clauses: Sequence[Sequence[int]], pi: Sequence[int], rho: Sequence[int]) -> list[tuple[int, ...]]:
    return [tuple(pi[abs(lit) - 1] * (1 if lit > 0 else -1) for lit in clauses[rho[j]]) for j in range(len(rho))]


def permute_model(model: Sequence[int], pi: Sequence[int]) -> list[int]:
    return sorted((pi[abs(lit) - 1] * (1 if lit > 0 else -1) for lit in model), key=abs)


def transformed_signatures(n_vars: int, clauses: Sequence[Sequence[int]], pi: Sequence[int], rho: Sequence[int]) -> tuple:
    """Signatures of the original pushed through (pi, rho), computed without
    building the permuted formula: the recorded permutation must witness the isomorphism."""
    position_of = {orig: new for new, orig in enumerate(rho)}
    primal = primal_signature(n_vars, clauses)
    primal_t = (primal[0], tuple(sorted(tuple(sorted((pi[a - 1], pi[b - 1]))) for a, b in primal[1])))
    inc = incidence_signature(n_vars, clauses)
    inc_t = (inc[0], inc[1], tuple(sorted((pi[v - 1], position_of[p]) for v, p in inc[2])))
    return primal_t, inc_t


def _quartiles(values: Sequence[float]) -> tuple[float, float]:
    if len(values) < 2:
        return values[0], values[0]
    q = statistics.quantiles(values, n=4, method="inclusive")
    return q[0], q[2]


def charge_variants(n: int) -> dict[str, tuple[int, ...]]:
    """DISCOVERY_ROUND_01 s5.4 variants, using hard_instances' vertex choices."""
    return {
        "zero": tuple([0] * n),
        "one": tuple([1] + [0] * (n - 1)),
        "two": tuple([1, 1] + [0] * (n - 2)),
    }


def run_permutation_suite(
    vertex_counts: Sequence[int] = REGISTERED_MOEBIUS_VERTEX_COUNTS,
    seeds: Sequence[int] = REGISTERED_PERMUTATION_SEEDS,
    budget: int = PERMUTATION_SUITE_BUDGET,
    repeat_for_reproducibility: bool = True,
) -> tuple[list[dict], dict]:
    """Registered permutation suite on the registered Moebius ladders.

    Returns ``(log_records, summary)``. Each log record retains both
    permutation arrays (A2). The same ``(pi, rho)`` is applied to every
    charge variant of a graph.
    """
    log: list[dict] = []
    failures: list[str] = []
    for V in vertex_counts:
        g = g_moebius(V // 2)
        variants = {name: mi.encode_tseitin(g.to_dee(), ch) for name, ch in charge_variants(V).items()}
        n_vars = variants["zero"].n_vars
        n_clauses = len(variants["zero"].clauses)
        oracle = {name: tseitin_oracle(V, g.edges, inst.charges) for name, inst in variants.items()}
        base_report = {}
        names = list(variants)
        for a, b in itertools.combinations(names, 2):
            base_report[f"{a}~{b}"] = a3_report(n_vars, variants[a].clauses, n_vars, variants[b].clauses)
        if not all(all(r.values()) for r in base_report.values()):
            failures.append(f"V={V}: unpermuted variants fail A3 {base_report}")
        for seed in ("identity",) + tuple(seeds):
            if seed == "identity":
                pi, rho = list(range(1, n_vars + 1)), list(range(n_clauses))
            else:
                pi, rho = registered_permutation(n_vars, n_clauses, seed)
            permuted = {name: apply_permutation(inst.clauses, pi, rho) for name, inst in variants.items()}
            for a, b in itertools.combinations(names, 2):
                if not all(a3_report(n_vars, permuted[a], n_vars, permuted[b]).values()):
                    failures.append(f"V={V} seed={seed}: permuted {a}/{b} fail A3")
            for name, inst in variants.items():
                clauses = permuted[name]
                expected_t = transformed_signatures(n_vars, inst.clauses, pi, rho)
                actual_t = (primal_signature(n_vars, clauses), incidence_signature(n_vars, clauses))
                iso_ok = expected_t == actual_t
                is_sat = oracle[name].consistent
                witness_ok = None
                if is_sat:
                    model = edge_witness_to_model(oracle[name].witness, inst.edge_ids, n_vars)
                    witness_ok = verify_cnf_assignment(clauses, permute_model(model, pi))
                ref = solve_pysat(n_vars, [list(c) for c in clauses])
                dp = solve_dpll(n_vars, [list(c) for c in clauses], max_decisions=budget)
                reproducible = None
                if repeat_for_reproducibility:
                    dp2 = solve_dpll(n_vars, [list(c) for c in clauses], max_decisions=budget)
                    reproducible = (dp.status, dp.decisions, dp.propagations, dp.timed_out) == (
                        dp2.status, dp2.decisions, dp2.propagations, dp2.timed_out)
                dpll_correct = dp.status == Status.UNKNOWN or dp.satisfiable == is_sat
                record = {
                    "vertex_count": V, "variant": name, "seed": seed,
                    "pi": pi, "rho": rho,
                    "oracle_sat": is_sat,
                    "pysat_sat": ref.satisfiable,
                    "pysat_decisions": ref.decisions,
                    "dpll_status": dp.status, "dpll_decisions": dp.decisions,
                    "dpll_propagations": dp.propagations,
                    "y": math.log1p(min(dp.decisions, budget)),
                    "budget_hit": dp.status == Status.UNKNOWN,
                    "witness_transformed_ok": witness_ok,
                    "isomorphism_witnessed": iso_ok,
                    "dpll_reproducible": reproducible,
                }
                log.append(record)
                if ref.satisfiable != is_sat:
                    failures.append(f"V={V} seed={seed} {name}: PySAT {ref.satisfiable} vs oracle {is_sat}")
                if not dpll_correct:
                    failures.append(f"V={V} seed={seed} {name}: DPLL {dp.status} vs oracle {is_sat}")
                if witness_ok is False:
                    failures.append(f"V={V} seed={seed} {name}: transformed witness fails")
                if not iso_ok:
                    failures.append(f"V={V} seed={seed} {name}: recorded permutation does not witness isomorphism")
                if reproducible is False:
                    failures.append(f"V={V} seed={seed} {name}: DPLL not reproducible")
    return log, summarise_permutation_suite(log, budget, failures)


def summarise_permutation_suite(log: Sequence[dict], budget: int, failures: Sequence[str]) -> dict:
    """A6 descriptive statistics over the registered seeds (identity excluded)."""
    registered = [r for r in log if r["seed"] != "identity"]
    by_key: dict[tuple[int, str], list[dict]] = {}
    for r in registered:
        by_key.setdefault((r["vertex_count"], r["variant"]), []).append(r)
    cells = []
    for (V, variant), rows in sorted(by_key.items()):
        ys = sorted(r["y"] for r in rows)
        capped = [min(r["dpll_decisions"], budget) for r in rows]
        q1, q3 = _quartiles(ys)
        ratio = (1 + max(capped)) / (1 + min(capped))
        identity = next(r for r in log if r["seed"] == "identity" and r["vertex_count"] == V and r["variant"] == variant)
        cells.append({
            "vertex_count": V, "variant": variant, "n_permutations": len(rows),
            "median_y": statistics.median(ys), "min_y": ys[0], "max_y": ys[-1], "iqr_y": q3 - q1,
            "budget_hit_fraction": sum(r["budget_hit"] for r in rows) / len(rows),
            "R": ratio, "sensitivity_label": "low" if ratio <= 2 else "high",
            "identity_dpll_decisions": identity["dpll_decisions"],
        })
    contrasts = []
    for V in sorted({r["vertex_count"] for r in registered}):
        for odd, even in (("one", "zero"), ("one", "two")):
            deltas = []
            for seed in sorted({r["seed"] for r in registered}):
                y = {r["variant"]: r["y"] for r in registered if r["vertex_count"] == V and r["seed"] == seed}
                deltas.append(y[odd] - y[even])
            deltas.sort()
            contrasts.append({
                "vertex_count": V, "contrast": f"Y_{odd} - Y_{even}",
                "median": statistics.median(deltas), "min": deltas[0], "max": deltas[-1],
                "fraction_positive": sum(d > 0 for d in deltas) / len(deltas),
                "fraction_zero": sum(d == 0 for d in deltas) / len(deltas),
                "fraction_negative": sum(d < 0 for d in deltas) / len(deltas),
            })
    return {
        "claim_level": "Empirical Observation (exploratory; DISCOVERY_ROUND_01 s5.4, ADVERSARIAL_REVIEW_01 A6)",
        "budget_b": budget,
        "runs": len(log),
        "registered_runs": len(registered),
        "status_failures": list(failures),
        "cells": cells,
        "contrasts": contrasts,
    }


# ---------------------------------------------------------------------------
# Malformed-instance attack matrix
# ---------------------------------------------------------------------------

REJECTED_AT_CONSTRUCTION = "REJECTED_AT_CONSTRUCTION"
REJECTED_BY_VALIDATOR = "REJECTED_BY_VALIDATOR"
ACCEPTED_CONSISTENT = "ACCEPTED_CONSISTENT"
ACCEPTED_INCONSISTENT = "ACCEPTED_INCONSISTENT"  # label right, but clauses != declared system
ACCEPTED_MISLABELED = "ACCEPTED_MISLABELED"  # Dee's parity label contradicts the CNF
ACCEPTED_DOWNSTREAM_FAILURE = "ACCEPTED_DOWNSTREAM_FAILURE"  # accepted, then solvers reject it


@dataclass
class AttackOutcome:
    case_id: str
    attack: str
    description: str
    classification: str
    rejected_by: str | None = None
    dee_label: str | None = None
    cnf_status: str | None = None
    encoding_matches: bool | None = None
    notes: dict = field(default_factory=dict)
    instance: object = field(default=None, repr=False, compare=False)  # the built instance, if any


def _sat_label(flag: bool) -> str:
    return "SAT" if flag else "UNSAT"


def classify_instance(case_id: str, attack: str, description: str,
                      build: Callable[[], mi.TseitinInstance], notes: dict | None = None) -> AttackOutcome:
    """Build, then apply Dee's instance-level validators (validate_graph and
    validate_metadata), then compare Dee's parity label with the CNF's status."""
    out = AttackOutcome(case_id, attack, description, "", notes=dict(notes or {}))
    try:
        inst = build()
    except (ValueError, TypeError, AssertionError) as exc:
        out.classification = REJECTED_AT_CONSTRUCTION
        out.rejected_by = f"{type(exc).__name__}: {exc}"
        return out
    out.instance = inst
    for name, check in (
        ("validate_graph", lambda: mi.validate_graph(inst.graph, require_connected=False, require_cubic=True)),
        ("validate_metadata", lambda: mi.validate_metadata(inst)),
    ):
        try:
            check()
        except (ValueError, TypeError) as exc:
            out.classification = REJECTED_BY_VALIDATOR
            out.rejected_by = f"{name}: {exc}"
            out.notes["dee_label_if_called_anyway"] = _sat_label(mi.is_parity_satisfiable(inst)) if _safe(lambda: mi.is_parity_satisfiable(inst)) else "raises"
            return out
    out.dee_label = _sat_label(mi.is_parity_satisfiable(inst))
    try:
        out.cnf_status = _sat_label(solve_pysat(int(inst.n_vars), [list(c) for c in inst.clauses]).satisfiable)
    except (ValueError, TypeError) as exc:
        out.cnf_status = f"SOLVER_REJECTS: {type(exc).__name__}: {exc}"
        out.classification = ACCEPTED_DOWNSTREAM_FAILURE
        return out
    try:
        decoded = decode_xor_cnf(inst.clauses)
        expected = sorted(expected_constraints(inst.graph.n_vertices, inst.graph.edges, inst.charges, inst.edge_ids))
        out.encoding_matches = decoded.exact and sorted((c.variables, c.rhs) for c in decoded.constraints) == expected
    except ValueError as exc:
        out.encoding_matches = False
        out.notes["encoding_check_error"] = str(exc)
    if out.dee_label != out.cnf_status:
        out.classification = ACCEPTED_MISLABELED
    elif not out.encoding_matches:
        out.classification = ACCEPTED_INCONSISTENT
    else:
        out.classification = ACCEPTED_CONSISTENT
    return out


def _safe(fn: Callable[[], object]) -> bool:
    try:
        fn()
        return True
    except Exception:  # noqa: BLE001 - probing only
        return False


def _petersen_pair() -> mi.MatchedTseitinPair:
    return mi.generate_matched_tseitin_pair(mi.petersen_graph())


def malformed_cases() -> list[AttackOutcome]:
    """Every Section 6.1 attack, executed against Dee's module."""
    out: list[AttackOutcome] = []
    pair = _petersen_pair()
    even, odd = pair.even, pair.odd
    k4 = mi.k4()

    # --- Incorrect edge mappings ------------------------------------------
    ids = list(even.edge_ids)
    # Swap the variables of edge 0 = (0,1) and an edge far from it, then pick a
    # genuine model in which the two swapped variables differ.
    j = next(i for i, (u, v) in enumerate(even.graph.edges) if {u, v}.isdisjoint({0, 1}))
    ids[0], ids[j] = ids[j], ids[0]
    swapped = replace(even, edge_ids=tuple(ids))
    oracle = tseitin_oracle(10, even.graph.edges, (0,) * 10)
    model = None
    for cycle_bits in _cycle_space_samples(even):
        if cycle_bits[0] != cycle_bits[j]:
            model = edge_witness_to_model(cycle_bits, even.edge_ids, even.n_vars)
            break
    genuine_ok = model is not None and verify_cnf_assignment([list(c) for c in even.clauses], model)
    dee_on_genuine = mi.validate_tseitin_assignment(swapped, {abs(l): l > 0 for l in model}) if model else None
    out.append(classify_instance(
        "M01", "incorrect edge mapping", "edge_ids of edges 0 and j swapped after encoding (hand-built)",
        lambda: swapped,
        {"genuine_cnf_model_satisfies_clauses": genuine_ok,
         "dee_validate_tseitin_assignment_on_that_model": dee_on_genuine,
         "oracle_consistent": oracle.consistent},
    ))
    out.append(classify_instance("M02", "incorrect edge mapping", "edge_ids of wrong length at encode",
                                 lambda: mi.encode_tseitin(k4, (0,) * 4, edge_ids=(1, 2, 3, 4, 5))))
    out.append(classify_instance("M03", "incorrect edge mapping", "edge id 0 / negative at encode",
                                 lambda: mi.encode_tseitin(k4, (0,) * 4, edge_ids=(0, 2, 3, 4, 5, 6))))
    out.append(classify_instance("M04", "incorrect edge mapping", "float edge ids at encode",
                                 lambda: mi.encode_tseitin(k4, (0,) * 4, edge_ids=tuple(float(i) for i in range(1, 7)))))
    out.append(classify_instance("M05", "incorrect edge mapping", "bool edge id (True) at encode",
                                 lambda: mi.encode_tseitin(k4, (0,) * 4, edge_ids=(True, 2, 3, 4, 5, 6))))
    out.append(classify_instance("M06", "incorrect edge mapping", "sparse positive ids (legitimate; isolated declared variables)",
                                 lambda: mi.encode_tseitin(k4, (1, 0, 0, 1), edge_ids=(3, 10, 17, 24, 31, 38))))

    # --- Duplicate edge IDs -----------------------------------------------
    out.append(classify_instance("M07", "duplicate edge IDs", "repeated id at encode",
                                 lambda: mi.encode_tseitin(k4, (0,) * 4, edge_ids=(1, 1, 2, 3, 4, 5))))
    out.append(classify_instance("M08", "duplicate edge IDs", "repeated id in a hand-built instance (clauses unchanged)",
                                 lambda: replace(even, edge_ids=(1,) + even.edge_ids[1:-1] + (1,))))

    # --- Missing clauses ----------------------------------------------------
    out.append(classify_instance("M09", "missing clauses", "odd instance minus one clause, metadata stale",
                                 lambda: replace(odd, clauses=odd.clauses[1:])))
    out.append(classify_instance("M10", "missing clauses", "odd instance minus one clause, n_clauses metadata refreshed",
                                 lambda: mi.replace_metadata(replace(odd, clauses=odd.clauses[1:]), n_clauses=len(odd.clauses) - 1)))
    out.append(classify_instance("M11", "missing clauses", "duplicated clause, n_clauses refreshed (semantically harmless)",
                                 lambda: mi.replace_metadata(replace(odd, clauses=odd.clauses + odd.clauses[:1]), n_clauses=len(odd.clauses) + 1)))

    # --- Corrupted charge metadata ----------------------------------------
    for case_id, desc, kwargs in (
        ("M12", "charge_sum_mod2 flipped", {"charge_sum_mod2": 1 - even.metadata["charge_sum_mod2"]}),
        ("M13", "component_charge_parities flipped", {"component_charge_parities": ((tuple(range(10)), 1),)}),
        ("M14", "n_vars wrong", {"n_vars": even.n_vars + 1}),
        ("M15", "n_clauses wrong", {"n_clauses": len(even.clauses) - 1}),
        ("M16", "n_vertices / n_edges / family wrong (fields validate_metadata does not read)",
         {"n_vertices": 99, "n_edges": -5, "family": "not-tseitin"}),
    ):
        out.append(classify_instance(case_id, "corrupted charge metadata", desc,
                                     lambda kw=kwargs: mi.replace_metadata(even, **kw)))
    out.append(classify_instance(
        "M17", "corrupted charge metadata",
        "charges field says odd, clauses encode even; metadata recomputed from the charges",
        lambda: mi.replace_metadata(replace(even, charges=odd.charges), charge_sum_mod2=1,
                                    component_charge_parities=mi.component_charge_parities(even.graph, odd.charges)),
    ))
    out.append(classify_instance("M18", "corrupted charge metadata", "encode with caller metadata overriding charge_sum_mod2",
                                 lambda: mi.encode_tseitin(k4, (1, 0, 0, 0), metadata={"charge_sum_mod2": 0})))

    # --- Invalid endpoints ------------------------------------------------
    out.append(classify_instance("M19", "invalid endpoints", "endpoint 9 in a 4-vertex graph at encode",
                                 lambda: mi.encode_tseitin(mi.SimpleGraph(4, ((0, 1), (0, 2), (0, 9), (1, 2), (1, 3), (2, 3))), (0,) * 4)))
    out.append(classify_instance("M20", "invalid endpoints", "negative endpoint at encode",
                                 lambda: mi.encode_tseitin(mi.SimpleGraph(4, ((-1, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))), (0,) * 4)))
    prism = mi.prism_graph(3)
    valid = mi.encode_tseitin(prism, (1, 0, 0, 1, 0, 0))  # connected, even total: SAT
    rungs_out = mi.SimpleGraph(6, tuple(sorted([(0, 1), (0, 2), (1, 2), (3, 4), (3, 5), (4, 5), (0, 9), (1, 9), (2, 9)])))
    hand_built = mi.replace_metadata(replace(valid, graph=rungs_out),
                                     component_charge_parities=mi.component_charge_parities(rungs_out, valid.charges))
    out.append(classify_instance(
        "M21", "invalid endpoints",
        "hand-built: prism3 CNF, graph with rung endpoints replaced by 9; metadata recomputed",
        lambda: hand_built,
        {"components_ignores_invalid_edges": mi.components(rungs_out),
         "dee_label_if_validate_graph_is_skipped": _sat_label(mi.is_parity_satisfiable(hand_built)),
         "validate_metadata_alone": _safe(lambda: mi.validate_metadata(hand_built)),
         "cnf_status": _sat_label(solve_pysat(valid.n_vars, [list(c) for c in valid.clauses]).satisfiable)},
    ))

    # --- Repeated graph edges, loops, degree --------------------------------
    out.append(classify_instance("M22", "repeated graph edges", "K4 plus a second (0,1) edge",
                                 lambda: mi.encode_tseitin(mi.duplicate_edge_graph(), (0,) * 4)))
    out.append(classify_instance("M23", "repeated graph edges", "cubic multigraph: two vertices joined by three parallel edges",
                                 lambda: mi.encode_tseitin(mi.SimpleGraph(2, ((0, 1), (0, 1), (0, 1))), (0, 0))))
    out.append(classify_instance("M24", "repeated graph edges", "self-loop", lambda: mi.encode_tseitin(mi.self_loop_graph(), (0,) * 4)))
    out.append(classify_instance("M25", "repeated graph edges", "non-cubic graph with validate=False",
                                 lambda: mi.encode_tseitin(mi.non_cubic_graph(), (0,) * 4, validate=False)))

    # --- Disconnected even-total but odd-component (legitimate) --------------
    two_k4 = mi.disconnected_two_k4()
    for case_id, desc, charges in (
        ("M26", "two K4, one charge in each (even total, both components odd)", (1, 0, 0, 0, 1, 0, 0, 0)),
        ("M27", "two K4, zero charged components", (0,) * 8),
        ("M28", "two K4, one odd component", (1, 0, 0, 0, 0, 0, 0, 0)),
        ("M29", "two K4, two charges in the same component", (1, 1, 0, 0, 0, 0, 0, 0)),
    ):
        out.append(classify_instance(case_id, "disconnected even-total but odd-component", desc,
                                     lambda ch=charges: mi.encode_tseitin(two_k4, ch)))
    out.append(classify_instance("M30", "disconnected even-total but odd-component", "empty graph (empty system)",
                                 lambda: mi.encode_tseitin(mi.SimpleGraph(0, ()), ())))

    # --- Generator preconditions --------------------------------------------
    out.append(classify_instance("M31", "generator scope", "moebius_ladder(2): registered 4-vertex ladder (DISCOVERY_ROUND_01 s5.4)",
                                 lambda: mi.encode_tseitin(mi.moebius_ladder(2), (0,) * 4)))
    out.append(classify_instance("M32", "generator scope", "matched pair on a disconnected graph",
                                 lambda: mi.generate_matched_tseitin_pair(two_k4).odd))
    out.append(classify_instance("M33", "generator scope", "matched pair with odd base charge",
                                 lambda: mi.generate_matched_tseitin_pair(mi.k4(), (1, 0, 0, 0)).odd))
    return out


def _cycle_space_samples(inst: mi.TseitinInstance) -> Iterable[tuple[int, ...]]:
    """Cycles through each edge: genuine solutions of the all-zero-charge system.

    For edge i = (u, v), the oracle solves G - i with charge 1 at u and v
    (a u-v path); adding edge i closes a cycle.
    """
    n, edges = inst.graph.n_vertices, inst.graph.edges
    for i, (u, v) in enumerate(edges):
        rest = [e for k, e in enumerate(edges) if k != i]
        charges = [0] * n
        charges[u] ^= 1
        charges[v] ^= 1
        res = tseitin_oracle(n, rest, charges)
        if res.consistent:
            bits = list(res.witness)
            bits.insert(i, 1)
            yield tuple(bits)


# ---------------------------------------------------------------------------
# Dee's vertex-permutation metamorphic transform (ruling A2, last paragraphs)
# ---------------------------------------------------------------------------


def check_vertex_permutation_metamorphic(g: Graph, perm: Sequence[int]) -> dict:
    """Is ``permute_matched_pair`` a correct relabelling, and is its edge-ID bijection recorded?

    The induced bijection is recomputed here from (perm, old edges, new
    edges). Both members' decoded XOR constraints must map exactly through it,
    and the charges and the flipped vertex must move consistently.
    """
    pair = mi.generate_matched_tseitin_pair(g.to_dee())
    moved = mi.permute_matched_pair(pair, perm)
    old_var = dict(zip(pair.even.graph.edges, pair.even.edge_ids))
    new_var = dict(zip(moved.even.graph.edges, moved.even.edge_ids))
    var_map = {old_var[(u, v)]: new_var[(min(perm[u], perm[v]), max(perm[u], perm[v]))] for u, v in pair.even.graph.edges}
    relabelling_ok = sorted(var_map.values()) == sorted(new_var.values())
    for member in ("even", "odd"):
        old, new = getattr(pair, member), getattr(moved, member)
        mapped = sorted((tuple(sorted(var_map[v] for v in c.variables)), c.rhs) for c in decode_xor_cnf(old.clauses).constraints)
        got = sorted((c.variables, c.rhs) for c in decode_xor_cnf(new.clauses).constraints)
        relabelling_ok &= mapped == got
        relabelling_ok &= all(new.charges[perm[v]] == old.charges[v] for v in range(g.n))
    relabelling_ok &= moved.flipped_vertex == perm[pair.flipped_vertex]
    recorded = any(hasattr(moved, name) for name in ("edge_bijection", "edge_permutation", "variable_permutation"))
    return {"relabelling_correct": relabelling_ok, "edge_bijection_recorded": recorded}


def vertex_permutation_suite() -> dict:
    results = []
    for g in [g_k4(), g_k33(), g_prism(3), g_moebius(3), g_moebius(4), g_prism(4), g_petersen()]:
        perms = {"rotation": mi.rotation_permutation(g.n, 1), "reverse": mi.reverse_permutation(g.n)}
        for seed in range(5):
            p = list(range(g.n))
            random.Random(f"{SEED_SUITE_PREFIX}|vertex-perm|{g.name}|{seed}").shuffle(p)
            perms[f"random:{seed}"] = tuple(p)
        for label, perm in perms.items():
            results.append({"graph": g.name, "perm": label, **check_vertex_permutation_metamorphic(g, perm)})
    return {
        "checked": len(results),
        "relabelling_correct": sum(r["relabelling_correct"] for r in results),
        "edge_bijection_recorded": sum(r["edge_bijection_recorded"] for r in results),
    }


def lean_fixture_check(lean_path: str | Path | None = None) -> dict:
    """Compare Python XOR3 clause lists with the Lean fixtures xor3CNF_dimacs_true/false."""
    import re
    from om_lab.hard_instances import _xor3_clauses

    path = Path(lean_path) if lean_path else Path(__file__).resolve().parents[2] / "lean" / "Millennium" / "Tseitin.lean"
    if not path.exists():
        return {"available": False}
    text = path.read_text(encoding="utf-8")
    fixtures = {}
    for rhs, name in ((1, "xor3CNF_dimacs_true"), (0, "xor3CNF_dimacs_false")):
        block = text.split(f"theorem {name}", 1)[1].split(":= by", 1)[0]
        body = block.split("=", 1)[1]
        rows = re.findall(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]", body)
        fixtures[rhs] = [tuple(int(x) for x in row) for row in rows]
    return {
        "available": True,
        "lean_file": str(path.name),
        "matched_instances.xor3_clauses": all(list(mi.xor3_clauses(1, 2, 3, q)) == fixtures[q] for q in (0, 1)),
        "hard_instances._xor3_clauses": all([tuple(c) for c in _xor3_clauses(1, 2, 3, q)] == fixtures[q] for q in (0, 1)),
        "fixtures": {str(q): fixtures[q] for q in (0, 1)},
    }


# ---------------------------------------------------------------------------
# Matched-pair check vacuity (mutation test), min-fill duplicate, Moebius bounds
# ---------------------------------------------------------------------------


def mutation_probe() -> dict:
    """Swap one variable in Dee's rhs=1 XOR3 encoding (a deliberate bug) and see
    which checks notice: Dee's in-generator pair assertions or the A3 signatures."""
    original = mi.xor3_clauses

    def buggy(a: int, b: int, c: int, rhs: int):
        clauses = original(a, b, c, rhs)
        if rhs == 1:  # replace c by b in one clause: wrong incidence, still 3 literals
            first = clauses[0]
            clauses = ((first[0], first[1], -first[1] if first[2] > 0 else first[1]),) + clauses[1:]
        return clauses

    mi.xor3_clauses = buggy
    try:
        try:
            pair = mi.generate_matched_tseitin_pair(mi.k4())
            dee_pair_assertions = "passed"
        except AssertionError as exc:  # since PR #24 (03b626d) Dee's pair assertions catch this mutation
            return {"dee_pair_assertions": f"raised: {exc}", "a3_detects": None}
    finally:
        mi.xor3_clauses = original
    report = a3_report(pair.even.n_vars, pair.even.clauses, pair.odd.n_vars, pair.odd.clauses)
    return {"dee_pair_assertions": dee_pair_assertions, "a3_report": report, "a3_detects": not all(report.values())}


def minfill_comparison() -> dict:
    """Dee's min_fill_width_estimate vs Nova's canonical primal_min_fill_width (ruling A1)."""
    rows = []
    for V in REGISTERED_MOEBIUS_VERTEX_COUNTS:
        g = g_moebius(V // 2)
        inst = mi.encode_tseitin(g.to_dee(), (0,) * V)
        for seed in ("identity",) + REGISTERED_PERMUTATION_SEEDS:
            if seed == "identity":
                clauses = [list(c) for c in inst.clauses]
            else:
                pi, rho = registered_permutation(inst.n_vars, len(inst.clauses), seed)
                clauses = [list(c) for c in apply_permutation(inst.clauses, pi, rho)]
            dee = mi.min_fill_width_estimate(replace(inst, clauses=tuple(map(tuple, clauses))))
            nova = primal_min_fill_width(inst.n_vars, clauses).width
            rows.append({"vertex_count": V, "seed": seed, "dee": dee, "nova": nova})
    disagreements = [r for r in rows if r["dee"] != r["nova"]]
    return {"compared": len(rows), "disagreements": len(disagreements), "examples": disagreements[:10],
            "max_nova_width": max(r["nova"] for r in rows), "max_dee_width": max(r["dee"] for r in rows)}


def minfill_random_probe(seeds: Iterable[int] = range(1000)) -> dict:
    """Dee's vs Nova's min-fill on random 3-SAT outside the Tseitin family.

    For seed s: ``rng = random.Random(s)``, ``n = rng.randint(6, 18)``,
    ``m = rng.randint(n, 4 * n)``, formula ``generate_random_3sat(n, m, seed=s)``.
    """
    from om_lab.generators import generate_random_3sat

    stub = mi.encode_tseitin(mi.k4(), (0, 0, 0, 0))
    seeds = list(seeds)
    rows = []
    for s in seeds:
        rng = random.Random(s)
        n = rng.randint(6, 18)
        m = rng.randint(n, 4 * n)
        inst = generate_random_3sat(n, m, seed=s)
        dee = mi.min_fill_width_estimate(replace(stub, n_vars=n, clauses=tuple(map(tuple, inst.clauses))))
        nova = primal_min_fill_width(n, inst.clauses).width
        if dee != nova:
            rows.append({"seed": s, "n": n, "m": m, "dee": dee, "nova": nova})
    smallest = min(rows, key=lambda r: (r["n"], r["m"])) if rows else None
    return {"compared": len(seeds), "disagreements": len(rows), "dee_higher": sum(r["dee"] > r["nova"] for r in rows),
            "dee_lower": sum(r["dee"] < r["nova"] for r in rows), "smallest_example": smallest}


def cycle_rank_probe(seeds: Sequence[int] = REGISTERED_PERMUTATION_SEEDS, max_decisions: int = 200_000) -> list[dict]:
    """DPLL branch counts under the registered permutations, beyond the ladders.

    Exploratory (Section 5 of the review): compares the observed counts with
    r and 2^(r+1) - 2, where r = |E| - |V| + #components is the cycle rank.
    The pattern does not hold for cubic graphs in general; see
    cycle_rank_counterexamples() and cycle_rank_random_scan().
    """
    rows = []
    graphs = [g_k4(), g_k33(), g_prism(3), g_prism(4), g_prism(5), g_prism(6), g_petersen(),
              g_union(g_k4(), g_k4()), g_union(g_k33(), g_petersen())]
    for g in graphs:
        rank = len(g.edges) - g.n + len(components_of(g.n, g.edges))
        observed = {}
        for name, charges in charge_variants(g.n).items():
            inst = mi.encode_tseitin(g.to_dee(), charges)
            counts = set()
            for seed in seeds:
                pi, rho = registered_permutation(inst.n_vars, len(inst.clauses), seed)
                clauses = [list(c) for c in apply_permutation(inst.clauses, pi, rho)]
                counts.add(solve_dpll(inst.n_vars, clauses, max_decisions=max_decisions).decisions)
            observed[name] = sorted(counts)
        rows.append({"graph": g.name, "connected": len(components_of(g.n, g.edges)) == 1, "cycle_rank": rank,
                     "predicted_even": rank, "predicted_odd": 2 ** (rank + 1) - 2, "observed": observed})
    return rows


def certifier_on_accepted_attacks(outcomes: Sequence[AttackOutcome] | None = None) -> dict[str, str]:
    """PR #10's ``certify_tseitin_by_construction`` on every attack case that Dee's
    validators accept (cross-check for CLAUDE-R8-05..R8-07)."""
    from om_lab.certify import certify_tseitin_by_construction

    outcomes = malformed_cases() if outcomes is None else outcomes
    return {o.case_id: str(certify_tseitin_by_construction(o.instance)["verification_status"])
            for o in outcomes if o.classification.startswith("ACCEPTED")}


def random_connected_cubic(n: int, rng: random.Random) -> list[tuple[int, int]]:
    """Configuration-model sample of a simple connected cubic graph (rejection sampling)."""
    while True:
        points = [v for v in range(n) for _ in range(3)]
        rng.shuffle(points)
        edges: set[tuple[int, int]] = set()
        for i in range(0, len(points), 2):
            u, v = points[i], points[i + 1]
            e = (min(u, v), max(u, v))
            if u == v or e in edges:
                break
            edges.add(e)
        else:
            if len(components_of(n, sorted(edges))) == 1:
                return sorted(edges)


# Two 3-edge-connected cubic graphs on 10 vertices (girth 3) found by
# cycle_rank_random_scan(). Under the registered seeds the DPLL branch count is
# not the ladder pattern r / 2^(r+1) - 2 (CLAUDE-R8-16).
CYCLE_RANK_COUNTEREXAMPLES = {
    "G10a": ((
        (0, 4), (0, 6), (0, 7), (1, 4), (1, 5), (1, 6), (2, 4), (2, 8), (2, 9), (3, 5),
        (3, 7), (3, 9), (5, 6), (7, 8), (8, 9)), (1, 0, 1, 0, 0, 0, 1, 0, 0, 1)),
    "G10b": ((
        (0, 1), (0, 3), (0, 9), (1, 5), (1, 9), (2, 3), (2, 6), (2, 7), (3, 8), (4, 6),
        (4, 8), (4, 9), (5, 7), (5, 8), (6, 7)), (0, 1, 0, 0, 1, 0, 1, 0, 0, 0)),
}


def cycle_rank_counterexamples(seeds: Sequence[int] = REGISTERED_PERMUTATION_SEEDS) -> list[dict]:
    """Registered-seed DPLL branch counts on CYCLE_RANK_COUNTEREXAMPLES."""
    rows = []
    for name, (edges, charges) in CYCLE_RANK_COUNTEREXAMPLES.items():
        g = Graph(name, len(charges), tuple(edges))
        inst = mi.encode_tseitin(g.to_dee(), charges)
        rank = len(edges) - g.n + 1
        sat = tseitin_oracle(g.n, list(edges), charges).consistent
        identity = solve_dpll(inst.n_vars, [list(c) for c in inst.clauses]).decisions
        counts = []
        for seed in seeds:
            pi, rho = registered_permutation(inst.n_vars, len(inst.clauses), seed)
            counts.append(solve_dpll(inst.n_vars, [list(c) for c in apply_permutation(inst.clauses, pi, rho)]).decisions)
        rows.append({"graph": name, "edges": [list(e) for e in edges], "charges": list(charges), "sat": sat,
                     "cycle_rank": rank, "connected": len(components_of(g.n, list(edges))) == 1,
                     "predicted": rank if sat else 2 ** (rank + 1) - 2, "identity_decisions": identity,
                     "registered_seed_decisions": sorted(set(counts)),
                     "R": (1 + max(counts)) / (1 + min(counts))})
    return rows


def cycle_rank_random_scan(vertex_counts: Sequence[int] = (8, 10, 12, 14, 16), graphs_per_size: int = 30,
                           trials_per_graph: int = 40, seed: str = "OM-P4-R8|cycle-rank-scan") -> dict:
    """How often DPLL counts leave the ladder pattern on random connected cubic graphs.

    Per trial: a uniform 0/1 charge vector, then a (pi, rho) drawn with the A2
    construction from a random seed; the count is compared with r (consistent
    systems) or 2^(r+1) - 2 (inconsistent systems).
    """
    rng = random.Random(seed)
    rows = {}
    for n in vertex_counts:
        st = {"graphs": 0, "graphs_with_deviation": 0, "sat_runs": 0, "sat_deviations": 0,
              "unsat_runs": 0, "unsat_deviations": 0}
        for _ in range(graphs_per_size):
            edges = random_connected_cubic(n, rng)
            g = Graph(f"random{n}", n, tuple(edges))
            dee, rank = g.to_dee(), len(edges) - n + 1
            st["graphs"] += 1
            deviated = False
            for _ in range(trials_per_graph):
                charges = tuple(rng.randint(0, 1) for _ in range(n))
                inst = mi.encode_tseitin(dee, charges)
                sat = tseitin_oracle(n, edges, charges).consistent
                pi, rho = registered_permutation(inst.n_vars, len(inst.clauses), rng.randrange(10**9))
                d = solve_dpll(inst.n_vars, [list(c) for c in apply_permutation(inst.clauses, pi, rho)]).decisions
                key = "sat" if sat else "unsat"
                st[f"{key}_runs"] += 1
                if d != (rank if sat else 2 ** (rank + 1) - 2):
                    st[f"{key}_deviations"] += 1
                    deviated = True
            st["graphs_with_deviation"] += deviated
        rows[str(n)] = st
    return {"seed": seed, "graphs_per_size": graphs_per_size, "trials_per_graph": trials_per_graph, "by_vertex_count": rows}


def moebius_decomposition_check(vertex_counts: Sequence[int] = REGISTERED_MOEBIUS_VERTEX_COUNTS) -> dict:
    """Mechanically check the DISCOVERY_ROUND_01 s6 / s6.1 path decompositions.

    Bags B_i = R_0 u R_i u R_{i+1} on the ladder (claimed width <= 5), and
    their edge-incidence replacements on the CNF primal graph, which is the
    line graph (claimed width <= 17).
    """
    results = []
    for V in vertex_counts:
        k = V // 2
        g = g_moebius(k)
        rung = [{i, i + k} for i in range(k)]
        bags = [rung[0] | rung[i] | rung[i + 1] for i in range(k - 1)] if k >= 2 else [set(range(V))]
        ok_graph, width_graph = _is_path_decomposition(range(V), g.edges, bags)
        inst = mi.encode_tseitin(g.to_dee(), (0,) * V)
        var_of = dict(zip(inst.graph.edges, inst.edge_ids))
        line_bags = [{var_of[e] for e in g.edges if e[0] in bag or e[1] in bag} for bag in bags]
        primal_edges = primal_signature(inst.n_vars, inst.clauses)[1]
        ok_line, width_line = _is_path_decomposition(range(1, inst.n_vars + 1), primal_edges, line_bags)
        results.append({
            "vertex_count": V,
            "ladder_decomposition_valid": ok_graph, "ladder_width": width_graph,
            "primal_decomposition_valid": ok_line, "primal_width": width_line,
            "nova_min_fill_width_identity": primal_min_fill_width(inst.n_vars, [list(c) for c in inst.clauses]).width,
        })
    return {"claim_level": "Empirical Observation (construction checked on registered sizes)", "results": results}


def _is_path_decomposition(vertices: Iterable[int], edges: Iterable[tuple[int, int]], bags: Sequence[set[int]]) -> tuple[bool, int]:
    vertices = list(vertices)
    if any(not any(v in b for b in bags) for v in vertices):
        return False, -1
    if any(not any(u in b and v in b for b in bags) for u, v in edges):
        return False, -1
    for v in vertices:
        idx = [i for i, b in enumerate(bags) if v in b]
        if idx != list(range(idx[0], idx[-1] + 1)):  # contiguous interval along the path
            return False, -1
    return True, max(len(b) for b in bags) - 1


# ---------------------------------------------------------------------------
# Gate B re-attack of Dee's repair (draft PR #24, 03b626d)
# ---------------------------------------------------------------------------


def validators_accept_legitimate_instances(full: bool = True) -> dict:
    """Over-rejection check: Dee's validators must accept every legitimate instance.

    ``validate_metadata`` re-encodes since PR #24, so it is applied to every
    instance the legitimate sweeps build: all charge vectors on the exhaustive
    graphs under three edge maps, the seed suite under two, both members of
    every matched pair on the connected exhaustive graphs, vertex-permuted
    pairs, and the empty graph.
    """
    rejected: list[tuple] = []
    counts = Counter()

    def check(kind: str, label: tuple, inst: mi.TseitinInstance) -> None:
        counts[kind] += 1
        try:
            mi.validate_graph(inst.graph, require_connected=False, require_cubic=True)
            mi.validate_metadata(inst)
        except (ValueError, TypeError, AssertionError) as exc:
            rejected.append((kind,) + label + (f"{type(exc).__name__}: {exc}",))

    graphs = exhaustive_graphs() if full else [g_k4(), g_k33(), g_prism(3), g_union(g_k4(), g_k4())]
    for g in graphs:
        dee = g.to_dee()
        variants = edge_id_variants(g) if full else {"default": edge_id_variants(g)["default"],
                                                     "sparse": edge_id_variants(g)["sparse"]}
        for ids_name, ids in variants.items():
            for name, charges in all_charge_vectors(g):
                check("exhaustive", (g.name, ids_name, name), mi.encode_tseitin(dee, charges, edge_ids=ids))
    if full:
        for g in seed_suite_graphs():
            dee = g.to_dee()
            for ids_name in ("default", "shuffled"):
                for name, charges in seed_suite_charge_vectors(g):
                    check("seed_suite", (g.name, ids_name, name),
                          mi.encode_tseitin(dee, charges, edge_ids=edge_id_variants(g)[ids_name]))
    for g in graphs:
        if len(components_of(g.n, list(g.edges))) != 1:
            continue
        dee = g.to_dee()
        for name, base in all_charge_vectors(g):
            if sum(base) % 2:
                continue
            for flip in range(g.n):
                pair = mi.generate_matched_tseitin_pair(dee, base_charge=base, flip_vertex=flip)
                check("pair_member", (g.name, name, flip, "even"), pair.even)
                check("pair_member", (g.name, name, flip, "odd"), pair.odd)
    for name, graph in mi.connected_cubic_registry().items():
        pair = mi.generate_matched_tseitin_pair(graph)
        n = graph.n_vertices
        for shift in range(n):
            for perm in (mi.rotation_permutation(n, shift), tuple(reversed(mi.rotation_permutation(n, shift)))):
                permuted = mi.permute_matched_pair(pair, perm)
                check("permuted_pair_member", (name, shift, "even"), permuted.even)
                check("permuted_pair_member", (name, shift, "odd"), permuted.odd)
    check("empty_graph", ("empty",), mi.encode_tseitin(mi.SimpleGraph(0, ()), ()))
    return {"checked": dict(sorted(counts.items())), "total": sum(counts.values()),
            "rejected": rejected[:20], "n_rejected": len(rejected)}


def xor3_signature_preserving_mutations(graph_name: str = "petersen") -> dict:
    """Two deliberate bugs in ``xor3_clauses`` that keep every A3 signature.

    ``sign_swap`` exchanges the third literals of the 2nd and 4th rhs=1 clauses
    (one positive, one negative): same variables, same per-variable sign counts,
    but the clause group no longer encodes XOR = 1. ``parity_flip`` encodes
    XOR = 1 - rhs everywhere. Reports whether ``generate_matched_tseitin_pair``
    raises, and each member's declared label against PySAT on its clauses.
    """
    original = mi.xor3_clauses

    def sign_swap(a: int, b: int, c: int, rhs: int):
        cls = [list(x) for x in original(a, b, c, rhs)]
        if rhs == 1:
            cls[1][2], cls[3][2] = cls[3][2], cls[1][2]
        return tuple(tuple(x) for x in cls)

    def parity_flip(a: int, b: int, c: int, rhs: int):
        return original(a, b, c, 1 - rhs)

    graph = {"petersen": mi.petersen_graph, "k4": mi.k4}[graph_name]()
    rows = {}
    for name, fn in (("sign_swap", sign_swap), ("parity_flip", parity_flip)):
        mi.xor3_clauses = fn
        try:
            try:
                pair = mi.generate_matched_tseitin_pair(graph)
                raised = None
            except AssertionError as exc:
                pair, raised = None, str(exc)
        finally:
            mi.xor3_clauses = original
        row: dict = {"generator_raised": raised}
        if pair is not None:
            report = a3_report(pair.even.n_vars, pair.even.clauses, pair.odd.n_vars, pair.odd.clauses)
            row["a3_all_equal"] = all(report.values())
            for role, inst in (("even", pair.even), ("odd", pair.odd)):
                row[role] = {
                    "declared_label": _sat_label(mi.is_parity_satisfiable(inst)),
                    "cnf_status": _sat_label(solve_pysat(inst.n_vars, [list(c) for c in inst.clauses]).satisfiable),
                    "decodes_to_exact_xor": decode_xor_cnf(inst.clauses).exact,
                }
        rows[name] = row
    return rows


def integrity_fuzz(trials: int = 6000, seed: str = "OM-P4-PR24|fuzz") -> dict:
    """Random single mutations of valid instances against validate_graph + validate_metadata.

    Each trial encodes a random charge vector on a random exhaustive graph with
    random distinct sparse ids, applies one mutation (kinds below), and records
    whether the validators accept it. An accepted mutant is "non-canonical" when
    it differs from ``encode_tseitin(graph, charges, edge_ids)`` or carries a
    non-int ``n_vars`` or charge.
    """
    rng = random.Random(seed)
    graphs = [g.to_dee() for g in exhaustive_graphs()]
    kinds = ["flip_sign", "drop_clause", "dup_clause", "swap_clauses", "change_var", "change_charge", "swap_ids",
             "shift_id", "dup_id", "n_vars_plus", "n_vars_float", "charges_float", "repoint_edge", "reorder_edges",
             "metadata_extra"]
    stats = {k: {"tried": 0, "accepted": 0, "accepted_noncanonical": 0, "escaped_non_valueerror": 0} for k in kinds}
    for _ in range(trials):
        g = rng.choice(graphs)
        base = mi.encode_tseitin(g, tuple(rng.randint(0, 1) for _ in range(g.n_vertices)),
                                 edge_ids=tuple(rng.sample(range(1, 4 * len(g.edges)), len(g.edges))))
        kind = rng.choice(kinds)
        cl = [list(c) for c in base.clauses]
        kw: dict = {}
        md = dict(base.metadata)
        if kind == "flip_sign":
            i, j = rng.randrange(len(cl)), rng.randrange(3)
            cl[i][j] = -cl[i][j]
        elif kind == "drop_clause":
            cl.pop(rng.randrange(len(cl)))
            md["n_clauses"] = len(cl)
        elif kind == "dup_clause":
            cl.append(list(rng.choice(cl)))
            md["n_clauses"] = len(cl)
        elif kind == "swap_clauses":
            i, j = rng.sample(range(len(cl)), 2)
            cl[i], cl[j] = cl[j], cl[i]
        elif kind == "change_var":
            i, j = rng.randrange(len(cl)), rng.randrange(3)
            v = rng.choice(base.edge_ids)
            cl[i][j] = v if cl[i][j] > 0 else -v
        elif kind == "change_charge":
            ch = list(base.charges)
            k = rng.randrange(len(ch))
            ch[k] ^= 1
            kw["charges"] = tuple(ch)
            md["charge_sum_mod2"] = sum(ch) % 2
            md["component_charge_parities"] = mi.component_charge_parities(base.graph, ch)
        elif kind == "swap_ids":
            ids = list(base.edge_ids)
            i, j = rng.sample(range(len(ids)), 2)
            ids[i], ids[j] = ids[j], ids[i]
            kw["edge_ids"] = tuple(ids)
        elif kind == "shift_id":
            ids = list(base.edge_ids)
            i = rng.randrange(len(ids))
            free = sorted(set(range(1, max(ids))) - set(ids))
            if free:
                ids[i] = rng.choice(free)
            kw["edge_ids"] = tuple(ids)
        elif kind == "dup_id":
            ids = list(base.edge_ids)
            i, j = rng.sample(range(len(ids)), 2)
            ids[j] = ids[i]
            kw["edge_ids"] = tuple(ids)
        elif kind == "n_vars_plus":
            kw["n_vars"] = base.n_vars + 1
            md["n_vars"] = base.n_vars + 1
        elif kind == "n_vars_float":
            kw["n_vars"] = float(base.n_vars)
        elif kind == "charges_float":
            kw["charges"] = tuple(float(c) for c in base.charges)
        elif kind == "repoint_edge":
            edges = list(base.graph.edges)
            i = rng.randrange(len(edges))
            u, _v = edges[i]
            edges[i] = (u, rng.randrange(base.graph.n_vertices + 2))
            kw["graph"] = mi.SimpleGraph(base.graph.n_vertices, tuple(edges))
        elif kind == "reorder_edges":
            edges = list(base.graph.edges)
            rng.shuffle(edges)
            kw["graph"] = mi.SimpleGraph(base.graph.n_vertices, tuple(edges))
        elif kind == "metadata_extra":
            md["note"] = "extra"
        inst = replace(base, clauses=tuple(tuple(c) for c in cl), metadata=md, **kw)
        st = stats[kind]
        st["tried"] += 1
        try:
            mi.validate_graph(inst.graph, require_connected=False, require_cubic=True)
            mi.validate_metadata(inst)
        except ValueError:
            continue
        except Exception:  # noqa: BLE001 - counted: the documented exception type is ValueError
            st["escaped_non_valueerror"] += 1
            continue
        st["accepted"] += 1
        try:
            canon = mi.encode_tseitin(inst.graph, inst.charges, edge_ids=inst.edge_ids)
            same = (canon.clauses == inst.clauses and canon.n_vars == inst.n_vars and type(inst.n_vars) is int
                    and tuple(inst.charges) == canon.charges and all(type(c) is int for c in inst.charges))
        except (ValueError, TypeError):
            same = False
        if not same:
            st["accepted_noncanonical"] += 1
    return {"seed": seed, "trials": trials, "by_kind": stats,
            "accepted_noncanonical_kinds": sorted(k for k, v in stats.items() if v["accepted_noncanonical"])}


def declared_var_cost(tops: Sequence[int] = (10_000, 30_000)) -> dict:
    """Seconds for primal_graph and min_fill_width_estimate on K4 when one edge id is ``top``.

    Not part of run_all (about 5 minutes at 30,000 on the review machine).
    """
    import time

    rows = {}
    for top in tops:
        inst = mi.encode_tseitin(mi.k4(), (0, 0, 0, 0), edge_ids=(1, 2, 3, 4, 5, top))
        t0 = time.perf_counter()
        mi.primal_graph(inst)
        t1 = time.perf_counter()
        width = mi.min_fill_width_estimate(inst)
        t2 = time.perf_counter()
        rows[str(top)] = {"primal_graph_s": round(t1 - t0, 3), "min_fill_s": round(t2 - t1, 2), "width": width}
    return rows


def pr24_type_probes() -> dict:
    """Type-only malformations found at Gate B (CLAUDE-G24-01, G24-04).

    ``n_vars_float`` is a hand-built copy of a valid odd K4 instance with
    ``n_vars=6.0``; ``charges_float`` and ``charges_bool`` are built with
    ``encode_tseitin``. For each: does ``validate_metadata`` accept it, and what
    do the direct consumers do with it? At 03b626d all three were accepted;
    since Dee's 577e469 ``validate_metadata`` rejects ``n_vars_float`` and
    ``encode_tseitin`` refuses the non-int charges (TypeError).
    """
    from om_lab.certify import certify_tseitin_by_construction

    odd = mi.encode_tseitin(mi.k4(), (1, 0, 0, 0))
    builders = {
        "n_vars_float": lambda: replace(odd, n_vars=float(odd.n_vars)),
        "charges_float": lambda: mi.encode_tseitin(mi.k4(), (1.0, 0.0, 0.0, 0.0)),
        "charges_bool": lambda: mi.encode_tseitin(mi.k4(), (True, False, False, False)),
    }
    rows = {}
    for name, build in builders.items():
        row: dict = {}
        try:
            inst = build()
        except (ValueError, TypeError) as exc:
            rows[name] = {"construction": f"{type(exc).__name__}: {exc}"}
            continue
        for label, fn in (
            ("validate_metadata", lambda: mi.validate_metadata(inst)),
            ("is_parity_satisfiable", lambda: mi.is_parity_satisfiable(inst)),
            ("solve_pysat", lambda: solve_pysat(inst.n_vars, [list(c) for c in inst.clauses]).status),
            ("solve_dpll", lambda: solve_dpll(inst.n_vars, [list(c) for c in inst.clauses]).status),
            ("primal_graph", lambda: len(mi.primal_graph(inst))),
            ("certify_tseitin_by_construction", lambda: str(certify_tseitin_by_construction(inst)["verification_status"])),
        ):
            try:
                value = fn()
                row[label] = value if isinstance(value, (bool, int, str)) else str(value)
            except (ValueError, TypeError) as exc:
                row[label] = f"raises {type(exc).__name__}"
        rows[name] = row
    return rows


# ---------------------------------------------------------------------------
# Everything, for the review report
# ---------------------------------------------------------------------------


def run_all(out_dir: str | Path, *, full: bool = True) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"attacked_commit": ATTACKED_COMMIT, "claim_level": "Empirical Observation"}
    report["constructors"] = check_dee_constructors()
    report["exhaustive"] = sweep(exhaustive_graphs(), all_charge_vectors,
                                 id_variants=("default", "shuffled", "sparse") if full else ("default",), dpll=True)
    report["seed_suite"] = sweep(seed_suite_graphs(), seed_suite_charge_vectors,
                                 id_variants=("default", "shuffled") if full else ("default",))
    report["a3_pairs"] = a3_pair_sweep([g for g in exhaustive_graphs()], max_bases=None if full else 4)
    report["mutation_probe"] = mutation_probe()
    outcomes = malformed_cases()
    report["malformed"] = [asdict_outcome(o) for o in outcomes]
    report["certifier_on_accepted_attacks"] = certifier_on_accepted_attacks(outcomes)
    report["minfill"] = minfill_comparison()
    report["minfill_random_probe"] = minfill_random_probe()
    report["cycle_rank_probe"] = cycle_rank_probe()
    report["cycle_rank_counterexamples"] = cycle_rank_counterexamples()
    report["cycle_rank_random_scan"] = cycle_rank_random_scan()
    report["moebius_bounds"] = moebius_decomposition_check()
    report["vertex_permutations"] = vertex_permutation_suite()
    report["lean_fixtures"] = lean_fixture_check()
    log, summary = run_permutation_suite(repeat_for_reproducibility=True)
    log_path = out / "permutation_suite_log.jsonl"
    data = "".join(json.dumps(r, sort_keys=True) + "\n" for r in log)
    log_path.write_text(data, encoding="utf-8")
    summary["log_file"] = log_path.name
    summary["log_sha256"] = hashlib.sha256(data.encode("utf-8")).hexdigest()
    report["permutation_suite"] = summary
    report["gate_b_pr24"] = {
        "commit": GATE_B_PR24_COMMIT,
        "validators_accept_legitimate_instances": validators_accept_legitimate_instances(full=full),
        "xor3_signature_preserving_mutations": xor3_signature_preserving_mutations(),
        "type_probes": pr24_type_probes(),
        "integrity_fuzz": integrity_fuzz(),
    }
    (out / "review_pr8_report.json").write_text(json.dumps(report, indent=1, sort_keys=True, default=str), encoding="utf-8")
    return report


def asdict_outcome(o: AttackOutcome) -> dict:
    return {
        "case_id": o.case_id, "attack": o.attack, "description": o.description,
        "classification": o.classification, "rejected_by": o.rejected_by,
        "dee_label": o.dee_label, "cnf_status": o.cnf_status,
        "encoding_matches": o.encoding_matches, "notes": o.notes,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m om_lab.review_pr8", description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--quick", action="store_true", help="default edge ids only; fewer A3 bases")
    args = parser.parse_args(argv)
    report = run_all(args.out_dir, full=not args.quick)
    ex, ss = report["exhaustive"], report["seed_suite"]
    ps = report["permutation_suite"]
    print(f"[Claim Level: Empirical Observation] review of PR #8 at {ATTACKED_COMMIT}")
    print(f"exhaustive: {ex['instances']} instances, mismatches={len(ex['mismatches'])}")
    print(f"seed suite: {ss['instances']} instances, mismatches={len(ss['mismatches'])}")
    print(f"A3 pairs: {report['a3_pairs']['pairs']} checked, failures={len(report['a3_pairs']['failures'])}")
    print(f"permutation suite: {ps['runs']} runs, status failures={len(ps['status_failures'])}, log sha256={ps['log_sha256']}")
    print("malformed:", Counter(o["classification"] for o in report["malformed"]))
    print(f"min-fill (Dee vs Nova): {report['minfill']['disagreements']}/{report['minfill']['compared']} disagree")
    gb = report["gate_b_pr24"]["validators_accept_legitimate_instances"]
    print(f"Gate B (PR #24 at {GATE_B_PR24_COMMIT}): validators rejected {gb['n_rejected']} of {gb['total']} legitimate instances")
    return 0 if not (ex["mismatches"] or ss["mismatches"] or ps["status_failures"]) else 1


if __name__ == "__main__":
    sys.exit(main())
