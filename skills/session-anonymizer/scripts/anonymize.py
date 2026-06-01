#!/usr/bin/env python3
"""Three-layer PII anonymization for therapy transcripts.

Layer 1: Natasha (Russian NER — names, locations, orgs)
Layer 2: Deterministic regex (emails/URLs via scrubadub, phones via
         libphonenumber, structured IDs via regex) — replaces OpenAI
         Privacy Filter; instant, no model download
Layer 3: Local LLM via Ollama (medications, dates, contextual IDs)

All layers run locally by default. No data leaves the machine.
"""

import argparse
import json
import subprocess
import sys
import os
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Span:
    start: int
    end: int
    text: str
    label: str
    source: str
    confidence: float = 1.0


@dataclass
class AnonymizationResult:
    original_length: int
    redacted_text: str
    spans: list
    stats: dict
    warnings: list


def run_natasha(text: str) -> list[Span]:
    """Layer 1: Natasha NER for Russian text."""
    try:
        from natasha import Segmenter, NewsEmbedding, NewsNERTagger, Doc
    except ImportError:
        return []

    segmenter = Segmenter()
    emb = NewsEmbedding()
    ner_tagger = NewsNERTagger(emb)

    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_ner(ner_tagger)

    label_map = {"PER": "PERSON", "LOC": "LOCATION", "ORG": "ORG"}
    spans = []
    for span in doc.spans:
        mapped = label_map.get(span.type, span.type)
        spans.append(Span(
            start=span.start, end=span.stop,
            text=text[span.start:span.stop],
            label=mapped, source="natasha"
        ))
    return spans


import re

# Structured identifiers: policy / account / card-like grouped digit runs,
# e.g. 7722-4455-8811, 1234 5678 9012 3456. Phone-shaped groupings are left
# to libphonenumber below; merge_spans resolves any overlap.
_ID_PATTERN = re.compile(r"\b\d{4}[\s-]\d{4}[\s-]\d{2,4}(?:[\s-]\d{2,4})?\b")

# Numeric dates: DD.MM.YYYY / DD/MM/YYYY / ISO YYYY-MM-DD. Dates are PHI under
# HIPAA and were the one type no NER/LLM layer caught (the benchmark showed OPF's
# whole RU advantage was dates) — a trivial regex recovers it at regex speed.
# Spelled-out dates ("15 января") still fall to the LLM layer.
# Validated numeric dates: DD.MM.YYYY / DD/MM/YYYY / ISO YYYY-MM-DD(THH:MM). Day
# 1-31, month 1-12 (rejects 99.99.9999). Optional ISO time so 1984-08-08T00:00 is
# not split by a premature \b. Spelled-out dates remain the LLM layer's job.
_DATE_PATTERN = re.compile(
    r"\b(?:(?:0?[1-9]|[12]\d|3[01])[.\/](?:0?[1-9]|1[0-2])[.\/]\d{2,4}"
    r"|\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])(?:T\d{2}:\d{2}(?::\d{2})?)?)\b")

# --- Relative / colloquial DATE recognizers (the one additive capability the
# Presidio baseline had over the stack: it caught "last Tuesday", "19th of the
# month", "two weeks ago", "12 December" that the absolute-date regex + NER/LLM
# layers missed). These extend the deterministic DATE layer to spelled-out and
# relative calendar references in BOTH languages. They are kept TIGHT around
# lexical date anchors (weekday / month name / "ago"-style relative words) so a
# bare number that is an age, an ID, or a 00:12:45 timestamp is never matched.
#
# EN: weekday-relative, "N days/weeks/months/years ago", yesterday/today/tomorrow,
#     last/next week/month/year, "the 19th [of the month/Month]", and month-name
#     dates ("12 December", "March 3rd, 2024", "December/48"). On the EN gold this
#     is a pure recall win (0 false positives — the gold annotates exactly these
#     relative forms as DATE PII).
_MONTHS_EN = (r"(?:January|February|March|April|May|June|July|August|September|"
              r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)")
