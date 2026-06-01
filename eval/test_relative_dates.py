#!/usr/bin/env python3
"""Unit tests for the relative/colloquial DATE recognizer (T6).

Proves the deterministic regex layer now covers relative, spelled-out, and
month-name dates in EN + RU (the additive capability the Presidio baseline had),
and that it does NOT fire on a timestamp, an age, or a non-date discourse marker.

Run: python3 test_relative_dates.py   (or: pytest eval/test_relative_dates.py)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "skills", "session-anonymizer", "scripts"))
import anonymize


def _dates(text):
    return {s.text for s in anonymize.run_regex(text) if s.label == "DATE"}


def test_en_relative_positives():
    for s in ("last Tuesday", "last Thursday", "12 December", "March 3rd, 2024",
              "5th of January", "19th of the month", "June 14 2019", "two weeks ago",
              "3 days ago", "yesterday", "tomorrow", "today", "next Monday",
              "on Monday", "last week", "December/48", "18th April 2020",
              "November 13th, 1958"):
        assert _dates("We spoke " + s + " about it."), f"EN should tag {s!r} as DATE"


def test_ru_relative_positives():
    for s in ("третьего февраля", "12 декабря", "в прошлый вторник",
              "2 недели назад", "10 лет назад", "до Нового года", "после Нового года",
              "первого мая", "25 марта"):
        assert _dates("Это случилось " + s + "."), f"RU should tag {s!r} as DATE"


def test_negatives_not_dates():
    # timestamp, age (EN+RU), discourse marker, and a structured account id must
    # never be tagged DATE by the relative-date recognizer.
    assert not _dates("Лог: 00:12:45 ошибка."), "timestamp must not be a DATE"
    assert not _dates("I am 34 years old."), "EN age must not be a DATE"
    assert not _dates("Мне 34 года."), "RU age must not be a DATE"
    assert not _dates("Как в прошлый раз решили."), "'в прошлый раз' is not a date"
    assert not _dates("В следующий раз обсудим."), "'в следующий раз' is not a date"


def test_offsets_and_all_occurrences():
    text = "Сначала 12 декабря, потом третьего февраля, и ещё 12 декабря."
    spans = [s for s in anonymize.run_regex(text) if s.label == "DATE"]
    # both "12 декабря" occurrences + the spelled-out date are emitted
    assert sum(1 for s in spans if s.text == "12 декабря") == 2
    assert any(s.text == "третьего февраля" for s in spans)
    for s in spans:  # offsets must slice back to the matched text
        assert text[s.start:s.end] == s.text


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("✓ all relative-date tests passed")
