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

# --- YAML frontmatter direct-identifier recognizer (T8 leak fix) -------------
# Session transcripts begin with a leading `---...---` YAML block whose
# `client_id` (a first name, often Latin/lowercase: marina/igor/alina/...) is a
# DIRECT IDENTIFIER the regex/NER/LLM layers structurally never see as a name.
# It survived into the "redacted" text and made cross-session linkability a
# trivial exact-string match (AUC 1.0). We mask the VALUE of identifying keys
# inside the frontmatter block only.
#
#   client_id -> ID       (a stable per-client handle, not a free-text name)
#   client/patient/name/therapist -> PERSON  (but ONLY if the value is a real
#       name; single-letter role codes "Т"/"К"/"T"/"C" are speaker tags, not
#       identifiers, and are left intact).
#
# Keys are case-insensitive; values may be Latin or Cyrillic, quoted or not.
# Non-name fields (date/modality/session_no/synthetic) are deliberately untouched.
_FM_KEY_LABEL = {
    "client_id": "ID",
    "client": "PERSON",
    "patient": "PERSON",
    "name": "PERSON",
    "therapist": "PERSON",
}
# A single Latin/Cyrillic letter (optionally quoted) is a speaker ROLE code, not
# an identifier — never mask it.
_FM_ROLE_CODE = re.compile(r"^[A-Za-zА-Яа-яЁё]$")
# Leading frontmatter block: opening `---` on the first line, closing `---`.
_FM_BLOCK = re.compile(r"\A﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL)
# One `key: value` line. Captures the value (quoted or bare) with its offsets.
_FM_LINE = re.compile(
    r"(?im)^[ \t]*([A-Za-z_][\w-]*)[ \t]*:[ \t]*"
    r"(?:\"([^\"\r\n]*)\"|'([^'\r\n]*)'|([^\r\n#]*?))[ \t]*(?:#.*)?$")


def run_frontmatter(text: str) -> list[Span]:
    """Mask the VALUE of identifying keys inside the leading YAML frontmatter.

    Direct-identifier de-leak (T8): the per-client `client_id` first name and any
    real name in client/patient/name/therapist keys are emitted as spans with the
    correct char offsets. Single-letter speaker codes (Т/К/T/C) are left intact.
    Only the leading `---...---` block is scanned; non-name fields are untouched.
    """
    spans = []
    block = _FM_BLOCK.match(text)
    if not block:
        return spans
    inner = block.group(1)
    base = block.start(1)
    for m in _FM_LINE.finditer(inner):
        key = m.group(1).lower()
        label = _FM_KEY_LABEL.get(key)
        if label is None:
            continue
        # whichever alternative matched is the value; find its group index for offsets
        for gi in (2, 3, 4):
            if m.group(gi) is not None:
                val = m.group(gi)
                vstart = base + m.start(gi)
                vend = base + m.end(gi)
                break
        val = val.strip()
        if not val:
            continue
        # role codes (single letter) are speaker tags, not identifiers
        if _FM_ROLE_CODE.match(val):
            continue
        spans.append(Span(start=vstart, end=vend, text=text[vstart:vend],
                          label=label, source="regex"))
    return spans


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

    # YAML frontmatter direct identifiers (T8 leak fix): mask client_id and any
    # real name in client/patient/name/therapist keys; skip single-letter codes.
    spans.extend(run_frontmatter(text))

    return spans


_DEFAULT_PII_PROMPT_TEMPLATE = (
    'Extract ALL PII, including quasi-identifiers that narrow identity. '
    'Include MEDICATIONS with dosages, AGES (also spelled-out, e.g. "тридцать четыре года"), '
    'and PROFESSIONS/occupations. Return ONLY JSON array '
    '[{"text":"...","type":"PERSON|LOCATION|ORG|PHONE|DATE|ADDRESS|MEDICATION|ID|AGE|PROFESSION"}]. '
    'No explanations.\n\nText: {text}'
)


def _load_llm_prompt_template() -> str:
    """Return the experiment prompt template, or the verified default prompt."""
    prompt_file = os.environ.get("LLM_PROMPT_FILE")
    if prompt_file:
        with open(prompt_file, encoding="utf-8") as f:
            return f.read()
    return os.environ.get("LLM_PROMPT_TEMPLATE", _DEFAULT_PII_PROMPT_TEMPLATE)


def _render_llm_prompt(text: str, prompt_template: Optional[str] = None) -> str:
    """Render a prompt template without requiring JSON braces to be escaped."""
    template = prompt_template if prompt_template is not None else _load_llm_prompt_template()
    if "{text}" in template:
        return template.replace("{text}", text)
    return template.rstrip() + "\n\nText: " + text


def _extract_json_array(output: str):
    """Return the first valid JSON array in a model response.

    Local models sometimes emit a valid array followed by another array or prose.
    A greedy ``[.*]`` match turns that into "Extra data" and discards all spans.
    Trying each ``[`` offset with JSONDecoder keeps strict JSON while tolerating
    harmless trailing text.
    """
    decoder = json.JSONDecoder()
    for i, ch in enumerate(output):
        if ch != "[":
            continue
        try:
            obj, _end = decoder.raw_decode(output[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, list):
            return obj
    return None


def iter_text_chunks(text: str, chunk_chars: int = 2500, overlap: int = 200):
    """Yield ``(offset, chunk)`` pairs, preferring transcript-friendly boundaries.

    This is semantic-enough for transcripts: keep turns/paragraphs intact when
    possible, and use overlap so identifiers near a boundary are still visible.
    It avoids embedding-based semantic chunking, which would add a second model
    and would not help exact character-offset scoring.
    """
    if chunk_chars <= 0 or len(text) <= chunk_chars:
        yield 0, text
        return
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_chars:
        raise ValueError("overlap must be smaller than chunk_chars")

    start = 0
    n = len(text)
    while start < n:
        hard_end = min(n, start + chunk_chars)
        if hard_end == n:
            yield start, text[start:hard_end]
            return

        lower = start + max(1, chunk_chars // 3)
        end = hard_end
        for sep in ("\n\n", "\n", ". ", "? ", "! "):
            pos = text.rfind(sep, lower, hard_end)
            if pos != -1:
                end = pos + len(sep)
                break
        if end <= start:
            end = hard_end

        yield start, text[start:end]
        start = max(end - overlap, start + 1)


def run_ollama_chunked(text: str, model: str = "qwen2.5:3b",
                       prompt_template: Optional[str] = None,
                       chunk_chars: int = 2500, overlap: int = 200) -> list[Span]:
    """Run the LLM detector on overlapping chunks and map spans to full text."""
    spans: list[Span] = []
    seen = set()
    for offset, chunk in iter_text_chunks(text, chunk_chars, overlap):
        for span in run_ollama(chunk, model, prompt_template=prompt_template):
            start = offset + span.start
            end = offset + span.end
            if not (0 <= start < end <= len(text)):
                continue
            key = (start, end, span.label)
            if key in seen:
                continue
            seen.add(key)
            spans.append(Span(
                start=start,
                end=end,
                text=text[start:end],
                label=span.label,
                source=span.source,
                confidence=span.confidence,
            ))
    return spans


def run_ollama(text: str, model: str = "qwen2.5:3b",
               prompt_template: Optional[str] = None) -> list[Span]:
    """Layer 3: Local LLM via Ollama HTTP API for medications, dates, contextual IDs."""
    import re
    try:
        import urllib.request

        prompt = _render_llm_prompt(text, prompt_template)

        # Engine-agnostic local-LLM transport. LLM_API=openai targets the
        # OpenAI-compatible /v1/chat/completions endpoint that llama.cpp's
        # `llama-server` (primary, memory-efficient — pin the .gguf + quant),
        # vLLM, and Ollama all expose. Default "ollama" keeps /api/chat for an
        # existing local Ollama. Base URL: LLM_BASE_URL or OLLAMA_HOST.
        api = os.environ.get("LLM_API", "ollama").lower()
        base = os.environ.get("LLM_BASE_URL",
                              os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        messages = [{"role": "user", "content": prompt}]
        # LLM_TEMPERATURE lets run-variance experiments (R5) vary sampling without
        # touching the prompt; defaults to 0 for the deterministic default stack.
        temperature = float(os.environ.get("LLM_TEMPERATURE", "0"))
        # Reasoning models (e.g. Qwen3) spend output budget on a <think> block
        # before the JSON; LLM_MAX_TOKENS lets a cloud run raise the cap so long
        # transcripts don't truncate the answer. Default 2048 keeps local behaviour.
        max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "2048"))
        headers = {"Content-Type": "application/json"}
        if api == "openai":
            url = base + "/v1/chat/completions"
            payload = json.dumps({"model": model, "messages": messages,
                                  "temperature": temperature, "max_tokens": max_tokens,
                                  "stream": False}).encode()
            # Bearer auth for cloud OpenAI-compatible providers (Cerebras/Groq/etc).
            key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
            if key:
                headers["Authorization"] = "Bearer " + key
            # Some providers front their API with Cloudflare, which 403s (error
            # 1010) requests with a default urllib User-Agent. A browser UA passes.
            headers["User-Agent"] = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                                     "Chrome/124.0 Safari/537.36")
        else:
            url = base + "/api/chat"
            # Gemma 4 and other reasoning-capable Ollama models may otherwise
            # spend the whole generation budget in message.thinking and return
            # an empty content field. Non-reasoning models ignore this flag.
            payload = json.dumps({"model": model, "messages": messages, "stream": False,
                                  "think": False,
                                  "options": {"temperature": temperature, "num_predict": max_tokens}}).encode()

        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())

        if api == "openai":
            output = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        else:
            output = data.get("message", {}).get("content", "")
        output = re.sub(r'<think>.*?</think>', '', output, flags=re.DOTALL)

        entities = _extract_json_array(output)
        if entities is None:
            return []
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