_WD_EN = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
# spelled small cardinals so "two weeks ago" is caught alongside "3 days ago"
_NUM_EN = r"(?:\d{1,3}|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
_DATE_REL_EN = re.compile(
    "(?i)\\b(?:"
    + "(?:last|next|this|on)\\s+" + _WD_EN
    + "|" + _NUM_EN + "\\s+(?:day|week|month|year)s?\\s+ago"
    + "|yesterday|tomorrow|today"
    + "|(?:last|next|this)\\s+(?:week|month|year)"
    + "|the\\s+\\d{1,2}(?:st|nd|rd|th)(?:\\s+of\\s+(?:the\\s+month|" + _MONTHS_EN + "))?"
    + "|\\d{1,2}(?:st|nd|rd|th)\\s+of\\s+(?:the\\s+month|" + _MONTHS_EN + ")"
    + "|" + _MONTHS_EN + "\\s+\\d{1,2}(?:st|nd|rd|th)?(?:,?\\s+\\d{4})?"
    + "|\\d{1,2}(?:st|nd|rd|th)?\\s+" + _MONTHS_EN + "(?:,?\\s+\\d{4})?"
    + "|" + _MONTHS_EN + "/\\d{2,4}"
    + ")\\b")

# RU: weekday-anchored relative refs ("в прошлый вторник"), "N дней/недель/месяцев/
#     лет [тому] назад", "до/после/перед/к Нового года", spelled day-of-month +
#     month ("третьего февраля"), and numeric day + month ("12 декабря").
#     DELIBERATELY EXCLUDES bare deictic adverbs (сегодня/вчера/завтра) and bare
#     week refs (на этой/прошлой неделе): on the RU gold those carry no standalone
#     identifying information and are NOT annotated as PII, so matching them adds
#     hundreds of false positives for zero recall (e.g. "сегодня" alone occurs
#     238× in the corpus, none in gold). Keeping the recognizer anchored to a
#     concrete calendar token (weekday / month / N-ago) recovers the real
#     spelled-out dates the LLM layer missed without collapsing precision.
_MONTHS_RU = (r"(?:январ[ья]|феврал[ья]|марта|апрел[ья]|ма[йя]|июн[ья]|июл[ья]|"
              r"август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья])")
_WD_RU = r"(?:понедельник|вторник|сред[уы]|четверг|пятниц[уы]|суббот[уы]|воскресень[ея])"
_ORD_RU = (r"(?:перв|втор|треть|четверт|пят|шест|седьм|восьм|девят|десят|"
           r"одиннадцат|двенадцат|тринадцат|четырнадцат|пятнадцат|шестнадцат|"
           r"семнадцат|восемнадцат|девятнадцат|двадцат|тридцат)\w*")
_DATE_REL_RU = re.compile(
    "(?i)(?<!\\w)(?:"
    + "в\\s+(?:прошл|следующ|эт)\\w+\\s+" + _WD_RU
    + "|\\d{1,3}\\s+(?:дн\\w+|недел\\w+|месяц\\w+|год\\w+|лет)\\s+(?:тому\\s+)?назад"
    + "|(?:до|после|перед|к)\\s+Нов\\w+\\s+год\\w+"
    + "|" + _ORD_RU + "\\s+" + _MONTHS_RU
    + "|\\d{1,2}\\s+" + _MONTHS_RU
    + ")\\b")

# Russian structured identifiers (PII-Bench RU taxonomy). SNILS has a distinctive
# XXX-XXX-XXX XX shape; passport is 4+6 digits. INN is context-gated (a bare 10/12
# digit run collides with timestamps/phones/case numbers — Codex audit #6), so it is
# only matched when an "ИНН" cue precedes it; the captured group is the digits.
_SNILS_PATTERN = re.compile(r"\b\d{3}-\d{3}-\d{3}[ -]\d{2}\b")
_PASSPORT_PATTERN = re.compile(r"\b\d{4}\s\d{6}\b")
_INN_PATTERN = re.compile(r"(?i)\bИНН\D{0,12}(\d{12}|\d{10})\b")
# Social handles / messenger links: @handle, t.me/x, vk.com/id, instagram, www.
# Case-insensitive domains; path must not end on a dot (trailing punctuation trimmed).
_HANDLE_PATTERN = re.compile(
    r"(?i)(?:(?:https?://)?(?:www\.)?(?:t\.me|vk\.com|instagram\.com|wa\.me)/[\w./+]*[\w/+]"
    r"|(?<!\w)@[A-Za-z][\w.]*[A-Za-z0-9])")


