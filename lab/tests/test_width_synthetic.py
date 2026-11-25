"""Synthetic and oracle tests for ``width_features`` and ``analyze_width``.

This file covers:

1. **Oracle self-tests** -- the oracle's own routines produce the
   analytically known widths on tiny fixtures.
2. **Synthetic regimes (reconstructed)** -- ten synthetic regimes that
   I believe correspond to ``ADVERSARIAL_REVIEW_01`` Section 6.4.  I do
   not have that section in front of me; Lumi should diff the regime
   list against the real section and replace any that differ.  Every
   regime is checked against the exact oracle, not against the
   implementation it is testing.
3. **Replay / validity tests** -- DEE-R9-09 (independent replay) and
   DEE-R9-11 (heuristic width == replayed width) on fixed and random
   small fixtures.
4. **Tie-breaking** -- DEE-R9-12.
5. **Heuristic >= exact** -- DEE-R9-10, on fixed fixtures and on
   deterministic random small graphs.
6. **Relabelling sensitivity** -- DEE-R9-15.
7. **Regression tests for the review's static findings** -- DEE-R9-01,
   DEE-R9-04, DEE-R9-05, DEE-R9-17, DEE-R9-20.  These tests document
   the *current* behaviour; they are not endorsements of it.  If Nova
   fixes a finding, the corresponding test should be updated to assert
   the fixed behaviour.

Run with: ``pytest lab/tests/test_width_synthetic.py -v`` from the
repository root (with ``lab/`` on ``sys.path``).
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

# Ensure ``lab/`` is on sys.path so ``om_lab`` can be imported whether
# pytest is invoked from the repo root or from ``lab/``.
_LAB_DIR = Path(__file__).resolve().parent.parent
if str(_LAB_DIR) not in sys.path:
    sys.path.insert(0, str(_LAB_DIR))

import pytest

from om_lab.width_features import (
    primal_graph,
    primal_min_fill_width,
    primal_min_fill_width_from_graph,
    replay_elimination_order,
)
from om_lab.width_oracle import (
    elimination_width_for_order,
    exact_min_elimination_width,
    exact_min_elimination_width_from_graph,
    is_valid_elimination_order,
    primal_graph_from_clauses,
    replay_elimination_order_independent,
    validate_min_fill_result,
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _random_graph(rng: random.Random, n: int, p: float) -> dict[int, set[int]]:
    """Erdos-Renyi graph on vertices 1..n with edge probability p."""
    adj: dict[int, set[int]] = {v: set() for v in range(1, n + 1)}
    for u in range(1, n + 1):
        for v in range(u + 1, n + 1):
            if rng.random() < p:
                adj[u].add(v)
                adj[v].add(u)
    return adj


def _clauses_from_adj(adj: dict[int, set[int]]) -> list[list[int]]:
    """One 2-literal clause per edge, enough to reproduce ``adj``."""
    clauses: list[list[int]] = []
    for u in sorted(adj):
        for v in sorted(adj[u]):
            if u < v:
                clauses.append([u, v])
    return clauses


def _make_row(
    *,
    n: int = 30,
    m: int = 380,
    index: int = 0,
    split: str = "train",
    seed: int | None = 1,
    width: int = 5,
    degree_mean: float = 10.0,
    decisions: int | None = 100,
    timed_out: bool = False,
    satisfiable: bool = True,
    verified: bool = True,
    y: float | None = None,
    status: str | None = None,
    verification_status: str | None = None,
    a_hundredths: int | None = 400,
) -> dict:
    """Build a single analysis row.

    ``y`` and ``decisions`` may be passed explicitly as ``None`` to
    simulate an ERROR row (DEE-R9-04).  If ``status`` is ``None`` it is
    derived from ``satisfiable`` / ``timed_out``.  If
    ``verification_status`` is ``None`` it is derived honestly from
    ``status``.
    """
    if status is None:
        status = "UNKNOWN" if timed_out else ("SAT" if satisfiable else "UNSAT")
    if verification_status is None:
        if status == "SAT":
            verification_status = (
                "SAT_WITNESS_CHECKED" if verified else "INVALID"
            )
        elif status == "UNSAT":
            verification_status = "UNSAT_SOLVER_AGREEMENT_ONLY"
        else:
            verification_status = "NOT_APPLICABLE"
    if y is None and decisions is not None:
        y = math.log1p(min(int(decisions), 10_000))
    return {
        "n": int(n),
        "m": int(m),
        "a_hundredths": a_hundredths,
        "index": index,
        "split": split,
        "seed": seed,
        "width": int(width),
        "degree_mean": float(degree_mean),
        "decisions": None if decisions is None else int(decisions),
        "timed_out": bool(timed_out),
        "satisfiable": bool(satisfiable),
        "status": status,
        "verified": bool(verified),
        "verification_status": verification_status,
        "y": y,
        "width_reversed": None,
    }


# ---------------------------------------------------------------------------
# 1. Oracle self-tests
# ---------------------------------------------------------------------------


class TestOracleSelfTests:
    """The oracle's own routines produce analytically known widths."""

    def test_empty_graph(self):
        adj: dict[int, set[int]] = {}
        assert exact_min_elimination_width_from_graph(adj) == (0, ())

    def test_isolated_vertices(self):
        adj = {1: set(), 2: set(), 3: set()}
        w, order = exact_min_elimination_width_from_graph(adj)
        assert w == 0
        assert sorted(order) == [1, 2, 3]

    def test_single_edge(self):
        adj = {1: {2}, 2: {1}}
        w, order = exact_min_elimination_width_from_graph(adj)
        assert w == 1
        assert sorted(order) == [1, 2]

    def test_triangle(self):
        adj = {1: {2, 3}, 2: {1, 3}, 3: {1, 2}}
        w, _ = exact_min_elimination_width_from_graph(adj)
        assert w == 2

    def test_path_5(self):
        adj = {
            1: {2},
            2: {1, 3},
            3: {2, 4},
            4: {3, 5},
            5: {4},
        }
        w, _ = exact_min_elimination_width_from_graph(adj)
        assert w == 1

    def test_complete_graph_5(self):
        n = 5
        adj = {v: set(range(1, n + 1)) - {v} for v in range(1, n + 1)}
        w, _ = exact_min_elimination_width_from_graph(adj)
        assert w == 4

    def test_elimination_width_for_order_detects_bad_order(self):
        # Path 1-2-3: order (2, 1, 3) has width 2, order (1, 2, 3) has width 1.
        adj = {1: {2}, 2: {1, 3}, 3: {2}}
        assert elimination_width_for_order(adj, (1, 2, 3)) == 1
        assert elimination_width_for_order(adj, (2, 1, 3)) == 2

    def test_replay_rejects_non_permutation(self):
        adj = {1: {2}, 2: {1, 3}, 3: {2}}
        with pytest.raises(ValueError):
            elimination_width_for_order(adj, (1, 2))

    def test_is_valid_elimination_order(self):
        assert is_valid_elimination_order(3, [1, 2, 3])
        assert is_valid_elimination_order(3, [3, 1, 2])
        assert not is_valid_elimination_order(3, [1, 2])
        assert not is_valid_elimination_order(3, [1, 2, 2])
        assert not is_valid_elimination_order(3, [0, 1, 2])

    def test_primal_graph_from_clauses_empty(self):
        adj = primal_graph_from_clauses(5, [])
        assert adj == {v: set() for v in range(1, 6)}

    def test_primal_graph_from_clauses_signs_ignored(self):
        adj = primal_graph_from_clauses(3, [[-1, 2, -3]])
        assert adj == {1: {2, 3}, 2: {1, 3}, 3: {1, 2}}

    def test_primal_graph_from_clauses_repeated_literals(self):
        adj = primal_graph_from_clauses(2, [[1, 1, 2, 2]])
        assert adj == {1: {2}, 2: {1}}