# --- RU entity propagation (dependency-free) -------------------------------
# The benchmark's residual-risk finding: a name is detected somewhere but a
# different *variant* leaks — an inflected case form (Артёмом, Денису), a
# vocative (Роман,), a capitalized common-word collision (Веру), or a Latin
# transliteration (Timur). Once ANY mention of a PERSON is detected, propagate
# the mask to all its variants. No model/dict dependency — runs anywhere.

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}
_WORD = re.compile(r"[А-Яа-яЁё]+|[A-Za-z]+")

# Russian first names that are also common nouns — for these, a lowercase exact
# occurrence is almost always the common word, so it must stay capitalization-gated.
_COMMON_COLLISIONS = {
    "вера", "роман", "инсайт", "мир", "надежда", "любовь", "роза",
    "лилия", "майя", "ангел", "марс", "владимир",
}

# Patronymic suffixes (incl. case forms). Capitalized RU words ending here are
# almost exclusively patronymics — a direct identifier the name layers miss when
# the root first name isn't separately mentioned (e.g. "Тимур Маратович").
_PATRONYMIC = re.compile(
    r"\b[А-ЯЁ][а-яё]+(?:ович|овича|овичу|овичем|овиче"
    r"|евич|евича|евичу|евичем|евиче"
    r"|овна|овны|овне|овну|овной"
    r"|евна|евны|евне|евну|евной"
    r"|ична|ичны|ичне|ичну|ичной"
    r"|инична|иничны|иничне|иничну|иничной)\b")