def run_regex(text: str) -> list[Span]:
    """Layer 2: deterministic PII — emails, URLs, phones, structured IDs.

    Replaces the OpenAI Privacy Filter (a 2.8 GB transformer that ran per-line
    inference on CPU). These targets are format-bound, so pattern matching is
    instant, deterministic, and needs no model download. Names/locations are
    already covered by Natasha (Layer 1).

      - emails / URLs : scrubadub deterministic detectors
      - phones        : Google libphonenumber (region RU), validated
      - structured IDs: regex (policy / account / card number groupings)

    Each sub-detector is optional; a missing dependency is skipped silently.
    """
    spans = []

    # Emails and URLs via scrubadub (instantiate detectors directly to avoid
    # enabling the EN-centric name detector — Natasha owns Russian names).
    try:
        from scrubadub.detectors.email import EmailDetector
        for f in EmailDetector().iter_filth(text):
            spans.append(Span(start=f.beg, end=f.end, text=f.text,
                              label="EMAIL", source="scrubadub"))
    except ImportError:
        pass
    try:
        from scrubadub.detectors.url import UrlDetector
        for f in UrlDetector().iter_filth(text):
            spans.append(Span(start=f.beg, end=f.end, text=f.text,
                              label="URL", source="scrubadub"))
    except ImportError:
        pass

    # Phones via libphonenumber, anchored to Russian region for bare numbers.
    try:
        import phonenumbers
        for m in phonenumbers.PhoneNumberMatcher(text, "RU"):
            spans.append(Span(start=m.start, end=m.end, text=m.raw_string,
                              label="PHONE", source="phonenumbers"))
    except ImportError:
        pass

    # Structured identifiers (policy / account / card numbers).
    for m in _ID_PATTERN.finditer(text):
        spans.append(Span(start=m.start(), end=m.end(), text=m.group(),
                          label="ID", source="regex"))

    # Numeric dates (PHI). Spelled-out + relative dates handled below.
    for m in _DATE_PATTERN.finditer(text):
        spans.append(Span(start=m.start(), end=m.end(), text=m.group(),
                          label="DATE", source="regex"))

    # Relative / colloquial + month-name dates (EN + RU). All occurrences, correct
    # offsets. merge_spans dedupes any overlap with an absolute-date match. These
    # close the gap the Presidio baseline exposed (relative-date recall).
    for pat in (_DATE_REL_EN, _DATE_REL_RU):
        for m in pat.finditer(text):
            spans.append(Span(start=m.start(), end=m.end(), text=m.group(),
                              label="DATE", source="regex"))

    # Russian structured identifiers + social handles. merge_spans resolves overlaps.
    # `grp` selects which capture group is the actual identifier span (INN gates on a
    # preceding "ИНН" cue but only the digits should be redacted).
    for pat, label, grp in ((_SNILS_PATTERN, "ID", 0), (_PASSPORT_PATTERN, "ID", 0),
                            (_INN_PATTERN, "ID", 1), (_HANDLE_PATTERN, "URL", 0)):
        for m in pat.finditer(text):
            spans.append(Span(start=m.start(grp), end=m.end(grp), text=m.group(grp),
                              label=label, source="regex"))

    return spans