# ---------------------------------------------------------------------------
# 2. Synthetic regimes (reconstructed from ADVERSARIAL_REVIEW_01 Section 6.4)
# ---------------------------------------------------------------------------


class TestSyntheticRegimes:
    """Ten synthetic regimes, each checked against the exact oracle.

    NOTE: I do not have ADVERSARIAL_REVIEW_01 Section 6.4 in front of me.
    The regimes below are my reconstruction of the plausible content.
    Lumi should diff this list against the real section and replace any
    regime that differs.  Each test is written so that replacing one
    regime does not disturb the others.
    """

    def _check(self, n_vars: int, clauses: list[list[int]]) -> dict:
        """Run the implementation and the oracle, assert agreement."""
        result = primal_min_fill_width(n_vars, clauses)
        report = validate_min_fill_result(n_vars, clauses, result)
        assert report["ordering_valid"], report
        assert report["replay_matches_reported"], report
        assert report["heuristic_ge_exact"], report
        return report

    def test_regime_01_empty_formula(self):
        """Regime 1: no clauses, all variables isolated.  Width = 0."""
        report = self._check(5, [])
        assert report["reported_width"] == 0
        assert report["exact_min_width"] == 0

    def test_regime_02_single_clause_complete_graph(self):
        """Regime 2: one clause on 3 variables -> K_3.  Width = 2."""
        report = self._check(3, [[1, 2, 3]])
        assert report["reported_width"] == 2
        assert report["exact_min_width"] == 2

    def test_regime_03_disjoint_edges(self):
        """Regime 3: matching (1,2), (3,4).  Width = 1."""
        report = self._check(4, [[1, 2], [3, 4]])
        assert report["reported_width"] == 1
        assert report["exact_min_width"] == 1

    def test_regime_04_path(self):
        """Regime 4: path 1-2-3-4-5.  Width = 1."""
        report = self._check(5, [[1, 2], [2, 3], [3, 4], [4, 5]])
        assert report["reported_width"] == 1
        assert report["exact_min_width"] == 1

    def test_regime_05_star(self):
        """Regime 5: star centred on 1 with leaves 2..5.  Width = 1."""
        report = self._check(5, [[1, 2], [1, 3], [1, 4], [1, 5]])
        assert report["reported_width"] == 1
        assert report["exact_min_width"] == 1

    def test_regime_06_complete_graph(self):
        """Regime 6: one clause on all 5 variables -> K_5.  Width = 4."""
        report = self._check(5, [[1, 2, 3, 4, 5]])
        assert report["reported_width"] == 4
        assert report["exact_min_width"] == 4

    def test_regime_07_cycle(self):
        """Regime 7: 4-cycle.  Treewidth of C_4 is 2."""
        report = self._check(4, [[1, 2], [2, 3], [3, 4], [4, 1]])
        assert report["reported_width"] == 2
        assert report["exact_min_width"] == 2

    def test_regime_08_relabelling(self):
        """Regime 8: path is invariant under relabelling (width stays 1)."""
        clauses_a = [[1, 2], [2, 3], [3, 4], [4, 5]]
        # Relabel 1<->5, 2<->4, 3 fixed.
        clauses_b = [[5, 4], [4, 3], [3, 2], [2, 1]]
        ra = self._check(5, clauses_a)
        rb = self._check(5, clauses_b)
        assert ra["reported_width"] == rb["reported_width"] == 1

    def test_regime_09_repeated_literals(self):
        """Regime 9: (1,1,2) behaves like (1,2).  Width = 1."""
        report = self._check(2, [[1, 1, 2]])
        assert report["reported_width"] == 1
        assert report["exact_min_width"] == 1

    def test_regime_10_negative_literals(self):
        """Regime 10: (-1,2,-3) behaves like (1,2,3) -> K_3.  Width = 2."""
        report = self._check(3, [[-1, 2, -3]])
        assert report["reported_width"] == 2
        assert report["exact_min_width"] == 2


