"""Shared helpers for the two-stage freeze tests (Claude, Phase 4 Gate B/D).

``build_training_base`` runs a small confirmatory *training* subset once
(16 instances: n in {30, 40}, A in {426, 500}, indices 0-3) with retained
certificates. ``make_case`` copies it, builds a Stage A over it, runs the
non-executing preflight and writes a Stage B, exactly as Lumi would.

The live environment is replaced by :class:`FakeLive`, a deterministic
double of ``freeze.current_provenance`` (git, interpreter, dependency
inventory, documents), so the state of the checkout running the tests can
neither pass nor fail them. The real git probe is tested separately against
a temporary repository. ``freeze.expected_training_specs`` is patched to the
16-instance subset so that the training checks run on it instead of the
1960-instance population.

Nothing here executes a confirmatory test instance (indices 70-99).
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from om_lab import freeze
from om_lab import width_experiment as wx

SUBSET = dict(n_values=[30, 40], a_values=[426, 500], indices=range(0, 4))
SETTINGS = dict(workers=2, watchdog_s=600.0, max_attempts=3)
HEAD = "a" * 40
LATER = "b" * 40
STEM = "confirmatory_train_DIAGNOSTIC_SUBSET"


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def flip_hex(value: str) -> str:
    return ("0" if value[0] != "0" else "1") + value[1:]


def subset_specs() -> list[wx.InstanceSpec]:
    return wx.build_specs("confirmatory", "train", **SUBSET)


def build_training_base(base: Path) -> dict:
    """Run the 16-instance training subset once, retaining certificates."""
    return wx.run_split(
        population="confirmatory", split="train", out_dir=base / "train", workers=0,
        keep_certificates=True, diagnostic_subset=True, **SUBSET,
    )


def clean_provenance() -> dict:
    """The running environment, with git replaced by a clean checkout at HEAD."""
    prov = freeze.current_provenance()
    prov["git"] = {"available": True, "head": HEAD, "tree_clean": True, "dirty": [],
                   "commit_exists": None, "changed_since_commit": None}
    return prov


class FakeLive:
    """Deterministic stand-in for ``freeze.current_provenance``.

    ``commits`` maps each commit this fake checkout contains to the frozen
    paths changed between it and HEAD, which is what ``git_provenance``
    reports for a real checkout.
    """

    def __init__(self, provenance: dict):
        self.provenance = provenance
        self.commits: dict[str, list[str]] = {HEAD: []}

    def __call__(self, *, commit=None, amendment_docs=freeze.DEFAULT_AMENDMENT_DOCS, drat_trim=None) -> dict:
        prov = copy.deepcopy(self.provenance)
        if commit is not None:
            prov["git"]["commit_exists"] = commit in self.commits
            prov["git"]["changed_since_commit"] = copy.deepcopy(self.commits.get(commit))
        return prov


@dataclass
class FreezeCase:
    root: Path
    live: FakeLive
    records_path: Path
    cert_manifest_path: Path
    cert_dir: Path
    stage_a: Path
    stage_b: Path
    model: Path

    # -- Stage A / Stage B editing -----------------------------------------

    def stage_a_doc(self) -> dict:
        return json.loads(self.stage_a.read_text(encoding="utf-8"))

    def stage_b_doc(self) -> dict:
        return json.loads(self.stage_b.read_text(encoding="utf-8"))

    def write_stage_b(self, doc: dict) -> None:
        self.stage_b.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def edit_stage_b(self, mutate: Callable[[dict], object]) -> None:
        doc = self.stage_b_doc()
        mutate(doc)
        self.write_stage_b(doc)

    def resign(self) -> None:
        """Rewrite Stage B to name the current Stage A bytes, bypassing preflight.

        This isolates Stage A's own checks from the Stage B hash binding: a
        refusal after ``resign`` comes from the Stage A content itself.
        """
        self.edit_stage_b(lambda doc: doc.update(stage_a_sha256=sha256_file(self.stage_a)))

    def edit_stage_a(self, mutate: Callable[[dict], object], *, resign: bool = True) -> None:
        doc = self.stage_a_doc()
        mutate(doc)
        self.stage_a.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if resign:
            self.resign()

    # -- training artefacts -------------------------------------------------

    def records(self) -> list[dict]:
        return wx.read_jsonl(self.records_path)

    def write_records(self, records: list[dict]) -> None:
        wx.write_jsonl(records, self.records_path)

    def cert_manifest(self) -> list[dict]:
        return wx.load_certificate_manifest(self.cert_manifest_path)[1]

    def write_cert_manifest(self, entries: list[dict]) -> None:
        self.cert_manifest_path.write_text(json.dumps(entries, indent=1, sort_keys=True), encoding="utf-8")

    def unsat_ids(self) -> list[str]:
        return [r["instance_id"] for r in self.records() if r["status"] == "UNSAT"]

    def sat_ids(self) -> list[str]:
        return [r["instance_id"] for r in self.records() if r["status"] == "SAT"]

    def cert_files(self, instance_id: str) -> tuple[Path, Path]:
        cnf, drat = wx.certificate_file_names(instance_id)
        return self.cert_dir / cnf, self.cert_dir / drat

    def audit_certificates(self, **kwargs) -> dict:
        kwargs.setdefault("specs", subset_specs())
        kwargs.setdefault("certificates_dir", self.cert_dir)
        kwargs.setdefault("certificate_manifest", self.cert_manifest())
        return wx.audit_retained_certificates(self.records(), **kwargs)

    # -- verification -------------------------------------------------------

    def verify(self, **kwargs) -> freeze.AuthorizedFreeze:
        kwargs.setdefault("requested_settings", freeze.make_settings(**SETTINGS))
        return freeze.verify_for_execution(self.stage_a, self.stage_b, **kwargs)


def make_case(tmp_path: Path, monkeypatch, base: Path, base_provenance: dict) -> FreezeCase:
    """Copy the training base, build Stage A, preflight it and write Stage B."""
    root = tmp_path / "case"
    shutil.copytree(base / "train", root / "train")
    specs = subset_specs()
    monkeypatch.setattr(freeze, "expected_training_specs", lambda: list(specs))
    live = FakeLive(copy.deepcopy(base_provenance))
    monkeypatch.setattr(freeze, "current_provenance", live)
    train = root / "train"
    records = train / f"{STEM}_results.jsonl"
    manifest = train / f"{STEM}_certificate_manifest.json"
    cert_dir = train / "certificates"
    built = freeze.build_stage_a(
        out_dir=root / "freeze", training_records_path=records, training_certificates_dir=cert_dir,
        training_certificate_manifest_path=manifest, independent_reproduction_sha256=sha256_file(records),
        reproduced_by="independent reproducer (test)", settings=freeze.make_settings(**SETTINGS),
    )
    stage_b = root / "freeze" / "freeze_stage_b.json"
    freeze.authorize(built["stage_a_path"], authorized_by="Lumi (test)", test_split_unexposed=True,
                     out_path=stage_b)
    return FreezeCase(root=root, live=live, records_path=records, cert_manifest_path=manifest,
                      cert_dir=cert_dir, stage_a=Path(built["stage_a_path"]), stage_b=stage_b,
                      model=Path(built["model_path"]))