def run_ollama(text: str, model: str = "qwen2.5:3b") -> list[Span]:
    """Layer 3: Local LLM via Ollama HTTP API for medications, dates, contextual IDs."""
    import re
    try:
        import urllib.request

        prompt = ('Extract ALL PII, including quasi-identifiers that narrow identity. '
                  'Include MEDICATIONS with dosages, AGES (also spelled-out, e.g. "тридцать четыре года"), '
                  'and PROFESSIONS/occupations. Return ONLY JSON array '
                  '[{\"text\":\"...\",\"type\":\"PERSON|LOCATION|ORG|PHONE|DATE|ADDRESS|MEDICATION|ID|AGE|PROFESSION\"}]. '
                  'No explanations.\n\nText: ' + text)

        # Engine-agnostic local-LLM transport. LLM_API=openai targets the
        # OpenAI-compatible /v1/chat/completions endpoint that llama.cpp's
        # `llama-server` (primary, memory-efficient — pin the .gguf + quant),
        # vLLM, and Ollama all expose. Default "ollama" keeps /api/chat for an
        # existing local Ollama. Base URL: LLM_BASE_URL or OLLAMA_HOST.
        api = os.environ.get("LLM_API", "ollama").lower()
        base = os.environ.get("LLM_BASE_URL",
                              os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        messages = [{"role": "user", "content": prompt}]
        if api == "openai":
            url = base + "/v1/chat/completions"
            payload = json.dumps({"model": model, "messages": messages,
                                  "temperature": 0, "max_tokens": 2048,
                                  "stream": False}).encode()
        else:
            url = base + "/api/chat"
            payload = json.dumps({"model": model, "messages": messages, "stream": False,
                                  "options": {"temperature": 0, "num_predict": 2048}}).encode()

        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())

        if api == "openai":
            output = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        else:
            output = data.get("message", {}).get("content", "")
        output = re.sub(r'<think>.*?</think>', '', output, flags=re.DOTALL)

        match = re.search(r'\[.*\]', output, re.DOTALL)
        if not match:
            return []

        entities = json.loads(match.group())
        spans = []
        seen = set()  # de-dupe (start,end) across entities
        low = text.lower()
        for ent in entities:
            ent_text = (ent.get("text") or "").strip()
            label = ent.get("type", "UNKNOWN")
            if len(ent_text) < 2:
                continue
            # Emit a span for EVERY occurrence of the returned value (the model returns
            # each value once, but redaction must cover all mentions). Case-insensitive,
            # so repeated mentions no longer all collapse onto the first via text.find().
            occ = [m.start() for m in re.finditer(re.escape(ent_text.lower()), low)]
            if not occ:
                # morphological fallback: match the stem at a word start and extend
                # over the whole word (handles RU inflection, e.g. Москва→Москве).
                # Emit ALL such occurrences, stopping the span at the word boundary
                # rather than the next ASCII space (Codex audit #3/#4).
                stem = ent_text[:max(3, len(ent_text) - 2)]
                if len(stem) >= 3:
                    for m in re.finditer(r"(?<!\w)" + re.escape(stem) + r"\w*", text, re.IGNORECASE):
                        key = (m.start(), m.end())
                        if key in seen or m.end() - m.start() < 2:
                            continue
                        seen.add(key)
                        spans.append(Span(start=m.start(), end=m.end(), text=m.group(),
                                          label=label, source="ollama", confidence=0.85))
                continue
            for idx in occ:
                key = (idx, idx + len(ent_text))
                if key in seen:
                    continue
                seen.add(key)
                spans.append(Span(
                    start=idx, end=idx + len(ent_text),
                    text=text[idx:idx + len(ent_text)],
                    label=label,
                    source="ollama",
                    confidence=0.85
                ))
        return spans
    except Exception as e:
        import sys
        print(f"Ollama error: {type(e).__name__}: {e}", file=sys.stderr)
        return []


def merge_spans(all_spans: list[Span]) -> list[Span]:
    """Merge overlapping spans, preferring higher-confidence or more specific labels."""
    if not all_spans:
        return []

    sorted_spans = sorted(all_spans, key=lambda s: (s.start, -(s.end - s.start)))
    merged = [sorted_spans[0]]

    for span in sorted_spans[1:]:
        prev = merged[-1]
        if span.start < prev.end:
            if span.end > prev.end:
                prev.end = span.end
                prev.text = prev.text  # keep original
            if span.confidence > prev.confidence:
                prev.label = span.label
                prev.source = span.source
        else:
            merged.append(span)

    return merged


