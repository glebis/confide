"""TDD for the RU entity-propagation pass in the session-anonymizer skill.

The benchmark's residual-risk finding: the stack masks most name mentions but
leaks specific *variants* — inflected case forms, vocatives, capitalized
common-word collisions, and Latin transliterations. Propagation closes these by
masking every morphological/translit variant of an already-detected PERSON name.
Dependency-free (no pymorphy/natasha at runtime) so it runs anywhere.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "skills", "session-anonymizer", "scripts"))

import anonymize as az


def _masked(text, surfaces, **kw):
    spans = az.propagate_names(text, surfaces, **kw)
    return {text[s.start:s.end] for s in spans}


def test_propagates_instrumental_case():
    assert "Артёмом" in _masked("Я говорил с Артёмом вчера", {"Артём"})


def test_propagates_dative_case():
    assert "Денису" in _masked("Денису позвонили утром", {"Денис"})


def test_propagates_vocative_sentence_initial():
    assert "Роман" in _masked("Роман, я хочу сказать одну вещь", {"Роман"})


def test_capitalization_gate_blocks_common_word_collision():
    # "Вера" the name vs "веру" the common noun (faith): mask only the capitalized one.
    got = _masked("Я потерял веру, но встретил Веру", {"Вера"})
    assert "Веру" in got
    assert "веру" not in got


def test_transliterated_latin_name_is_masked():
    assert "Timur" in _masked("a quick meeting with Timur today", {"Тимур"})


def test_unrelated_capitalized_word_not_masked():
    assert _masked("Москва сегодня большая", {"Артём"}) == set()


def test_short_names_require_exact_to_avoid_overmatch():
    # 3-letter tokens are too short for stem matching; must not bleed into others.
    assert _masked("он Ян и она Яна", {"Ян"}) <= {"Ян"}


def test_anonymize_propagates_from_a_detected_mention(monkeypatch):
    """End-to-end: a base layer detects 'Артём' once; the inflected 'Артёмом'
    elsewhere must be redacted via the propagation pass."""
    text = "Клиент Артём пришёл. Я говорил с Артёмом вчера."
    i = text.index("Артём")
    monkeypatch.setattr(az, "run_natasha",
                        lambda t: [az.Span(start=i, end=i + len("Артём"),
                                           text="Артём", label="PERSON", source="natasha")])
    monkeypatch.setattr(az, "run_ollama", lambda t, model="": [])
    monkeypatch.setattr(az, "run_regex", lambda t: [])
    res = az.anonymize(text, layers=["natasha"])
    assert "Артёмом" not in res.redacted_text     # the inflected variant was masked
    labels = [s["text"] for s in res.spans]
    assert any("Артёмом" == t for t in labels)
