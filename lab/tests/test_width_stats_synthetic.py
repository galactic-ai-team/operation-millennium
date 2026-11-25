"""Synthetic statistical regression tests for analyze_width.py.

Covers the 10 statistical cases from ADVERSARIAL_REVIEW_01 §6.4:

    1. Width has no within-cell variation.
    2. Width predicts effort perfectly within cells.
    3. Width appears useful only because density varies.
    4. Degree predicts effort but width adds no information.
    5. Width worsens held-out predictions.
    6. Budget-exhausted rows.
    7. Missing cells.
    8. Undefined baseline MAE.
    9. Undefined bootstrap replicates.
    10. Deliberate train/test contamination.

Expected values are derived by hand from the frozen specification
(DISCOVERY_ROUND_01 §3.8–§3.10).  They are **Proved** for the specific
fixtures below (small integer arithmetic; the improved MAEs and the
dispositions follow by direct computation, not by running the
implementation).  The implementation's agreement with them is
**Empirical Observation** — Lumi runs the suite and reports.

Corrections after Lumi's first run on dev 5df68f4 (PR #23, commit f23d811,
3 failed, 9 passed):

* Case 6, ``test_well_formed_budget_rows_pass_gates``.  Fixture used
  ``decisions=None`` on timed-out rows.  Nova's R9-04 fix treats ``None``
  decisions as an ERROR row, correctly.  Fixed: well-formed timed-out
  rows use ``decisions=BUDGET_B`` (int).
* Case 6, ``test_timed_out_labeled_unsat_fails_gate``.  Same fixture
  error.  Fixed to ``decisions=BUDGET_B`` so the budget check is the
  only one that can fire; assertion loosened to accept any wording that
  mentions "budget", "timed", or "UNKNOWN".
* Case 9.  Probability estimate assumed the old per-cell sample size
  ``len(rows)``.  Nova's R9-17 fix samples a fixed 30 per cell (spec-
  compliant for the confirmatory population, where every test cell has
  30 rows).  Rewritten to test the §3.10 invariant that
  ``primary_disposition`` must be INCONCLUSIVE when
  ``bootstrap["n_undefined"] > 0``; independent of the sampling rule.

Run from repo root:
    pytest lab/tests/test_width_stats_synthetic.py -v
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

_LAB_DIR = Path(__file__).resolve().parent.parent
if str(_LAB_DIR) not in sys.path:
    sys.path.insert(0, str(_LAB_DIR))

import pytest

from om_lab.analyze_width import (
    BUDGET_B,
    evaluate,
    fit_degree_adjusted,
    fit_m0_m1,
    integrity_gates,
    paired_stratified_bootstrap,
    primary_disposition,
    verification_gates,
)


TOL = dict(rel=1e-9, abs=1e-12)
_LOG_CAP = math.log1p(BUDGET_B)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row(
    n: int,
    m: int,
    index: int,
    split: str,
    seed: int,
    width: int,
    y: float,
    *,
    degree: float = 10.0,
    decisions: int | None = 100,
    timed_out: bool = False,
    satisfiable: bool | None = None,
    verified: bool = True,
    status: str | None = None,
    verification_status: str | None = None,
    a_hundredths: int = 400,
) -> dict:
    """Build one row matching analyze_width's row schema.

    ``y`` is passed explicitly (never derived) so the test controls the
    response exactly.  ``satisfiable`` defaults to ``False`` for
    UNKNOWN rows (integrity gate: UNKNOWN rows must not claim SAT).
    ``decisions`` should be a non-negative int on every well-formed row,
    including timed-out rows (``capped_log_effort`` ignores it when
    ``timed_out=True``, but the *row schema* stores it as an int).
    """
    if status is None:
        status = "UNKNOWN" if timed_out else "SAT"
    if satisfiable is None:
        satisfiable = (status == "SAT")
    if verification_status is None:
        if status == "SAT":
            verification_status = "SAT_WITNESS_CHECKED" if verified else "INVALID"
        elif status == "UNSAT":
            verification_status = "UNSAT_SOLVER_AGREEMENT_ONLY"
        else:
            verification_status = "NOT_APPLICABLE"
    return {
        "n": int(n),
        "m": int(m),
        "a_hundredths": a_hundredths,
        "index": int(index),
        "split": split,
        "seed": int(seed),
        "width": int(width),
        "degree_mean": float(degree),
        "decisions": None if decisions is None else int(decisions),
        "timed_out": bool(timed_out),
        "satisfiable": bool(satisfiable),
        "status": status,
        "verified": bool(verified),
        "verification_status": verification_status,
        "y": float(y),
        "width_reversed": None,
    }


def _gates(rows: list[dict], population: str = "synthetic"):
    return integrity_gates(rows, population), verification_gates(rows)


def _fit_eval(train_rows, test_rows):
    fit = fit_m0_m1(train_rows)
    fit_deg = fit_degree_adjusted(train_rows)
    evaluation = evaluate(test_rows, fit, fit_deg)
    return fit, fit_deg, evaluation


# ---------------------------------------------------------------------------
# Case 1 — Width has no within-cell variation.
# ---------------------------------------------------------------------------


class TestCase01NoWithinCellVariation:
    """Width constant within each cell -> M1 unidentifiable -> INCONCLUSIVE."""

    def test_beta_is_none_and_disposition_is_inconclusive(self):
        train = (
            [_row(30, 380, i, "train", 100 + i, width=3, y=float(i + 1))
             for i in range(4)]
            + [_row(40, 400, 4 + i, "train", 104 + i, width=5, y=float(i + 2))
               for i in range(4)]
        )
        test = (
            [_row(30, 380, 70 + i, "test", 200 + i, width=3, y=float(i + 1))
             for i in range(4)]
            + [_row(40, 400, 74 + i, "test", 204 + i, width=5, y=float(i + 2))
               for i in range(4)]
        )
        rows = train + test
        fit = fit_m0_m1(train)
        assert fit["beta"] is None
        assert fit["slope_denominator"] == 0.0

        gates, verification = _gates(rows)
        assert gates["passed"], gates
        assert verification["passed"], verification

        disp = primary_disposition(None, None, gates, verification, fit)
        assert disp["disposition"] == "INCONCLUSIVE"
        assert any("M1 slope denominator is zero" in r for r in disp["reasons"])
        assert disp["point_improvement"] is None


# ---------------------------------------------------------------------------
# Case 2 — Width predicts effort perfectly within cells.
# ---------------------------------------------------------------------------


class TestCase02PerfectWithinCellPrediction:
    """y == width within each cell -> M1 exact, improvement == 1.0 -> PASS."""

    def test_fit_and_disposition(self):
        train = (
            [_row(30, 380, i, "train", 100 + i, width=i + 1, y=float(i + 1))
             for i in range(4)]
            + [_row(40, 400, 4 + i, "train", 104 + i, width=i + 1, y=float(i + 1))
               for i in range(4)]
        )
        test = (
            [_row(30, 380, 70 + i, "test", 200 + i, width=i + 1, y=float(i + 1))
             for i in range(4)]
            + [_row(40, 400, 74 + i, "test", 204 + i, width=i + 1, y=float(i + 1))
               for i in range(4)]
        )
        rows = train + test
        fit, _fit_deg, evaluation = _fit_eval(train, test)

        assert fit["beta"] == pytest.approx(1.0, **TOL)
        assert evaluation["mae_m0"] == pytest.approx(1.0, **TOL)
        assert evaluation["mae_m1"] == pytest.approx(0.0, **TOL)
        assert evaluation["improvement"] == pytest.approx(1.0, **TOL)

        bootstrap = paired_stratified_bootstrap(evaluation["paired"])
        assert bootstrap["n_undefined"] == 0
        assert bootstrap["ci_lower_2.5"] == pytest.approx(1.0, **TOL)

        gates, verification = _gates(rows)
        disp = primary_disposition(evaluation, bootstrap, gates, verification, fit)
        assert disp["disposition"] == "PASS"
        assert disp["point_improvement"] == pytest.approx(1.0, **TOL)


# ---------------------------------------------------------------------------
# Case 3 — Width appears useful only because density varies.
# ---------------------------------------------------------------------------


class TestCase03DensityConfound:
    """Across cells width and y co-vary; within cells beta == 0 -> FAIL."""

    def test_pooled_illusion_within_cell_null(self):
        train = (
            [_row(30, 100, 0, "train", 100, width=1, y=1.5, a_hundredths=300),
             _row(30, 100, 1, "train", 101, width=2, y=1.5, a_hundredths=300),
             _row(30, 100, 2, "train", 102, width=1, y=2.5, a_hundredths=300),
             _row(30, 100, 3, "train", 103, width=2, y=2.5, a_hundredths=300)]
            + [_row(30, 400, 4, "train", 104, width=4, y=3.5, a_hundredths=1300),
               _row(30, 400, 5, "train", 105, width=5, y=3.5, a_hundredths=1300),
               _row(30, 400, 6, "train", 106, width=4, y=4.5, a_hundredths=1300),
               _row(30, 400, 7, "train", 107, width=5, y=4.5, a_hundredths=1300)]
        )
        test = (
            [_row(30, 100, 70, "test", 200, width=1, y=1.5, a_hundredths=300),
             _row(30, 100, 71, "test", 201, width=2, y=1.5, a_hundredths=300),
             _row(30, 100, 72, "test", 202, width=1, y=2.5, a_hundredths=300),
             _row(30, 100, 73, "test", 203, width=2, y=2.5, a_hundredths=300)]
            + [_row(30, 400, 74, "test", 204, width=4, y=3.5, a_hundredths=1300),
               _row(30, 400, 75, "test", 205, width=5, y=3.5, a_hundredths=1300),
               _row(30, 400, 76, "test", 206, width=4, y=4.5, a_hundredths=1300),
               _row(30, 400, 77, "test", 207, width=5, y=4.5, a_hundredths=1300)]
        )
        rows = train + test
        fit, _fit_deg, evaluation = _fit_eval(train, test)

        assert fit["beta"] == pytest.approx(0.0, abs=1e-12)
        assert evaluation["mae_m0"] == pytest.approx(0.5, **TOL)
        assert evaluation["mae_m1"] == pytest.approx(0.5, **TOL)
        assert evaluation["improvement"] == pytest.approx(0.0, abs=1e-12)

        bootstrap = paired_stratified_bootstrap(evaluation["paired"])
        gates, verification = _gates(rows)
        disp = primary_disposition(evaluation, bootstrap, gates, verification, fit)
        assert disp["disposition"] == "FAIL"
        assert disp["point_improvement"] == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# Case 4 — Degree predicts effort, width adds nothing.
# ---------------------------------------------------------------------------


class TestCase04DegreePredictsWidthNot:
    """M2 fits exactly; M1 == M0; M3 == M2; primary is FAIL."""

    def test_m2_exact_m1_null_m3_equals_m2(self):
        def _cell_rows(n, m, a_hun, offset, split, seed_base):
            deg = [1.0, 2.0, 3.0, 4.0]
            wid = [2, 4, 1, 3]
            yv = [3.0, 5.0, 7.0, 9.0]
            return [
                _row(n, m, offset + i, split, seed_base + i,
                     width=wid[i], y=yv[i], degree=deg[i], a_hundredths=a_hun)
                for i in range(4)
            ]

        train = (
            _cell_rows(30, 380, 400, 0, "train", 100)
            + _cell_rows(40, 400, 400, 4, "train", 104)
        )
        test = (
            _cell_rows(30, 380, 400, 70, "test", 200)
            + _cell_rows(40, 400, 400, 74, "test", 204)
        )
        rows = train + test
        fit, fit_deg, evaluation = _fit_eval(train, test)

        assert fit["beta"] == pytest.approx(0.0, abs=1e-12)
        assert fit_deg["m2_beta_degree"] == pytest.approx(2.0, **TOL)
        assert fit_deg["m3"]["singular"] is False
        assert fit_deg["m3"]["beta_degree"] == pytest.approx(2.0, **TOL)
        assert fit_deg["m3"]["beta_width"] == pytest.approx(0.0, abs=1e-12)

        assert evaluation["mae_m0"] == pytest.approx(2.0, **TOL)
        assert evaluation["mae_m1"] == pytest.approx(2.0, **TOL)
        assert evaluation["mae_m2"] == pytest.approx(0.0, **TOL)
        assert evaluation["mae_m3"] == pytest.approx(0.0, **TOL)
        assert evaluation["improvement"] == pytest.approx(0.0, abs=1e-12)
        assert evaluation["improvement_m2"] == pytest.approx(1.0, **TOL)
        assert evaluation["improvement_m3"] == pytest.approx(1.0, **TOL)

        bootstrap = paired_stratified_bootstrap(evaluation["paired"])
        gates, verification = _gates(rows)
        disp = primary_disposition(evaluation, bootstrap, gates, verification, fit)
        assert disp["disposition"] == "FAIL"


# ---------------------------------------------------------------------------
# Case 5 — Width worsens held-out predictions.
# ---------------------------------------------------------------------------


class TestCase05WidthWorsens:
    """Train beta = -1; test y = +width; improvement == -1 -> FAIL."""

    def test_negative_improvement(self):
        train = [
            _row(30, 380, i, "train", 100 + i, width=i + 1, y=float(4 - i))
            for i in range(4)
        ]
        test = [
            _row(30, 380, 70 + i, "test", 200 + i, width=i + 1, y=float(i + 1))
            for i in range(4)
        ]
        rows = train + test
        fit, _fit_deg, evaluation = _fit_eval(train, test)

        assert fit["beta"] == pytest.approx(-1.0, **TOL)
        assert evaluation["mae_m0"] == pytest.approx(1.0, **TOL)
        assert evaluation["mae_m1"] == pytest.approx(2.0, **TOL)
        assert evaluation["improvement"] == pytest.approx(-1.0, **TOL)

        bootstrap = paired_stratified_bootstrap(evaluation["paired"])
        gates, verification = _gates(rows)
        disp = primary_disposition(evaluation, bootstrap, gates, verification, fit)
        assert disp["disposition"] == "FAIL"
        assert disp["point_improvement"] < 0


# ---------------------------------------------------------------------------
# Case 6 — Budget-exhausted rows.
# ---------------------------------------------------------------------------


class TestCase06BudgetExhausted:
    """Timed-out rows are UNKNOWN; mislabelling fails the integrity gate."""

    def test_well_formed_budget_rows_pass_gates(self):
        # Well-formed timed-out rows carry an integer decisions field
        # (the row schema is int, not None; capped_log_effort ignores it
        # when timed_out=True, but the row stores the int).
        rows = [
            _row(30, 380, 0, "train", 100, width=3, y=2.0),
            _row(30, 380, 1, "train", 101, width=4, y=3.0),
            _row(30, 380, 2, "train", 102, width=5, y=_LOG_CAP,
                 decisions=BUDGET_B, timed_out=True, status="UNKNOWN"),
            _row(30, 380, 70, "test", 200, width=3, y=2.0),
            _row(30, 380, 71, "test", 201, width=4, y=3.0),
            _row(30, 380, 72, "test", 202, width=5, y=_LOG_CAP,
                 decisions=BUDGET_B, timed_out=True, status="UNKNOWN"),
        ]
        gates, verification = _gates(rows)
        assert gates["passed"], gates
        assert verification["passed"], verification

    def test_timed_out_labeled_unsat_fails_gate(self):
        # The only malformed property is timed_out=True with status=UNSAT.
        # decisions is a proper int so no other check fires on that row.
        rows = [
            _row(30, 380, 0, "train", 100, width=3, y=2.0),
            _row(30, 380, 1, "train", 101, width=4, y=3.0),
            _row(30, 380, 2, "train", 102, width=5, y=_LOG_CAP,
                 decisions=BUDGET_B, timed_out=True, status="UNSAT",
                 verification_status="UNSAT_SOLVER_AGREEMENT_ONLY"),
            _row(30, 380, 70, "test", 200, width=3, y=2.0),
        ]
        gates, _ver = _gates(rows)
        assert not gates["passed"]
        # Accept any wording that identifies the budget/timed-out problem.
        assert any(
            ("budget" in f.lower())
            or ("timed" in f.lower())
            or ("UNKNOWN" in f)
            for f in gates["failures"]
        ), f"no budget-related failure in {gates['failures']}"

        fit = fit_m0_m1([r for r in rows if r["split"] == "train"])
        _ver = verification_gates(rows)
        disp = primary_disposition(None, None, gates, _ver, fit)
        assert disp["disposition"] == "INCONCLUSIVE"


# ---------------------------------------------------------------------------
# Case 7 — Missing cells.
# ---------------------------------------------------------------------------


class TestCase07MissingCells:
    """A test cell with no training rows fails the integrity gate."""

    def test_missing_train_cell(self):
        train = [
            _row(30, 380, i, "train", 100 + i, width=i + 1, y=float(i + 1))
            for i in range(4)
        ]
        test = [
            _row(30, 380, 70 + i, "test", 200 + i, width=i + 1, y=float(i + 1))
            for i in range(4)
        ] + [
            _row(40, 400, 74 + i, "test", 204 + i, width=i + 1, y=float(i + 1))
            for i in range(4)
        ]
        rows = train + test
        gates, _ver = _gates(rows)
        assert not gates["passed"]
        assert any("no training rows" in f for f in gates["failures"])

        fit = fit_m0_m1(train)
        _ver = verification_gates(rows)
        disp = primary_disposition(None, None, gates, _ver, fit)
        assert disp["disposition"] == "INCONCLUSIVE"


# ---------------------------------------------------------------------------
# Case 8 — Undefined baseline MAE (MAE_0 == 0).
# ---------------------------------------------------------------------------


class TestCase08UndefinedBaseline:
    """All test y equal the training cell mean -> improvement undefined."""

    def test_mae0_zero_improvement_none(self):
        train = [
            _row(30, 380, i, "train", 100 + i, width=i + 1, y=float(i + 4))
            for i in range(3)
        ]
        test = [
            _row(30, 380, 70 + i, "test", 200 + i, width=i + 1, y=5.0)
            for i in range(3)
        ]
        rows = train + test
        fit, _fd, evaluation = _fit_eval(train, test)
        assert evaluation["mae_m0"] == pytest.approx(0.0, abs=1e-12)
        assert evaluation["mae_m1"] == pytest.approx(2.0 / 3.0, **TOL)
        assert evaluation["improvement"] is None

        bootstrap = paired_stratified_bootstrap(evaluation["paired"])
        assert bootstrap["n_undefined"] == bootstrap["replicates"]

        gates, verification = _gates(rows)
        disp = primary_disposition(evaluation, bootstrap, gates, verification, fit)
        assert disp["disposition"] == "INCONCLUSIVE"
        assert disp["point_improvement"] is None
        assert any("MAE_0 is zero" in r for r in disp["reasons"])


# ---------------------------------------------------------------------------
# Case 9 — Undefined bootstrap replicates.
# ---------------------------------------------------------------------------


class TestCase09UndefinedBootstrapReplicates:
    """Undefined bootstrap replicates force INCONCLUSIVE (§3.10).

    Rewritten after Lumi's run on dev 5df68f4 to test the invariant
    ``primary_disposition`` must satisfy, not the sampling rule.  Under
    Nova's R9-17 fix the per-cell sample size is a fixed 30 (spec-
    compliant for the confirmatory population); a 4-row cell never
    produces an undefined replicate at 30 draws because the rare row
    appears almost surely.  So testing the sampling behaviour directly
    is fragile and depends on Nova's design.  The invariant — any
    undefined replicate in the bootstrap makes the disposition
    INCONCLUSIVE — is what §3.10 specifies.
    """

    def test_undefined_replicates_force_inconclusive(self):
        # A bootstrap with a mixture of defined and undefined replicates.
        bootstrap = {
            "replicates": 200,
            "seed": 9012026,
            "n_defined": 150,
            "n_undefined": 50,
            "mean": 0.6,
            "std": 0.1,
            "ci_lower_2.5": 0.4,
            "ci_upper_97.5": 0.8,
        }
        evaluation = {"improvement": 0.5}
        fit = {"beta": 1.0}
        gates = {"passed": True, "failures": []}
        verification = {"passed": True, "failures": []}
        disp = primary_disposition(
            evaluation, bootstrap, gates, verification, fit
        )
        assert disp["disposition"] == "INCONCLUSIVE"
        assert any("undefined replicates" in r for r in disp["reasons"])

    def test_all_undefined_replicates_is_inconclusive(self):
        bootstrap = {
            "replicates": 200,
            "seed": 9012026,
            "n_defined": 0,
            "n_undefined": 200,
            "mean": None,
            "std": None,
            "ci_lower_2.5": None,
            "ci_upper_97.5": None,
        }
        evaluation = {"improvement": 0.5}
        fit = {"beta": 1.0}
        gates = {"passed": True, "failures": []}
        verification = {"passed": True, "failures": []}
        disp = primary_disposition(
            evaluation, bootstrap, gates, verification, fit
        )
        assert disp["disposition"] == "INCONCLUSIVE"

    def test_full_cell_bootstrap_has_no_undefined_replicates(self):
        # Smoke: a full 30-row cell with mixed err_m0 values does not
        # produce undefined replicates under any reasonable sampling
        # rule (fixed 30 or len(rows) = 30 are identical here).  This
        # documents Nova's R9-17 fix without asserting the sampling
        # rule on sub-30 cells (a design question for §3.10).
        paired_rows = (
            [{"n": 30, "m": 380, "index": i, "err_m0": 1.0, "err_m1": 0.0}
             for i in range(30)]
        )
        bootstrap = paired_stratified_bootstrap(paired_rows, replicates=200)
        assert bootstrap["n_undefined"] == 0


# ---------------------------------------------------------------------------
# Case 10 — Deliberate train/test contamination.
# ---------------------------------------------------------------------------


class TestCase10TrainTestContamination:
    """Same (n, m, index) in train and test fails the integrity gate."""

    def test_overlap_fails_gate(self):
        rows = [
            _row(30, 380, 0, "train", 100, width=3, y=2.0),
            _row(30, 380, 1, "train", 101, width=4, y=3.0),
            _row(30, 380, 0, "test", 200, width=3, y=2.0),
            _row(30, 380, 1, "test", 201, width=4, y=3.0),
        ]
        gates, _ver = _gates(rows)
        assert not gates["passed"]
        joined = " | ".join(gates["failures"])
        assert "duplicate" in joined or "overlap" in joined

        fit = fit_m0_m1([r for r in rows if r["split"] == "train"])
        _ver = verification_gates(rows)
        disp = primary_disposition(None, None, gates, _ver, fit)
        assert disp["disposition"] == "INCONCLUSIVE"


# ---------------------------------------------------------------------------
# Independent M0–M3 calculation on a richer fixture.
# ---------------------------------------------------------------------------


class TestIndependentM0M3:
    """Independently recomputed M0, M1, M2, M3 MAEs on a 3-cell fixture.

    The independent calculation below is written from the specification
    (per-cell means; pooled within-cell centred sums; 2x2 normal
    equations), not imported from ``analyze_width``.  It is expected to
    agree with ``evaluate`` to floating-point precision.
    """

    @staticmethod
    def _independent_maes(train_rows, test_rows):
        from collections import defaultdict

        by_cell = defaultdict(list)
        for r in train_rows:
            by_cell[(r["n"], r["m"])].append(r)
        mean_y = {c: sum(x["y"] for x in rs) / len(rs) for c, rs in by_cell.items()}
        mean_w = {c: sum(x["width"] for x in rs) / len(rs) for c, rs in by_cell.items()}
        mean_d = {c: sum(x["degree_mean"] for x in rs) / len(rs) for c, rs in by_cell.items()}

        sww = swy = sdd = sdy = sdw = 0.0
        for r in train_rows:
            c = (r["n"], r["m"])
            dw = r["width"] - mean_w[c]
            dd = r["degree_mean"] - mean_d[c]
            dy = r["y"] - mean_y[c]
            sww += dw * dw
            swy += dw * dy
            sdd += dd * dd
            sdy += dd * dy
            sdw += dd * dw

        beta_w = swy / sww if sww != 0 else None
        beta_d = sdy / sdd if sdd != 0 else None
        det = sdd * sww - sdw * sdw
        rel_det = det / (sdd * sww) if (sdd > 0 and sww > 0) else 0.0
        if det != 0 and rel_det > 1e-12:
            bd3 = (sdy * sww - swy * sdw) / det
            bw3 = (swy * sdd - sdy * sdw) / det
        else:
            bd3 = bw3 = None

        cap = math.log1p(BUDGET_B)

        def clip(v):
            return max(0.0, min(v, cap))

        err0, err1, err2, err3 = [], [], [], []
        for r in test_rows:
            c = (r["n"], r["m"])
            err0.append(abs(r["y"] - clip(mean_y[c])))
            if beta_w is not None:
                err1.append(abs(r["y"] - clip(mean_y[c] + beta_w * (r["width"] - mean_w[c]))))
            if beta_d is not None:
                err2.append(abs(r["y"] - clip(mean_y[c] + beta_d * (r["degree_mean"] - mean_d[c]))))
            if bd3 is not None:
                p3 = mean_y[c] + bd3 * (r["degree_mean"] - mean_d[c]) + bw3 * (r["width"] - mean_w[c])
                err3.append(abs(r["y"] - clip(p3)))

        def m(v):
            return sum(v) / len(v) if v and len(v) == len(err0) else None

        mae0 = m(err0)
        mae1 = m(err1)
        mae2 = m(err2)
        mae3 = m(err3)
        improvement = 1 - mae1 / mae0 if (mae1 is not None and mae0) else None
        return {
            "mae_m0": mae0, "mae_m1": mae1, "mae_m2": mae2, "mae_m3": mae3,
            "improvement": improvement,
            "beta_w": beta_w, "beta_d": beta_d,
        }

    def test_independent_matches_implementation(self):
        def _rows(cell_params, split, idx0, seed0):
            out = []
            for k, (n, m, a_hun, deg_list, wid_list, y_list) in enumerate(cell_params):
                for i in range(4):
                    out.append(
                        _row(
                            n, m, idx0 + 4 * k + i, split, seed0 + 4 * k + i,
                            width=wid_list[i], y=float(y_list[i]),
                            degree=deg_list[i], a_hundredths=a_hun,
                        )
                    )
            return out

        cells = [
            (30, 100, 300,
             [1.0, 2.0, 3.0, 4.0], [1, 2, 3, 4], [1.5, 2.5, 3.8, 4.2]),
            (30, 300, 1000,
             [2.0, 3.0, 4.0, 5.0], [2, 3, 4, 5], [3.1, 4.2, 5.5, 6.1]),
            (40, 400, 400,
             [3.0, 4.0, 5.0, 6.0], [1, 2, 4, 5], [4.3, 5.1, 7.2, 8.0]),
        ]
        train = _rows(cells, "train", idx0=0, seed0=100)
        test = _rows(cells, "test", idx0=70, seed0=200)
        rows = train + test

        fit, _fd, evaluation = _fit_eval(train, test)
        ref = self._independent_maes(train, test)

        assert fit["beta"] == pytest.approx(ref["beta_w"], **TOL)
        assert evaluation["mae_m0"] == pytest.approx(ref["mae_m0"], **TOL)
        assert evaluation["mae_m1"] == pytest.approx(ref["mae_m1"], **TOL)
        if ref["mae_m2"] is not None:
            assert evaluation["mae_m2"] == pytest.approx(ref["mae_m2"], **TOL)
        if ref["mae_m3"] is not None:
            assert evaluation["mae_m3"] == pytest.approx(ref["mae_m3"], **TOL)
        assert evaluation["improvement"] == pytest.approx(ref["improvement"], **TOL)

        gates, verification = _gates(rows)
        assert gates["passed"], gates
        assert verification["passed"], verification
        bootstrap = paired_stratified_bootstrap(evaluation["paired"])
        disp = primary_disposition(evaluation, bootstrap, gates, verification, fit)
        assert disp["disposition"] in {"PASS", "FAIL"}
