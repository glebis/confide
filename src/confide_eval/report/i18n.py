"""Minimal, dependency-free i18n for the report generator.

Design — "poor-man's gettext" (English-keyed message catalog):
  * The message id IS the English source string (with ``{named}`` placeholders
    for any interpolated values), so the generator stays readable — you see the
    English inline and the translation is a lookup.
  * Translations live in JSON catalogs ``translations.<lang>.json`` next to this
    module, i.e. as *data*, not code: re-translating means editing JSON.
  * A missing key falls back to the English source (and is recorded by
    ``missing()`` so coverage can be asserted), so the report never breaks.
  * Values are interpolated with ``str.format`` *after* lookup, so numbers never
    enter the key — the same msgid is stable across runs.

Chosen over stdlib ``gettext`` because that needs ``.po``/``.mo`` files and an
``msgfmt`` compile step (the report is a single, no-build-step artifact), and
the string volume here is tiny (~90 messages). No third-party dependency.
"""
import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
_CATALOGS = {}          # lang -> {msgid: msgstr}
_LANG = "en"
_MISSING = set()        # msgids requested for a non-en lang with no translation


def _catalog(lang):
    if lang not in _CATALOGS:
        p = os.path.join(_DIR, f"translations.{lang}.json")
        _CATALOGS[lang] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    return _CATALOGS[lang]


def set_lang(lang):
    """Switch the active language for subsequent ``t()`` calls."""
    global _LANG
    _LANG = lang
    _catalog(lang)


def languages():
    """``["en", ...]`` — en (the source) plus every translations.<lang>.json found."""
    langs = ["en"]
    for f in sorted(os.listdir(_DIR)):
        if f.startswith("translations.") and f.endswith(".json"):
            langs.append(f[len("translations."):-len(".json")])
    return langs


def t(msgid, **kw):
    """Translate ``msgid`` into the active language, then ``.format(**kw)``.

    English (or a missing key) returns the source string unchanged; missing
    non-en keys are recorded in ``missing()`` for a coverage check."""
    if _LANG == "en":
        s = msgid
    else:
        s = _catalog(_LANG).get(msgid)
        if s is None:
            _MISSING.add(msgid)
            s = msgid
    return s.format(**kw) if kw else s


def missing():
    """Sorted list of msgids that fell back to English for a non-en language."""
    return sorted(_MISSING)
