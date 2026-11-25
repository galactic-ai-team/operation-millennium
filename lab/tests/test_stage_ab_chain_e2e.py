"""End-to-end Stage A / Stage B integration on a synthetic design
(Claude, ACE-GATE-D-02, runner side).

The chain under test uses the production code at every step:

    training run -> freeze.build_stage_a -> freeze.authorize (the
    non-executing preflight, then Stage B) -> official test run
    (run_split with Stage A and Stage B: verify_for_execution, the
    run_specs guard, real worker processes) -> combine -> audit of the
    retained certificates -> analyze_width.build_analysis_handoff ->
    the analyze_width command of runbook step 6 -> primary disposition

and the same chain with a forged, mismatched or unauthorized link, which
must be refused (both directions, as Ace's ruling asks).

Synthetic design. For this module only, the design constants
``N_VALUES`` and ``A_VALUES`` are replaced, in both
``om_lab.analyze_width`` and ``om_lab.width_experiment`` (which imports
them), by an unregistered design: n in {12, 14, 16, 18} and A in
{2.00, 2.50, 3.00, 6.00, 7.00, 8.00, 9.00}. Everything else is the
registered machinery: 28 cells, indices 0-69 train and 70-99 test, the
seed scheme, the budget, every check. No registered cell is in the
design, so no registered training or held-out instance is generated,
solved or read; a guard around ``run_specs`` refuses to start a worker
for any spec in a registered n or A. The tests check how the chain
behaves, never which disposition the synthetic data reaches.

The live environment is the ``FakeLive`` double of the other freeze
tests (a clean checkout); Stage B is written only by ``freeze.authorize``,
never by hand.

[Claim Level: Empirical Observation] for every result below.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from _freeze_fixtures import SETTINGS, FakeLive, clean_provenance, sha256_file
from om_lab import analyze_width as aw
from om_lab import freeze
from om_lab import width_experiment as wx

REGISTERED_N = tuple(aw.N_VALUES)
REGISTERED_A = tuple(aw.A_VALUES)
SYNTHETIC_N = (12, 14, 16, 18)
SYNTHETIC_A = (200, 250, 300, 600, 700, 800, 900)


def _read_json(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    """Run the authorised chain once on the synthetic design (about 25 s)."""
    assert not set(SYNTHETIC_N) & set(REGISTERED_N)
    assert not set(SYNTHETIC_A) & set(REGISTERED_A)
    out = tmp_path_factory.mktemp("stage_ab_chain")
    with pytest.MonkeyPatch.context() as mp:
        for module in (aw, wx):
            mp.setattr(module, "N_VALUES", list(SYNTHETIC_N))
            mp.setattr(module, "A_VALUES", list(SYNTHETIC_A))
        real_run_specs = wx.run_specs

        def run_specs_synthetic_only(specs, **kwargs):
            registered = [s.instance_id for s in specs
                          if s.n in REGISTERED_N or s.a_hundredths in REGISTERED_A]
            assert not registered, f"refusing to start workers for registered cells: {registered[:3]}"
            return real_run_specs(specs, **kwargs)

        mp.setattr(wx, "run_specs", run_specs_synthetic_only)
        mp.setattr(freeze, "current_provenance", FakeLive(clean_provenance()))

        # Runbook step 1: the training split, retaining certificates, and a
        # second run of the same code standing in for the reproduction.
        train = wx.run_split(population="confirmatory", split="train", out_dir=out,
                             keep_certificates=True, **SETTINGS)
        reproduction = wx.run_split(population="confirmatory", split="train", out_dir=out / "reproduction",
                                    keep_certificates=True, **SETTINGS)
        # Steps 2-4: Stage A, then freeze.authorize (preflight + Stage B).
        built = freeze.build_stage_a(
            out_dir=out / "freeze", training_records_path=train["results_path"],
            training_certificates_dir=out / "certificates",
            training_certificate_manifest_path=train["certificate_manifest_path"],
            independent_reproduction_sha256=reproduction["results_sha256"],
            reproduced_by="synthetic E2E fixture: second run in the same process (not independent)",
            settings=freeze.make_settings(**SETTINGS),
        )
        stage_b = out / "freeze" / "freeze_stage_b.json"
        freeze.authorize(built["stage_a_path"], authorized_by="Lumi (synthetic E2E fixture)",
                         test_split_unexposed=True, out_path=stage_b)
        # Step 5: the official test run.
        test = wx.run_split(population="confirmatory", split="test", out_dir=out,
                            stage_a_path=built["stage_a_path"], stage_b_path=stage_b,
                            keep_certificates=True, **SETTINGS)
        # Step 6: combine and audit.
        combined = wx.combine_results(
            [train["results_path"], test["results_path"]], out / "results.jsonl",
            certificate_manifests=[train["certificate_manifest_path"], test["certificate_manifest_path"]],
        )
        audit = wx.audit_records(
            wx.read_jsonl(combined["results_path"]), population="confirmatory", splits=["train", "test"],
            certificates_dir=out / "certificates", certificate_manifest_path=combined["certificate_manifest_path"],
        )
        yield SimpleNamespace(
            out=out, train=train, reproduction=reproduction, test=test, combined=combined, audit=audit,
            stage_a=Path(built["stage_a_path"]), stage_b=stage_b, model=Path(built["model_path"]),
            test_manifest=Path(test["run_manifest_path"]),
            combine_manifest=Path(combined["combine_manifest_path"]),
            records=Path(combined["results_path"]),
        )


def test_authorised_synthetic_chain_reaches_the_primary_disposition(chain, tmp_path, monkeypatch, capsys):
    stage_a = _read_json(chain.stage_a)
    training_sha = stage_a["training"]["records_sha256"]
    test_sha = sha256_file(chain.test["results_path"])
    # Every runner step produced its artefact, complete and passing integrity.
    assert chain.train["run_mode"] == "OFFICIAL" and chain.train["complete"] is True
    assert chain.reproduction["results_sha256"] == chain.train["results_sha256"] == training_sha
    test_manifest = _read_json(chain.test_manifest)
    assert (test_manifest["population"], test_manifest["split"], test_manifest["run_mode"]) == (
        "confirmatory", "test", "OFFICIAL")
    assert test_manifest["complete"] is True and test_manifest["n_instances"] == 840
    assert test_manifest["integrity"]["passed"] is True
    assert test_manifest["integrity"]["verification_gate_ready"] is True
    assert test_manifest["schedule_sha256"] == stage_a["population"]["test"]["schedule_sha256"]
    assert test_manifest["results_sha256"] == test_sha
    authorization = test_manifest["authorization"]
    assert authorization["stage_a_sha256"] == sha256_file(chain.stage_a)
    assert authorization["stage_b_sha256"] == sha256_file(chain.stage_b)
    assert authorization["test_schedule_sha256"] == test_manifest["schedule_sha256"]
    combine_manifest = _read_json(chain.combine_manifest)
    assert combine_manifest["complete"] is True and combine_manifest["n_records"] == 2800
    assert {entry["sha256"] for entry in combine_manifest["inputs"]} == {training_sha, test_sha}
    assert combine_manifest["results_sha256"] == sha256_file(chain.records)
    assert chain.audit["passed"] is True, chain.audit["failures"]
    n_unsat = sum(r["status"] == "UNSAT" for r in wx.read_jsonl(chain.records))
    assert chain.audit["retained_certificates"]["checked"] == n_unsat > 0
    # No registered cell anywhere in the analysed records.
    assert all(r["n_vars"] in SYNTHETIC_N and r["a_hundredths"] in SYNTHETIC_A for r in wx.read_jsonl(chain.records))

    # The handoff consumes exactly the artefacts the runner and combine wrote.
    handoff = aw.build_analysis_handoff(
        chain.stage_a, chain.stage_b, test_run_manifest_path=chain.test_manifest,
        combine_manifest_path=chain.combine_manifest, records_path=chain.records,
    )
    assert handoff["records_bound"] is True and handoff["records_sha256"] == sha256_file(chain.records)
    assert handoff["training_records_sha256"] == training_sha and handoff["test_results_sha256"] == test_sha
    assert handoff["test_run_manifest_sha256"] == sha256_file(chain.test_manifest)
    assert handoff["fitted_model_file_sha256"] == sha256_file(chain.model) != handoff["fitted_model_sha256"]

    # Runbook step 6, the official analysis command, reaches the primary disposition.
    out = tmp_path / "analysis"
    monkeypatch.setattr(sys, "argv", [
        "analyze_width", "--records", str(chain.records), "--population", "confirmatory",
        "--stage-a", str(chain.stage_a), "--stage-b", str(chain.stage_b),
        "--test-run-manifest", str(chain.test_manifest), "--combine-manifest", str(chain.combine_manifest),
        "--out-dir", str(out),
    ])
    aw.main()
    assert "Analysis handoff verified" in capsys.readouterr().out
    summary = _read_json(out / "width_analysis.json")
    assert summary["counts"]["n_rows"] == 2800 and summary["counts"]["n_error_rows"] == 0
    for gate in ("integrity_gates", "verification_gates", "reproducibility_gates", "fitted_model_gate"):
        assert summary[gate]["passed"] is True, (gate, summary[gate])
    echo = summary["analysis_handoff"]
    assert echo["stage_a_sha256"] == handoff["stage_a_sha256"]
    assert echo["stage_b_sha256"] == handoff["stage_b_sha256"]
    assert echo["records_bound"] is True
    disposition = summary["primary_disposition"]
    assert disposition["disposition"] in {"PASS", "FAIL", "INCONCLUSIVE"}
    assert _read_json(out / "primary_result.json")["disposition"] == disposition["disposition"]


def test_forged_mismatched_or_unauthorised_links_are_refused(chain, tmp_path):
    def handoff(stage_b=None, **overrides):
        kwargs = dict(test_run_manifest_path=chain.test_manifest, combine_manifest_path=chain.combine_manifest,
                      records_path=chain.records, deep_training=False)
        kwargs.update(overrides)
        return aw.build_analysis_handoff(chain.stage_a, stage_b or chain.stage_b, **kwargs)

    # A second, different authorisation (written by freeze.authorize) cannot
    # adopt the output of the run that the first one authorised.
    other_b = tmp_path / "freeze_stage_b_other.json"
    freeze.authorize(chain.stage_a, authorized_by="another coordinator (synthetic E2E fixture)",
                     test_split_unexposed=True, out_path=other_b)
    with pytest.raises(ValueError, match="authorises a different Stage B"):
        handoff(stage_b=other_b)

    # The test output changed after the authorised run, then recombined.
    records = wx.read_jsonl(chain.test["results_path"])
    records[0]["propagations"] += 1
    altered = tmp_path / "confirmatory_test_results.jsonl"
    wx.write_jsonl(records, altered)
    recombined = wx.combine_results([chain.train["results_path"], altered], tmp_path / "results.jsonl")
    with pytest.raises(ValueError, match="do not include the authorized test output"):
        handoff(combine_manifest_path=recombined["combine_manifest_path"], records_path=recombined["results_path"])

    # The combined records changed after the combine.
    tampered = tmp_path / "results_tampered.jsonl"
    tampered.write_bytes(chain.records.read_bytes().replace(b'"status":"SAT"', b'"status":"UNSAT"', 1))
    with pytest.raises(ValueError, match="differs from the combine manifest"):
        handoff(records_path=tampered)

    # The training run's manifest is not an authorised test run.
    with pytest.raises(ValueError, match="test-run binding"):
        handoff(test_run_manifest_path=Path(chain.train["run_manifest_path"]))

    # Unauthorised: without Stage B the runner refuses before scheduling
    # anything, and the analysis without the handoff cannot pass or fail.
    with pytest.raises(wx.ConfirmatoryRunNotAuthorized, match="--stage-a and --stage-b"):
        wx.run_split(population="confirmatory", split="test", out_dir=tmp_path / "unauthorised",
                     stage_a_path=chain.stage_a, stage_b_path=None, keep_certificates=True, **SETTINGS)
    assert not (tmp_path / "unauthorised").exists()
    summary, _ = aw.analyze_records(wx.read_jsonl(chain.records), "confirmatory", bootstrap_replicates=200)
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert any("reproducibility gate not evaluated" in r for r in summary["primary_disposition"]["reasons"])
    assert summary["analysis_handoff"] is None
