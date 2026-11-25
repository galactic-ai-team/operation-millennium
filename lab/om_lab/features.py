"""Structural feature extraction for CNF instances.

[Claim Level: Empirical Observation] for any use of these features to
predict solver hardness. The features themselves are deterministic,
directly computed properties of a formula -- no solving, learning, or
inference is involved in extracting them, and no feature here is a
proof of anything about worst-case complexity.

What is (and is not) a backbone feature
---------------------------------------
A true backbone (variables taking the same value in *every* satisfying
assignment) can only be established by solving. This module does **not**
estimate or claim a backbone. The structural proxy included instead is
``unit_clause_fraction`` (the density of unit clauses), plus
``pure_literal_fraction``. Either can be computed without a solver;
neither is a backbone.

All features are finite floats for every input, including the empty
formula (``n_vars == 0`` or no clauses): degenerate cases return 0.0
rather than NaN / division-by-zero. Feature definitions are stated in
the docstring of :func:`extract_features_from_clauses`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from typing import Sequence

from om_lab.generators import CNFInstance

__all__ = [
    "CNFFeatures",
    "FEATURE_NAMES",
    "extract_features",
    "extract_features_from_clauses",
]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: Sequence[float]) -> float:
    """Population standard deviation; 0.0 for fewer than two values."""
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    return math.sqrt(sum((v - mu) ** 2 for v in values) / len(values))


def _entropy_bits(probabilities: Sequence[float]) -> float:
    """Shannon entropy in bits of a probability distribution."""
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def _validate(n_vars: int, clauses: Sequence[Sequence[int]]) -> None:
    if n_vars < 0:
        raise ValueError("n_vars must be non-negative")
    for clause in clauses:
        for lit in clause:
            if lit == 0 or abs(lit) > n_vars:
                raise ValueError(
                    f"literal {lit} out of range for n_vars={n_vars}"
                )


@dataclass(frozen=True)
class CNFFeatures:
    """Deterministic structural features of one CNF instance.

    Every field is a plain ``float`` (or ``int`` for the two counts) so
    the dataclass serialises directly to JSON. See
    :func:`extract_features_from_clauses` for the definition of each
    field.
    """

    n_vars: int
    n_clauses: int
    alpha: float
    clause_len_mean: float
    clause_len_std: float
    clause_len_min: float
    clause_len_max: float
    clause_len_entropy: float
    unit_clause_fraction: float
    binary_clause_fraction: float
    ternary_clause_fraction: float
    tautology_clause_fraction: float
    duplicate_clause_fraction: float
    pos_literal_fraction: float
    polarity_balance: float
    var_occurrence_mean: float
    var_occurrence_std: float
    var_occurrence_max: float
    var_occurrence_cv: float
    var_occurrence_entropy: float
    var_occurrence_entropy_norm: float
    isolated_var_fraction: float
    singleton_var_fraction: float
    pure_literal_fraction: float
    cooccurrence_degree_mean: float
    cooccurrence_degree_max: float
    cooccurrence_isolated_fraction: float

    def to_dict(self) -> dict[str, float]:
        """Return the features as an ordered ``{name: value}`` dict."""
        return {name: float(getattr(self, name)) for name in FEATURE_NAMES}


# Canonical feature order, used by ``to_dict`` and by the analysis script.
FEATURE_NAMES: list[str] = [
    "n_vars",
    "n_clauses",
    "alpha",
    "clause_len_mean",
    "clause_len_std",
    "clause_len_min",
    "clause_len_max",
    "clause_len_entropy",
    "unit_clause_fraction",
    "binary_clause_fraction",
    "ternary_clause_fraction",
    "tautology_clause_fraction",
    "duplicate_clause_fraction",
    "pos_literal_fraction",
    "polarity_balance",
    "var_occurrence_mean",
    "var_occurrence_std",
    "var_occurrence_max",
    "var_occurrence_cv",
    "var_occurrence_entropy",
    "var_occurrence_entropy_norm",
    "isolated_var_fraction",
    "singleton_var_fraction",
    "pure_literal_fraction",
    "cooccurrence_degree_mean",
    "cooccurrence_degree_max",
    "cooccurrence_isolated_fraction",
]


def extract_features_from_clauses(
    n_vars: int, clauses: Sequence[Sequence[int]]
) -> CNFFeatures:
    """Compute structural features of a CNF formula.

    Definitions (all fractions are in ``[0, 1]`` unless noted):

    * ``alpha``: ``n_clauses / n_vars`` (0.0 when ``n_vars == 0``).
    * Clause length: mean / population std / min / max over clauses,
      plus the Shannon entropy (bits) of the clause-length
      distribution. ``unit/binary/ternary_clause_fraction`` are the
      shares of clauses of length 1 / 2 / 3.
    * ``tautology_clause_fraction``: share of clauses containing both
      ``v`` and ``-v`` for some variable ``v``.
    * ``duplicate_clause_fraction``: ``1 - (#distinct clauses /
      #clauses)``; 0.0 when there are no clauses.
    * ``pos_literal_fraction``: positive literals / all literals.
      ``polarity_balance``: ``(pos - neg) / (pos + neg)`` in ``[-1, 1]``;
      0.0 when there are no literals.
    * Variable occurrence: for each variable, its total degree
      (positive + negative occurrences). Reported as mean / std /
      max, coefficient of variation (``std / mean``), and the Shannon
      entropy (bits) of the normalised degree distribution
      ``p_i = degree_i / total_literals``. The normalised entropy
      divides by ``log2(n_vars)`` (0.0 when ``n_vars <= 1``).
      ``isolated_var_fraction`` is the share of variables with degree
      0; ``singleton_var_fraction`` the share with degree exactly 1.
    * ``pure_literal_fraction``: among variables that occur at all,
      the share occurring with only one polarity. 0.0 when no variable
      occurs.
    * Variable co-occurrence graph: two distinct variables are adjacent
      when they appear together in a clause. Reported as the mean /
      max distinct-neighbour degree, and the share of variables with
      no neighbour (isolated variables count as isolated here too).
    """
    _validate(n_vars, clauses)
    clause_list = [list(c) for c in clauses]
    n_clauses = len(clause_list)

    # --- Clause-length statistics -------------------------------------
    lengths = [len(c) for c in clause_list]
    if n_clauses:
        unit_frac = sum(1 for ln in lengths if ln == 1) / n_clauses
        binary_frac = sum(1 for ln in lengths if ln == 2) / n_clauses
        ternary_frac = sum(1 for ln in lengths if ln == 3) / n_clauses
        length_counts = Counter(lengths)
        length_entropy = _entropy_bits(
            [count / n_clauses for count in length_counts.values()]
        )
    else:
        unit_frac = binary_frac = ternary_frac = length_entropy = 0.0

    tautologies = 0
    seen: Counter[tuple[int, ...]] = Counter()
    for clause in clause_list:
        seen[tuple(sorted(clause))] += 1
        lit_set = set(clause)
        if any(-lit in lit_set for lit in lit_set):
            tautologies += 1
    tautology_frac = tautologies / n_clauses if n_clauses else 0.0
    duplicate_frac = (
        1.0 - len(seen) / n_clauses if n_clauses else 0.0
    )

    # --- Literal polarity and per-variable occurrence ------------------
    pos_degree = [0] * n_vars
    neg_degree = [0] * n_vars
    total_literals = 0
    for clause in clause_list:
        for lit in clause:
            total_literals += 1
            if lit > 0:
                pos_degree[lit - 1] += 1
            else:
                neg_degree[-lit - 1] += 1
    n_pos = sum(pos_degree)
    if total_literals:
        pos_frac = n_pos / total_literals
        polarity_balance = (n_pos - (total_literals - n_pos)) / total_literals
    else:
        pos_frac = polarity_balance = 0.0

    degrees = [pos_degree[i] + neg_degree[i] for i in range(n_vars)]
    if n_vars:
        occ_mean = _mean([float(d) for d in degrees])
        occ_std = _std([float(d) for d in degrees])
        occ_max = float(max(degrees))
        occ_cv = occ_std / occ_mean if occ_mean > 0 else 0.0
        occ_entropy = _entropy_bits(
            [d / total_literals for d in degrees if total_literals > 0]
        )
        occ_entropy_norm = (
            occ_entropy / math.log2(n_vars) if n_vars > 1 else 0.0
        )
        isolated_frac = sum(1 for d in degrees if d == 0) / n_vars
        singleton_frac = sum(1 for d in degrees if d == 1) / n_vars
    else:
        occ_mean = occ_std = occ_max = occ_cv = 0.0
        occ_entropy = occ_entropy_norm = 0.0
        isolated_frac = singleton_frac = 0.0

    occurring = [i for i in range(n_vars) if degrees[i] > 0]
    if occurring:
        pure = sum(
            1 for i in occurring if pos_degree[i] == 0 or neg_degree[i] == 0
        )
        pure_frac = pure / len(occurring)
    else:
        pure_frac = 0.0

    # --- Variable co-occurrence graph ---------------------------------
    neighbours: list[set[int]] = [set() for _ in range(n_vars)]
    for clause in clause_list:
        vs = sorted({abs(lit) - 1 for lit in clause})
        for i, u in enumerate(vs):
            for v in vs[i + 1:]:
                neighbours[u].add(v)
                neighbours[v].add(u)
    co_degrees = [float(len(s)) for s in neighbours]
    if n_vars:
        co_mean = _mean(co_degrees)
        co_max = max(co_degrees)
        co_isolated_frac = sum(1 for d in co_degrees if d == 0) / n_vars
    else:
        co_mean = co_max = co_isolated_frac = 0.0

    return CNFFeatures(
        n_vars=n_vars,
        n_clauses=n_clauses,
        alpha=(n_clauses / n_vars) if n_vars else 0.0,
        clause_len_mean=_mean([float(ln) for ln in lengths]),
        clause_len_std=_std([float(ln) for ln in lengths]),
        clause_len_min=float(min(lengths)) if lengths else 0.0,
        clause_len_max=float(max(lengths)) if lengths else 0.0,
        clause_len_entropy=length_entropy,
        unit_clause_fraction=unit_frac,
        binary_clause_fraction=binary_frac,
        ternary_clause_fraction=ternary_frac,
        tautology_clause_fraction=tautology_frac,
        duplicate_clause_fraction=duplicate_frac,
        pos_literal_fraction=pos_frac,
        polarity_balance=polarity_balance,
        var_occurrence_mean=occ_mean,
        var_occurrence_std=occ_std,
        var_occurrence_max=occ_max,
        var_occurrence_cv=occ_cv,
        var_occurrence_entropy=occ_entropy,
        var_occurrence_entropy_norm=occ_entropy_norm,
        isolated_var_fraction=isolated_frac,
        singleton_var_fraction=singleton_frac,
        pure_literal_fraction=pure_frac,
        cooccurrence_degree_mean=co_mean,
        cooccurrence_degree_max=co_max,
        cooccurrence_isolated_fraction=co_isolated_frac,
    )


def extract_features(instance: CNFInstance) -> CNFFeatures:
    """Compute structural features of a :class:`CNFInstance`."""
    return extract_features_from_clauses(instance.n_vars, instance.clauses)
