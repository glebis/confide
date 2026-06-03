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

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout
    return out.splitlines()


def test_no_ai4privacy_derived_data_committed():
    bad = [f for f in _tracked()
           if re.search(r"ai4privacy|en-real", f, re.I)
           and re.match(r"(data/|caches/|results/)", f)]
    assert not bad, "AI4Privacy-derived data/artifacts committed (restricted license — fetch locally instead): " + ", ".join(bad)