def find_patronymics(text: str) -> list[Span]:
    """Detect Russian patronymics (Маратович, Сергеевна) as PERSON spans —
    independent of the detected first names, since the root is often absent."""
    return [Span(start=m.start(), end=m.end(), text=m.group(),
                 label="PERSON", source="patronymic", confidence=0.9)
            for m in _PATRONYMIC.finditer(text)]


def translit_ru(s: str) -> str:
    return "".join(_TRANSLIT.get(ch, ch) for ch in s.lower())


def _same_name(a: str, b: str) -> bool:
    """True if `a` and `b` are the same Russian name differing only by a short
    case inflection (shared stem). Short tokens (<4) require an exact match."""
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    n = min(len(a), len(b))
    if n < 4:
        return False
    cp = 0
    while cp < n and a[cp] == b[cp]:
        cp += 1
    # stems agree to within a 2-char divergence point and both tails are short
    return cp >= n - 2 and (len(a) - cp) <= 3 and (len(b) - cp) <= 3


def propagate_names(text: str, person_surfaces, capitalized_only: bool = True,
                    translit: bool = True) -> list[Span]:
    """Mask every morphological / transliterated variant of an already-detected
    PERSON name. `person_surfaces` is the set of detected name strings."""
    cyr_stems, cyr_exact, latin_forms = [], set(), set()
    for nm in person_surfaces:
        for tok in _WORD.findall(nm or ""):
            if len(tok) < 2:
                continue
            if re.match(r"[А-Яа-яЁё]", tok):
                cyr_stems.append(tok)
                cyr_exact.add(tok.lower())
                if translit:
                    latin_forms.add(translit_ru(tok))
            else:
                latin_forms.add(tok.lower())
    spans = []
    for m in _WORD.finditer(text):
        w = m.group()
        if len(w) < 2:
            continue
        is_cyr = bool(re.match(r"[А-Яа-яЁё]", w))
        hit = False
        if is_cyr:
            lw = w.lower()
            # Exact match to a detected name. Long, non-colliding surnames may be
            # masked even when dictated lowercase (e.g. "лебедев" in an email);
            # short or common-word names stay capitalization-gated.
            exact_lower_ok = (lw in cyr_exact and len(w) >= 5
                              and lw not in _COMMON_COLLISIONS)
            if lw in cyr_exact or any(_same_name(w, n) for n in cyr_stems):
                hit = True
                if capitalized_only and not w[0].isupper() and not exact_lower_ok:
                    hit = False
        elif translit and w.lower() in latin_forms:
            hit = True  # transliterated name (e.g. Timur) — always mask
        if hit:
            spans.append(Span(start=m.start(), end=m.end(), text=w,
                              label="PERSON", source="propagate", confidence=0.8))
    return spans