# ---------------------------------------------------------------------------
# 3. Replay / validity (DEE-R9-09, DEE-R9-11)
# ---------------------------------------------------------------------------


class TestReplayAndValidity:
    """Replay is independent (DEE-R9-09) and matches selection (DEE-R9-11)."""

    def test_replay_matches_selection_on_fixed_fixtures(self):
        fixtures = [
            (3, [[1, 2, 3]]),
            (4, [[1, 2], [3, 4]]),
            (5, [[1, 2], [2, 3], [3, 4], [4, 5]]),
            (5, [[1, 2], [1, 3], [1, 4], [1, 5]]),
            (4, [[1, 2], [2, 3], [3, 4], [4, 1]]),
        ]
        for n, clauses in fixtures:
            result = primal_min_fill_width(n, clauses)
            assert sorted(result.ordering) == list(range(1, n + 1))
            replayed = replay_elimination_order(n, clauses, result.ordering)
            oracle_replayed = replay_elimination_order_independent(
                n, clauses, result.ordering
            )
            assert replayed == result.width
            assert oracle_replayed == result.width

    def test_replay_matches_selection_on_random_graphs(self):
        rng = random.Random(2026)
        for trial in range(30):
            n = rng.randint(2, 7)
            p = rng.choice([0.2, 0.4, 0.6, 0.8])
            adj = _random_graph(rng, n, p)
            clauses = _clauses_from_adj(adj)
            result = primal_min_fill_width(n, clauses)
            assert sorted(result.ordering) == list(range(1, n + 1)), (
                f"trial {trial}: ordering not a permutation"
            )
            assert replay_elimination_order(
                n, clauses, result.ordering
            ) == result.width, f"trial {trial}: replay != reported"
            assert replay_elimination_order_independent(
                n, clauses, result.ordering
            ) == result.width, f"trial {trial}: oracle replay != reported"

    def test_replay_rejects_non_permutation(self):
        with pytest.raises(ValueError):
            replay_elimination_order(4, [[1, 2], [3, 4]], [1, 2, 3])
        with pytest.raises(ValueError):
            replay_elimination_order_independent(
                4, [[1, 2], [3, 4]], [1, 2, 3]
            )