def pseudonym_map(spans: list[Span], seed: str = "") -> dict[str, str]:
    """Generate consistent pseudonyms for detected entities."""
    names = ["Алексей", "Мария", "Дмитрий", "Елена", "Сергей", "Анна", "Павел", "Ольга"]
    cities = ["Город-А", "Город-Б", "Город-В", "Город-Г"]
    orgs = ["Организация-1", "Организация-2", "Организация-3"]

    mapping = {}
    name_idx = city_idx = org_idx = 0

    for span in spans:
        key = span.text.strip()
        if key in mapping:
            continue
        if span.label == "PERSON" or span.label == "PRIVATE_PERSON":
            mapping[key] = f"[{names[name_idx % len(names)]}]"
            name_idx += 1
        elif span.label in ("LOCATION", "ADDRESS", "PRIVATE_ADDRESS"):
            mapping[key] = f"[{cities[city_idx % len(cities)]}]"
            city_idx += 1
        elif span.label == "ORG":
            mapping[key] = f"[Организация-{org_idx + 1}]"
            org_idx += 1
        elif span.label in ("PHONE", "PRIVATE_PHONE"):
            mapping[key] = "[ТЕЛЕФОН]"
        elif span.label == "DATE" or span.label == "PRIVATE_DATE":
            mapping[key] = "[ДАТА]"
        elif span.label == "MEDICATION":
            mapping[key] = "[ПРЕПАРАТ]"
        elif span.label in ("ACCOUNT_NUMBER", "ID"):
            mapping[key] = "[ID-НОМЕР]"
        else:
            mapping[key] = f"[{span.label}]"
    return mapping


def redact(text: str, spans: list[Span], use_pseudonyms: bool = False) -> str:
    """Replace detected spans with placeholders or pseudonyms."""
    if use_pseudonyms:
        mapping = pseudonym_map(spans)

    result = []
    last_end = 0
    for span in sorted(spans, key=lambda s: s.start):
        result.append(text[last_end:span.start])
        if use_pseudonyms:
            key = span.text.strip()
            result.append(mapping.get(key, f"<{span.label}>"))
        else:
            result.append(f"<{span.label}>")
        last_end = span.end
    result.append(text[last_end:])
    return "".join(result)


def anonymize(text: str, layers: list[str] = None, model: str = "qwen2.5:3b",
              pseudonyms: bool = False) -> AnonymizationResult:
    """Run all anonymization layers and produce result."""
    if layers is None:
        layers = ["natasha", "ollama", "regex"]

    # "opf" is a deprecated alias for the deterministic "regex" layer that
    # replaced the OpenAI Privacy Filter.
    layers = ["regex" if l == "opf" else l for l in layers]

    all_spans = []
    warnings = []

    if "natasha" in layers:
        natasha_spans = run_natasha(text)
        all_spans.extend(natasha_spans)
        if not natasha_spans:
            warnings.append("Natasha returned no entities — may not be installed")

    if "ollama" in layers:
        ollama_spans = run_ollama(text, model)
        all_spans.extend(ollama_spans)
        if not ollama_spans:
            warnings.append("Ollama returned no entities — is the model running?")

    if "regex" in layers:
        regex_spans = run_regex(text)
        all_spans.extend(regex_spans)
        if not regex_spans:
            warnings.append("Regex layer found no emails/phones/IDs (none present, or scrubadub/phonenumbers not installed)")

    merged = merge_spans(all_spans)
    redacted_text = redact(text, merged, pseudonyms)

    stats = {}
    for span in merged:
        stats[span.label] = stats.get(span.label, 0) + 1

    warnings.append("Manual review recommended: contextual identifiers (unique life situations) cannot be detected automatically")

    return AnonymizationResult(
        original_length=len(text),
        redacted_text=redacted_text,
        spans=[asdict(s) for s in merged],
        stats=stats,
        warnings=warnings
    )


def encrypt_file(filepath: str, password: str) -> str:
    """AES-256 encrypt a file using openssl."""
    out_path = filepath + ".enc"
    result = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2",
         "-in", filepath, "-out", out_path, "-pass", f"pass:{password}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Encryption failed: {result.stderr}")
    return out_path


