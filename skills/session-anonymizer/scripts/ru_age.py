#!/usr/bin/env python3
"""Russian AGE recognizer (spelled-out cardinals + numeric, age-anchored).

AGE is a 0-deterministic-recall quasi type in the CONFIDE benchmark. Russian ages
are usually spelled-out cardinals anchored to a pronoun/"возраст" cue ("мне сорок
один", "возраст — двадцать девять") or to "N лет + a person reference" ("сорок
пять лет мужику").

The precision trap, learned by measuring on the RU gold: a bare "N лет/года" is
overwhelmingly a DURATION, not an age ("двадцать лет всё то же", "отца нет семь
лет"). Matching it produced ~69 false positives vs 13 real. So:
  - strong cues (возраст / исполнилось / стукнуло) -> always an age;
  - pronoun cues (мне/ему/ей/…) -> an age ONLY when the number is a predicate
    (followed by a clause boundary / год-лет / conjunction), never when it counts
    a following noun ("дал ей ОДИН проект", "сто РАЗ");
  - "N лет + person noun" -> an age.

Kept in its own module so it can be developed independently of anonymize.py.
"""
import re
from dataclasses import dataclass


@dataclass
class Span:
    start: int
    end: int
    text: str
    label: str
    source: str
    confidence: float = 1.0


_TENS = "двадцать|тридцать|сорок|пятьдесят|шестьдесят|семьдесят|восемьдесят|девяносто|сто"
_UNITS = "один|одна|два|две|три|четыре|пять|шесть|семь|восемь|девять"
_TEENS = ("десять|одиннадцать|двенадцать|тринадцать|четырнадцать|пятнадцать|"
          "шестнадцать|семнадцать|восемнадцать|девятнадцать")
_CARD = rf"(?:(?:{_TENS})(?:\s+(?:{_UNITS}))?|{_TEENS}|{_UNITS})"
_NUM = rf"(?:{_CARD}|\d{{1,3}})"
_YEARS = r"(?:год(?:а|у|ом|е|ов)?|лет|годик(?:а|ов)?)"
_FILL = r"(?:уже\s+|сейчас\s+|почти\s+|только\s+)?"
_PERSON = (r"(?:мужик\w*|мужчин\w*|женщин\w*|девушк\w*|парн\w*|пацан\w*|"
           r"человек\w*|тётк\w*|тетк\w*|дядьк\w*|бабушк\w*|дедушк\w*|мальчик\w*|девочк\w*)")

# strong cue -> always an age
_STRONG = re.compile(rf"(?i)\b(?:возраст\w*|исполни\w+|стукнул\w+)[\s—:\-–]+{_FILL}({_NUM})\b")
# pronoun cue -> age only when the number is a predicate (clause boundary follows)
_BOUND = (r"(?=\s*(?:$|[.,;:!?…)»\"'—–-]|год|лет"
          r"|\b(?:и|а|но|уже|всего|только|скоро|будет|было)\b))")
_PRON = re.compile(rf"(?i)\b(?:мне|тебе|ему|ей|вам|нам|им)[\s—:\-–]+{_FILL}({_NUM})\b{_BOUND}")
# N лет + person reference
_NUM_PERSON = re.compile(rf"(?i)\b({_NUM})\s+{_YEARS}\s+{_PERSON}")


def find_ages(text: str) -> list:
    """Return AGE Spans detected in `text` (see module docstring for the policy)."""
    spans, seen = [], set()

    def add(m):
        a, b = m.start(1), m.end(1)
        if (a, b) in seen:
            return
        seen.add((a, b))
        spans.append(Span(start=a, end=b, text=text[a:b], label="AGE",
                          source="age", confidence=0.85))

    for pat in (_STRONG, _PRON, _NUM_PERSON):
        for m in pat.finditer(text):
            add(m)
    return spans