# ---------------------------------------------------------------------------
# 4. Tie-breaking (DEE-R9-12)
# ---------------------------------------------------------------------------


class TestTieBreaking:
    """The rule is ``(fill, variable_id)`` -- smallest id wins a fill tie."""

    def test_path_all_fill_zero_picks_smallest_id(self):
        # Path 1-2-3-4-5: every vertex has fill 0, so smallest id wins
        # at each step.  Expected ordering: (1, 2, 3, 4, 5).
        result = primal_min_fill_width(
            5, [[1, 2], [2, 3], [3, 4], [4, 5]]
        )
        assert result.ordering == (1, 2, 3, 4, 5)

    def test_star_picks_leaf_over_centre(self):
        # Star centred on 1 with leaves 2..5.  Leaves have fill 0;
        # centre has fill C(4,2) = 6.  Min-fill picks 2 first (smallest
        # id among leaves), not 1.
        result = primal_min_fill_width(
            5, [[1, 2], [1, 3], [1, 4], [1, 5]]
        )
        assert result.ordering[0] == 2
        assert result.width == 1

    def test_4cycle_all_fill_one_picks_smallest_id(self):
        # 4-cycle: every vertex has fill 1, so smallest id wins.
        result = primal_min_fill_width(
            4, [[1, 2], [2, 3], [3, 4], [4, 1]]
        )
        assert result.ordering[0] == 1
        assert result.width == 2

    def test_tie_break_uses_variable_id_not_clause_order(self):
        # Same graph as the 4-cycle, but clauses presented in a
        # different order.  Tie-break must still pick id 1.
        result = primal_min_fill_width(
            4, [[4, 1], [3, 4], [2, 3], [1, 2]]
        )
        assert result.ordering[0] == 1