# --- RU AGE recognizer (spelled-out cardinals + numeric, age-anchored) -------
# AGE is a 0-deterministic-recall quasi type. Russian ages are usually spelled-out
# cardinals anchored to год/года/лет, a "возраст" cue, or a pronoun ("мне сорок
# один"). The trap is relative-time expressions ("пять лет назад", "через три
# года") — guarded out so they are never treated as ages.
_AGE_TENS = "двадцать|тридцать|сорок|пятьдесят|шестьдесят|семьдесят|восемьдесят|девяносто|сто"
_AGE_UNITS = "один|одна|два|две|три|четыре|пять|шесть|семь|восемь|девять"
_AGE_TEENS = ("десять|одиннадцать|двенадцать|тринадцать|четырнадцать|пятнадцать|"
              "шестнадцать|семнадцать|восемнадцать|девятнадцать")
_AGE_CARD = rf"(?:(?:{_AGE_TENS})(?:\s+(?:{_AGE_UNITS}))?|{_AGE_TEENS}|{_AGE_UNITS})"
_AGE_NUM = rf"(?:{_AGE_CARD}|\d{{1,3}})"
_AGE_YEARS = r"(?:год(?:а|у|ом|е|ов)?|лет|годик(?:а|ов)?)"
# A person reference disambiguates "N лет" as an AGE rather than a duration
# (the precision trap: "двадцать лет всё то же" / "отца нет семь лет" are NOT ages).
_AGE_PERSON = (r"(?:мужик\w*|мужчин\w*|женщин\w*|девушк\w*|парн\w*|пацан\w*|"
               r"человек\w*|тётк\w*|тетк\w*|дядьк\w*|бабушк\w*|дедушк\w*|мальчик\w*|девочк\w*)")
_AGE_FILL = r"(?:уже\s+|сейчас\s+|почти\s+|только\s+)?"
# Strong, unambiguous cue — always an age.
_AGE_STRONG = re.compile(rf"(?i)\b(?:возраст\w*|исполни\w+|стукнул\w+)[\s—:\-–]+{_AGE_FILL}({_AGE_NUM})\b")
# Pronoun cue — an age ONLY when the number is a predicate (followed by a clause
# boundary / год-лет / conjunction), NOT when it counts a following noun
# ("дал ей ОДИН проект", "сто РАЗ").
_AGE_BOUND = (r"(?=\s*(?:$|[.,;:!?…)»\"'—–-]|год|лет"
              r"|\b(?:и|а|но|уже|всего|только|скоро|будет|было)\b))")
_AGE_PRON = re.compile(rf"(?i)\b(?:мне|тебе|ему|ей|вам|нам|им)[\s—:\-–]+{_AGE_FILL}({_AGE_NUM})\b{_AGE_BOUND}")
# number + год/лет + person ("сорок пять лет мужику")
_AGE_NUM_PERSON = re.compile(rf"(?i)\b({_AGE_NUM})\s+{_AGE_YEARS}\s+{_AGE_PERSON}")


def find_ages(text: str) -> list[Span]:
    """Detect Russian ages anchored to an age context — a pronoun/возраст cue
    ("мне сорок один") or N лет + a person reference ("сорок пять лет мужику").
    Bare "N лет" is deliberately NOT matched: in transcripts it is overwhelmingly
    a duration ("двадцать лет вместе"), so matching it destroys precision."""
    spans, seen = [], set()

    def add(m):
        a, b = m.start(1), m.end(1)
        if (a, b) in seen:
            return
        seen.add((a, b))
        spans.append(Span(start=a, end=b, text=text[a:b], label="AGE",
                          source="age", confidence=0.85))

    for pat in (_AGE_STRONG, _AGE_PRON, _AGE_NUM_PERSON):
        for m in pat.finditer(text):
            add(m)
    return spans


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

    # RU entity propagation: mask inflected/vocative/transliterated variants of
    # any PERSON already detected by a prior layer (closes the benchmark's
    # residual name-variant leaks). Skipped if explicitly disabled.
    if "no-propagate" not in layers:
        all_spans.extend(find_patronymics(text))  # RU patronymics (direct IDs)
        all_spans.extend(find_ages(text))         # RU spelled-out / numeric ages
        person_surfaces = {s.text for s in all_spans if s.label == "PERSON"}
        if person_surfaces:
            all_spans.extend(propagate_names(text, person_surfaces))

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
