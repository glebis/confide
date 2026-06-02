"""RU-real (JayGuard) gold-slice integrity checks (deterministic, no LLM).

The slice is machine-derived from JayGuard's BIO labels (Apache-2.0). These tests
guard the three properties the build script promises: the gold loads, every span
offset aligns (text[start:end] == value), and every span type is in the CONFIDE
canonical set restricted to what JayGuard can label (PERSON / LOCATION).
"""
import json
import os

from confide_eval import paths
from confide_eval.scoring import score_bench as sb

GOLD = os.fspath(paths.GOLD["ru-real"])

# JayGuard labels only personal names and places -> these two CONFIDE types.
ALLOWED_TYPES = {"PERSON", "LOCATION"}
ALLOWED_CLASSES = {"direct", "quasi"}


def _load():
    with open(GOLD, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_gold_loads_and_is_nonempty():
    rows = _load()
    assert len(rows) >= 40, f"expected a focused slice of >=40 docs, got {len(rows)}"
    for r in rows:
        assert r["lang"] == "ru"
        assert r["text"]
        assert r["spans"], f"{r['doc_id']} has no spans"


def test_offsets_align_for_every_span():
    rows = _load()
    n = 0
    for r in rows:
        for s in r["spans"]:
            n += 1
            assert r["text"][s["start"]:s["end"]] == s["value"], (
                f"offset mismatch in {r['doc_id']}: "
                f"text[{s['start']}:{s['end']}]={r['text'][s['start']:s['end']]!r} "
                f"!= value={s['value']!r}")
    assert n > 0


def test_types_in_confide_set():
    for r in _load():
        for s in r["spans"]:
            assert s["type"] in ALLOWED_TYPES, f"unexpected type {s['type']}"
            assert sb.canon(s["type"]) in ALLOWED_TYPES
            assert s["identifier_class"] in ALLOWED_CLASSES
            assert s["harm"] in {"high", "medium", "low"}
            assert s.get("entity_id"), f"{r['doc_id']} span missing entity_id"


def test_dataset_is_wired_into_scorer():
    assert "ru-real" in sb.GOLD
    assert "ru-real" in sb.COMBOS
    # the RU local default ★ stack must be present
    names = [n for n, _ in sb.COMBOS["ru-real"]]
    assert any("★" in n for n in names)