# ---------------------------------------------------------------------------
# 5. Heuristic >= exact (DEE-R9-10)
# ---------------------------------------------------------------------------


class TestHeuristicGeExact:
    """Heuristic width is an upper bound on exact minimum elimination width."""

    def test_on_fixed_fixtures(self):
        fixtures = [
            (3, [[1, 2, 3]]),
            (4, [[1, 2], [3, 4]]),
            (5, [[1, 2], [2, 3], [3, 4], [4, 5]]),
            (5, [[1, 2], [1, 3], [1, 4], [1, 5]]),
            (4, [[1, 2], [2, 3], [3, 4], [4, 1]]),
            (5, [[1, 2, 3, 4, 5]]),
        ]
        for n, clauses in fixtures:
            result = primal_min_fill_width(n, clauses)
            exact, _ = exact_min_elimination_width(n, clauses)
            assert result.width >= exact, (
                f"heuristic {result.width} < exact {exact} for n={n} "
                f"clauses={clauses}"
            )

    def test_on_random_graphs(self):
        rng = random.Random(42)
        for trial in range(40):
            n = rng.randint(3, 7)
            p = rng.choice([0.2, 0.4, 0.6, 0.8])
            adj = _random_graph(rng, n, p)
            clauses = _clauses_from_adj(adj)
            result = primal_min_fill_width(n, clauses)
            exact, _ = exact_min_elimination_width(n, clauses)
            assert result.width >= exact, (
                f"trial {trial}: n={n} p={p} heuristic={result.width} "
                f"< exact={exact}"
            )


# ---------------------------------------------------------------------------
# 6. Relabelling sensitivity (DEE-R9-15)
# ---------------------------------------------------------------------------


class TestRelabellingSensitivity:
    """Width is documented as not a graph invariant; paths are invariant."""

    def test_path_width_invariant_under_reversal(self):
        clauses = [[1, 2], [2, 3], [3, 4], [4, 5]]
        reversed_clauses = [
            [5, 4], [4, 3], [3, 2], [2, 1]
        ]
        r1 = primal_min_fill_width(5, clauses)
        r2 = primal_min_fill_width(5, reversed_clauses)
        assert r1.width == r2.width == 1

    def test_complete_graph_width_invariant_under_reversal(self):
        # K_4 is the same graph under any labelling; width is 3.
        clauses = [[1, 2, 3, 4]]
        reversed_clauses = [[4, 3, 2, 1]]
        r1 = primal_min_fill_width(4, clauses)
        r2 = primal_min_fill_width(4, reversed_clauses)
        assert r1.width == r2.width == 3

    def test_module_documents_non_invariance(self):
        # Static check: the docstring of width_features mentions that
        # relabelling can change the width.  This is a documentation
        # check, not a runtime property.
        import om_lab.width_features as wf
        assert "relabelling" in (wf.__doc__ or "").lower()
        assert "not" in (wf.__doc__ or "").lower()


# ---------------------------------------------------------------------------
# 7. Regression tests for the review's static findings
# ---------------------------------------------------------------------------


