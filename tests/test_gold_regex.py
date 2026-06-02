"""Regression tests for the RU gold-builder surface-form regexes.

Guards against over-matching name patterns onto common words — notably the
c-maksim entity, whose old pattern `Максим[а-я]*` matched the adverb
"максимально" under re.IGNORECASE (PR #9 fixed the JSONL by hand, not the
source; this pins the fixed regex).
"""
from confide_eval.data.build_ru_dataset import CLIENTS, find_spans


def _maksim_entity():
    for ent in CLIENTS["c"]:
        if ent[0] == "c-maksim":
            return ent
    raise AssertionError("c-maksim entity not found in CLIENTS['c']")


def _maksim_hits(text):
    spans = find_spans(text, [_maksim_entity()])
    return [s["value"] for s in spans]


def test_maksim_matches_name_and_declensions():
    for name in ("Максим", "Максима", "Максиму", "Максимом", "Максиме"):
        assert _maksim_hits(name) == [name], f"name form {name!r} should match"


def test_maksim_in_sentence_context():
    text = "Я обсудила это с Максимом, и Максим согласился."
    assert _maksim_hits(text) == ["Максимом", "Максим"]


def test_maksim_does_not_match_adverb_maksimalno():
    # The bug: "максим" + "ально" with re.IGNORECASE matched the old pattern.
    assert _maksim_hits("я выложилась максимально") == []
    assert _maksim_hits("Максимально честно") == []


def test_maksim_does_not_match_other_names():
    assert _maksim_hits("Максимильян пришёл") == []
