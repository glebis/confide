"""Release guard: no AI4Privacy-derived DATA/artifacts committed to the public tree.

AI4Privacy's license forbids redistribution/derivatives without written permission,
so EN-real gold, derived detector caches, and derived results must be fetched/built
locally (see src/confide_eval/data/fetch_ai4privacy.py), never committed. Code that
*references* AI4Privacy (fetch/build/registry) is fine; committed data is not.
(P0 release-review issue #19.)
"""
import os
import re
import subprocess

from confide_eval import paths
from confide_eval.registry import check_artifacts

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout
    return out.splitlines()


def test_no_ai4privacy_derived_data_committed():
    bad = [f for f in _tracked()
           if re.search(r"ai4privacy|en-real", f, re.I)
           and re.match(r"(data/|caches/|results/)", f)]
    assert not bad, "AI4Privacy-derived data/artifacts committed (restricted license — fetch locally instead): " + ", ".join(bad)


def test_en_real_gold_path_is_local_only_when_not_fetched(tmp_path, monkeypatch):
    local = tmp_path / "pii-eval-ai4privacy.jsonl"
    legacy = tmp_path / "pii-eval-ai4privacy.local.jsonl"
    monkeypatch.setattr(paths, "EN_REAL_LOCAL", local)
    monkeypatch.setattr(paths, "EN_REAL_LEGACY_LOCAL", legacy)

    assert paths.en_real_gold() == local
    assert paths.en_real_text_present() is False


def test_public_artifact_check_excludes_en_real_when_local_text_absent(monkeypatch):
    monkeypatch.setattr(check_artifacts, "en_real_text_present", lambda: False)

    assert "en-real" not in check_artifacts.active_datasets()