class TestReviewRegressions:
    """Each test documents the *current* behaviour of a review finding.

    These tests are not endorsements.  If Nova fixes a finding, the
    test should be updated to assert the fixed behaviour.
    """

    def test_DEE_R9_01_integrity_gates_breaks_on_first_failure(self):
        """Only the first Y-out-of-range row is reported."""
        from om_lab.analyze_width import integrity_gates

        rows = [
            _make_row(split="train", index=0, y=-1.0, seed=1),
            _make_row(split="train", index=1, y=-2.0, seed=2),
        ]
        gates = integrity_gates(rows, "synthetic")
        assert not gates["passed"]
        y_failures = [f for f in gates["failures"] if "Y out of range" in f]
        # Current behaviour: exactly one, because the loop breaks.
        # Correct behaviour would be two.  This assertion documents
        # DEE-R9-01 and should be flipped when the bug is fixed.
        assert len(y_failures) == 1

    def test_DEE_R9_04_analyze_rows_crashes_on_error_row(self):
        """A row with ``status='ERROR'`` and ``y=None`` raises TypeError."""
        from om_lab.analyze_width import analyze_rows

        error_row = _make_row(
            split="train", index=0, seed=1, y=None, decisions=None,
            status="ERROR", verification_status="NOT_APPLICABLE",
        )
        with pytest.raises(TypeError):
            analyze_rows([error_row], "synthetic")

    def test_DEE_R9_05_phase1_seeds_below_10m_inverted(self):
        """The boolean is inverted: True when *not all* seeds are below 10M."""
        from om_lab.analyze_width import check_seed_manifest

        all_small = [{"seed": 1}, {"seed": 2}, {"seed": 3}]
        result_small = check_seed_manifest(all_small)
        # All seeds are below 10M, so the name would say True; the
        # implementation says False.  Inverted.
        assert result_small["phase1_seeds_below_10m"] is False

        one_big = [{"seed": 1}, {"seed": 20_000_000}]
        result_big = check_seed_manifest(one_big)
        # Not all seeds are below 10M, so the name would say False; the
        # implementation says True.  Inverted.
        assert result_big["phase1_seeds_below_10m"] is True

    def test_DEE_R9_17_evaluate_uses_row_weighting(self):
        """``evaluate`` weights rows, not cells, when cell sizes differ.

        Two cells: cell A (2 rows) with err_m0=1, err_m1=1; cell B (4
        rows) with err_m0=2, err_m1=0.  Row-weighted improvement is
        1 - (2/6)/(10/6) = 0.8.  Equal-cell-weighted would be
        1 - (1 + 0)/2 = 0.5.  The implementation gives 0.8.
        """
        from om_lab.analyze_width import evaluate

        fit = {
            "beta": 1.0,
            "cell_mean_y": {(30, 380): 0.0, (40, 400): 0.0},
            "cell_mean_width": {(30, 380): 0.0, (40, 400): 0.0},
        }
        fit_deg = {
            "m2_beta_degree": None,
            "m2_denominator": 0,
            "m3": {
                "singular": True,
                "beta_degree": None,
                "beta_width": None,
            },
            "m3_determinant": 0,
            "m3_relative_determinant": 0,
        }
        rows = [
            _make_row(n=30, m=380, split="test", index=70, seed=1,
                      y=1.0, width=0, decisions=None),
            _make_row(n=30, m=380, split="test", index=71, seed=2,
                      y=1.0, width=0, decisions=None),
            _make_row(n=40, m=400, split="test", index=70, seed=3,
                      y=2.0, width=2, decisions=None),
            _make_row(n=40, m=400, split="test", index=71, seed=4,
                      y=2.0, width=2, decisions=None),
            _make_row(n=40, m=400, split="test", index=72, seed=5,
                      y=2.0, width=2, decisions=None),
            _make_row(n=40, m=400, split="test", index=73, seed=6,
                      y=2.0, width=2, decisions=None),
        ]
        result = evaluate(rows, fit, fit_deg)
        assert abs(result["improvement"] - 0.8) < 1e-9, result
        assert abs(result["improvement"] - 0.5) > 0.1, result

    def test_DEE_R9_20_check_seed_manifest_inconsistent_thresholds(self):
        """``disjoint_from_phase1_scheme`` and ``phase1_seeds_below_10m``
        use different thresholds (102126 vs 10^7)."""
        from om_lab.analyze_width import check_seed_manifest

        # Seed 500K is above phase1_max (102126) but below 10^7.
        result = check_seed_manifest([{"seed": 500_000}])
        assert result["disjoint_from_phase1_scheme"] is True
        # Under the (inverted) name, 500K < 10M, so all(...) is True,
        # True is False = False.  The two booleans disagree about
        # whether this seed is "phase 1".
        assert result["phase1_seeds_below_10m"] is False