def _selftest_relative_dates():
    """Unit assertions for the relative/colloquial DATE recognizers (T6).

    Proves the new patterns MATCH the intended relative/spelled-out/month-name
    forms in both languages and DO NOT match a timestamp, an age, or a non-date
    discourse marker ("в прошлый раз" = "last time"). Run: ``anonymize.py --selftest``.
    """
    def dates(t):
        return {s.text for s in run_regex(t) if s.label == "DATE"}

    # EN positives — exactly the relative forms the EN gold annotates as DATE PII
    for s in ("last Tuesday", "12 December", "March 3rd, 2024", "5th of January",
              "19th of the month", "June 14 2019", "two weeks ago", "3 days ago",
              "yesterday", "next Monday", "December/48", "18th April 2020"):
        assert dates("We met " + s + ".") , f"EN should match {s!r}"

    # RU positives — spelled-out / weekday-anchored / N-ago / month-name dates
    for s in ("третьего февраля", "12 декабря", "в прошлый вторник",
              "2 недели назад", "10 лет назад", "до Нового года", "первого мая"):
        assert dates("Это было " + s + ".") , f"RU should match {s!r}"

    # Negatives — must NOT be tagged DATE (timestamp / age / discourse marker)
    assert not dates("Запись 00:12:45 в логе."), "timestamp must not be a DATE"
    assert not dates("I am 34 years old."), "age must not be a DATE"
    assert not dates("Мне 34 года, работаю."), "RU age must not be a DATE"
    assert not dates("Как в прошлый раз договаривались."), "'в прошлый раз' is not a date"
    assert not dates("Account 7722 4455 8811 ready."), "account id must not be a DATE"

    print("✓ relative-date recognizer self-test passed (EN+RU positives, "
          "timestamp/age/discourse-marker negatives)")


def main():
    parser = argparse.ArgumentParser(description="Three-layer therapy transcript anonymizer")
    parser.add_argument("input", nargs="?", help="Input file (or stdin if omitted)")
    parser.add_argument("-o", "--output", help="Output file (stdout if omitted)")
    parser.add_argument("--layers", default="natasha,regex,ollama",
                        help="Comma-separated layers to run (default: natasha,regex,ollama). "
                        "'opf' is accepted as a deprecated alias for 'regex'.")
    parser.add_argument("--model", default="qwen2.5:3b", help="Ollama model (default: qwen2.5:3b). "
                        "Use a non-reasoning model: qwen3 routes output to a separate 'thinking' "
                        "field and exhausts num_predict before emitting JSON, yielding no entities.")
    parser.add_argument("--pseudonyms", action="store_true", help="Use consistent pseudonyms instead of tags")
    parser.add_argument("--json", action="store_true", help="Output full JSON report")
    parser.add_argument("--encrypt", metavar="PASSWORD", help="Encrypt output with AES-256")
    parser.add_argument("--batch", metavar="DIR", help="Process all .txt/.md files in directory")
    parser.add_argument("--selftest", action="store_true",
                        help="Run the relative-date recognizer unit assertions and exit")
    args = parser.parse_args()

    if args.selftest:
        _selftest_relative_dates()
        return

    layers = [l.strip() for l in args.layers.split(",")]

    if args.batch:
        import glob
        files = glob.glob(os.path.join(args.batch, "*.txt")) + glob.glob(os.path.join(args.batch, "*.md"))
        out_dir = args.output or args.batch + "_anonymized"
        os.makedirs(out_dir, exist_ok=True)

        total_stats = {}
        for f in sorted(files):
            with open(f) as fh:
                text = fh.read()
            result = anonymize(text, layers, args.model, args.pseudonyms)
            out_file = os.path.join(out_dir, os.path.basename(f))
            with open(out_file, "w") as fh:
                fh.write(result.redacted_text)
            for k, v in result.stats.items():
                total_stats[k] = total_stats.get(k, 0) + v
            print(f"  {os.path.basename(f)}: {sum(result.stats.values())} entities", file=sys.stderr)

        print(json.dumps({"files": len(files), "output_dir": out_dir, "total_stats": total_stats}, indent=2, ensure_ascii=False))
        return

    if args.input:
        with open(args.input) as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    result = anonymize(text, layers, args.model, args.pseudonyms)

    if args.json:
        output = json.dumps(asdict(result), indent=2, ensure_ascii=False)
    else:
        output = result.redacted_text

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        if args.encrypt:
            enc_path = encrypt_file(args.output, args.encrypt)
            print(f"Encrypted: {enc_path}", file=sys.stderr)
    else:
        print(output)

    print(f"\nEntities found: {result.stats}", file=sys.stderr)
    for w in result.warnings:
        print(f"⚠ {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
