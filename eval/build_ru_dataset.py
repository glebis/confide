#!/usr/bin/env python3
"""Build the Russian gold PII dataset from synthetic answer keys.

Source of truth: sessions-ru/client-{a..f}/ANSWER-KEY.md embedded PII
inventories. The answer keys give *values*; this script locates every surface
form (incl. Russian morphological variants) across all 30 session transcripts
and emits char-offset gold spans.

Output: ../sessions-ru/pii-eval-ru.jsonl — one row per session, schema:
  {
    "doc_id": "ru-a-s01", "lang": "ru", "client": "a", "session": 1,
    "text": "<full raw file text the detectors also see>",
    "spans": [
      {"start": int, "end": int, "type": <CANON>, "value": str,
       "identifier_class": "direct"|"quasi", "entity_id": str,
       "llm_required": bool}
    ]
  }

CANON types: PERSON, LOCATION, ORG, PHONE, EMAIL, ID, DATE, MEDICATION, AGE,
PROFESSION. `entity_id` groups all mentions of one real-world entity so the
scorer can compute TAB-style entity-level recall (an entity is "protected" only
if ALL its mentions are masked). `identifier_class` follows TAB's direct vs
quasi-identifier split. `llm_required` marks entities that the deterministic
layers (Natasha NER + regex) structurally cannot catch — medications, ages
(esp. spelled-out), contextual dates, professions — i.e. the cases that need
the Ollama/qwen layer to pass.

Each entity is a tuple: (entity_id, CANON_type, identifier_class, llm_required,
[regex patterns]). Patterns use Python re with full-Unicode \\w (Cyrillic-aware).
After building, run with --review to dump every matched span with context for
human verification (gold must be hand-checked).
"""
import argparse
import json
import os
import re

# Single source of truth for the type->harm-level mapping (HARM-TAXONOMY.md).
# Imported from the scorer so the gold builder and harm_weighted_recall agree;
# do NOT define a second, conflicting mapping here.
from score_bench import HARM_LEVEL

HERE = os.path.dirname(os.path.abspath(__file__))
RU = os.path.join(HERE, "..", "sessions-ru")

# Per-client entity inventory. Patterns are matched case-insensitively over the
# full raw file text. `B` = word-ish boundary that also respects Cyrillic.
WB = r"(?<![\w])"   # left boundary (no preceding word char)
WE = r"(?![\w])"    # right boundary

CLIENTS = {
    "a": [
        # entity_id, type, class, llm_required, [patterns]
        ("a-marina",     "PERSON",     "direct", False, [rf"{WB}Марин\w*{WE}", rf"{WB}Волков\w*{WE}", rf"{WB}Сергеевн\w*{WE}", r"(?<=client_id: )marina"]),
        ("a-andrey",     "PERSON",     "direct", False, [rf"{WB}Андре[йяюе]\w*{WE}"]),
        ("a-petrova",    "PERSON",     "direct", False, [rf"{WB}Петров[аойуе]\w*{WE}"]),
        ("a-boss",       "PERSON",     "direct", False, [rf"{WB}Дмитри[йяюе]\w*\s+Олегович\w*{WE}"]),
        ("a-kaluga",     "LOCATION",   "quasi",  False, [rf"{WB}Калуг[аеуи]\w*{WE}"]),
        ("a-tverskaya",  "LOCATION",   "direct", False, [rf"{WB}Тверск\w*{WE}"]),
        ("a-neuromed",   "ORG",        "direct", False, [rf"Нейромед\w*"]),
        ("a-yandex",     "ORG",        "quasi",  False, [rf"Яндекс\w*"]),
        ("a-sertraline", "MEDICATION", "quasi",  True,  [rf"{WB}сертралин\w*{WE}"]),
        ("a-phone",      "PHONE",      "direct", False, [r"\+7-916-555-21-43"]),
        ("a-email",      "EMAIL",      "direct", False, [r"marina\.volkova@example\.ru"]),
        ("a-policy",     "ID",         "direct", False, [r"7722-4455-8811"]),
        ("a-date",       "DATE",       "quasi",  True,  [rf"{WB}15\s+январ\w*{WE}"]),
        # Age appears in the body only spelled-out ("тридцать четыре года"); the
        # bare "34" occurrences are all timestamp seconds (00:05:34), not ages.
        ("a-age",        "AGE",        "quasi",  True,  [rf"{WB}тридцать четыре{WE}"]),
        ("a-profession", "PROFESSION", "quasi",  True,  [rf"{WB}маркетолог\w*{WE}"]),
        # Session dates (frontmatter DD.MM.YYYY). %V → per-value entity_id so each
        # distinct date is its own entity. No deterministic RU layer tags dates.
        ("a-date-%V",    "DATE",       "quasi",  True,  [r"\b\d{1,2}\.\d{2}\.20\d{2}\b", rf"{WB}15\s+январ\w*{WE}"]),
        # --- v2 adjudicated additions (IAA blind spots, ru-a-s01) ---
        # Spelled-out policy/phone read aloud at the card check — real PII the regex
        # layer structurally cannot catch (hence llm_required), missed by v1 gold.
        ("a-policy-spelled", "ID",    "direct", True, [r"семь-семь-два-два, четыре-четыре-пять-пять, восемь-восемь-один-один"]),
        ("a-phone-spelled",  "PHONE", "direct", True, [r"плюс семь, девять-один-шесть, пять-пять-пять, двадцать один, сорок три"]),
        ("a-careerlevel",    "PROFESSION", "quasi", True, [rf"{WB}младшего специалиста{WE}"]),
    ],
    "b": [
        ("b-igor",       "PERSON",     "direct", False, [rf"{WB}Игор[ьяею]\w*{WE}", rf"{WB}Соколов\w*{WE}", rf"{WB}Анатольевич\w*{WE}"]),
        ("b-svetlana",   "PERSON",     "direct", False, [rf"{WB}Светлан[аыуе]\w*{WE}"]),
        ("b-alexey",     "PERSON",     "direct", False, [rf"{WB}Алексе[йяюе]\w*{WE}"]),
        ("b-pavel",      "PERSON",     "direct", False, [rf"{WB}Павел{WE}", rf"{WB}Павл[аеу]\w*{WE}"]),
        ("b-kostroma",   "LOCATION",   "quasi",  False, [rf"{WB}Костром[аеуы]\w*{WE}"]),
        ("b-zavolzhsky", "LOCATION",   "quasi",  False, [rf"{WB}Заволжск\w*{WE}"]),
        ("b-moscow",     "LOCATION",   "quasi",  False, [rf"{WB}Москв[аеуы]\w*{WE}"]),
        ("b-kontur",     "ORG",        "quasi",  False, [rf"Контур\w*"]),
        ("b-sber",       "ORG",        "quasi",  False, [rf"Сбер\w*"]),
        ("b-fluoxetine", "MEDICATION", "quasi",  True,  [rf"{WB}флуоксетин\w*{WE}"]),
        ("b-email",      "EMAIL",      "direct", False, [r"i\.sokolov@example\.com"]),
        ("b-phone",      "PHONE",      "direct", False, [r"\+7-910-444-78-12"]),
        ("b-date",       "DATE",       "quasi",  True,  [rf"{WB}3\s+феврал\w*{WE}"]),
        # "сорок один год" (spoken) + bare "41" in the card note; the negative
        # look-arounds keep timestamp seconds (00:08:41) out.
        ("b-age",        "AGE",        "quasi",  True,  [rf"{WB}сорок один{WE}", r"(?<![:\d])41(?![:\d])"]),
        ("b-profession", "PROFESSION", "quasi",  True,  [rf"{WB}программист\w*{WE}"]),
        ("b-date-%V",    "DATE",       "quasi",  True,  [r"\b\d{1,2}\.\d{2}\.20\d{2}\b", rf"{WB}третьего феврал\w*{WE}", rf"{WB}3\s+феврал\w*{WE}"]),
        # --- v2 adjudicated additions (IAA blind spots, client-b) ---
        ("b-ekaterinburg", "LOCATION",  "quasi", False, [rf"Екатеринбург\w*", rf"екатеринбург\w*"]),
        ("b-role",         "PROFESSION","quasi", True,  [rf"{WB}тимлид\w*{WE}", rf"{WB}[Бб]экенд\w*{WE}"]),
        ("b-igor-latin",   "PERSON",    "direct", False, [r"(?<=client_id: )igor"]),
    ],
    # --- new clients (longer corpus); PII planted by the generation agents ---
    "c": [  # Алина, UX-дизайнер, СПб
        ("c-alina",       "PERSON",     "direct", False, [rf"{WB}Алин[аыуе]\w*{WE}", rf"{WB}Кузнецов[а-я]+{WE}", rf"{WB}Сергеевн[а-я]+{WE}"]),
        ("c-maksim",      "PERSON",     "direct", False, [rf"{WB}Максим[а-я]*{WE}"]),
        ("c-zaytseva",    "PERSON",     "direct", False, [rf"{WB}Зайцев[а-я]+{WE}"]),
        ("c-boss",        "PERSON",     "direct", False, [rf"{WB}Ольг[а-я]+\s+Викторовн[а-я]+{WE}"]),
        ("c-alliance",    "ORG",        "direct", False, [r"Альянс\w*"]),
        ("c-avito",       "ORG",        "quasi",  False, [r"Авито\w*"]),
        ("c-escitalopram","MEDICATION", "quasi",  True,  [rf"{WB}эсциталопрам\w*{WE}"]),
        ("c-phone",       "PHONE",      "direct", False, [r"\+7-921-333-44-55"]),
        ("c-email",       "EMAIL",      "direct", False, [r"alina\.k@example\.ru"]),
        ("c-snils",       "ID",         "direct", False, [r"211-333-444[ -]?55"]),
        ("c-age",         "AGE",        "quasi",  True,  [rf"{WB}двадцать девять{WE}"]),
        ("c-profession",  "PROFESSION", "quasi",  True,  [rf"{WB}UX-?дизайнер\w*{WE}", rf"{WB}дизайнер\w*{WE}"]),
        ("c-spb",         "LOCATION",   "quasi",  False, [rf"{WB}Санкт-Петербург\w*{WE}", rf"{WB}Петербург\w*{WE}"]),
        ("c-date-%V",     "DATE",       "quasi",  True,  [r"\b\d{1,2}\.\d{2}\.20\d{2}\b"]),
    ],
    "d": [  # Роман, предприниматель, Новосибирск
        ("d-roman",       "PERSON",     "direct", False, [rf"{WB}Роман[а-я]*{WE}", rf"{WB}Лебедев[а-я]*{WE}", rf"{WB}Андреевич[а-я]*{WE}"]),
        ("d-natalya",     "PERSON",     "direct", False, [rf"{WB}Наталь[а-я]+{WE}", rf"{WB}Наталь[а-я]+{WE}"]),
        ("d-morozov",     "PERSON",     "direct", False, [rf"{WB}Морозов[а-я]*{WE}"]),
        ("d-artem",       "PERSON",     "direct", False, [rf"{WB}Артём[а-я]*{WE}", rf"{WB}Артем[а-я]*{WE}"]),
        ("d-insight",     "ORG",        "direct", False, [r"Инсайт\w*"]),
        ("d-sibtrans",    "ORG",        "quasi",  False, [r"СибТранс\w*"]),
        ("d-bupropion",   "MEDICATION", "quasi",  True,  [rf"{WB}бупропион\w*{WE}"]),
        ("d-phone",       "PHONE",      "direct", False, [r"\+7-913-222-11-00"]),
        ("d-email",       "EMAIL",      "direct", False, [r"r\.lebedev@example\.com"]),
        ("d-snils",       "ID",         "direct", False, [r"322-111-000[ -]?44"]),
        ("d-age",         "AGE",        "quasi",  True,  [rf"{WB}сорок пять{WE}"]),
        ("d-profession",  "PROFESSION", "quasi",  True,  [rf"{WB}предпринимател[а-я]+{WE}", rf"{WB}логистик[а-я]+{WE}"]),
        ("d-nsk",         "LOCATION",   "quasi",  False, [rf"{WB}Новосибирск\w*{WE}"]),
        ("d-date-%V",     "DATE",       "quasi",  True,  [r"\b\d{1,2}\.\d{2}\.20\d{2}\b"]),
    ],
    "e": [  # Вера, учитель, Екатеринбург (grief)
        ("e-vera",        "PERSON",     "direct", False, [rf"{WB}Вер[аыуе]\w*{WE}", rf"{WB}Орлов[а-я]+{WE}", rf"{WB}Павловн[а-я]+{WE}"]),
        ("e-dmitry",      "PERSON",     "direct", False, [rf"{WB}Дмитри[йяюе]\w*{WE}"]),
        ("e-sonya",       "PERSON",     "direct", False, [rf"{WB}Сон[яюи]\w*{WE}"]),
        ("e-sokolova",    "PERSON",     "direct", False, [rf"{WB}Соколов[а-я]+{WE}"]),
        ("e-larisa",      "PERSON",     "direct", False, [rf"{WB}Ларис[а-я]+\s+Петровн[а-я]+{WE}"]),
        ("e-school",      "ORG",        "quasi",  False, [rf"гимнази[а-я]+\s*(?:№\s*9|номер девять)"]),
        ("e-mirtazapine", "MEDICATION", "quasi",  True,  [rf"{WB}миртазапин\w*{WE}"]),
        ("e-phone",       "PHONE",      "direct", False, [r"\+7-922-555-77-88"]),
        ("e-email",       "EMAIL",      "direct", False, [r"vera\.orlova@example\.ru"]),
        ("e-snils",       "ID",         "direct", False, [r"455-222-111[ -]?33"]),
        ("e-age",         "AGE",        "quasi",  True,  [rf"{WB}тридцать семь{WE}"]),
        ("e-profession",  "PROFESSION", "quasi",  True,  [rf"{WB}учител[а-я]+{WE}"]),
        ("e-ekb",         "LOCATION",   "quasi",  False, [rf"{WB}Екатеринбург\w*{WE}"]),
        ("e-date-%V",     "DATE",       "quasi",  True,  [r"\b\d{1,2}\.\d{2}\.20\d{2}\b"]),
    ],
    "f": [  # Тимур, студент-программист, Казань (ADHD)
        ("f-timur",       "PERSON",     "direct", False, [rf"{WB}Тимур[а-я]*{WE}", rf"{WB}Хайруллин[а-я]*{WE}", rf"{WB}Маратович[а-я]*{WE}"]),
        ("f-timur-latin", "PERSON",     "direct", False, [rf"{WB}Timur{WE}"]),
        ("f-gulnara",     "PERSON",     "direct", False, [rf"{WB}Гульнар[а-я]+{WE}"]),
        ("f-vasilyev",    "PERSON",     "direct", False, [rf"{WB}Васильев[а-я]*{WE}"]),
        ("f-denis",       "PERSON",     "direct", False, [rf"{WB}Денис[а-я]*{WE}"]),
        ("f-kfu",         "ORG",        "quasi",  False, [rf"{WB}КФУ{WE}"]),
        ("f-atomoxetine", "MEDICATION", "quasi",  True,  [rf"{WB}атомоксетин\w*{WE}"]),
        ("f-phone",       "PHONE",      "direct", False, [r"\+7-917-888-99-00"]),
        ("f-email",       "EMAIL",      "direct", False, [r"timur\.kh@example\.com"]),
        ("f-snils",       "ID",         "direct", False, [r"566-333-222[ -]?11"]),
        ("f-age",         "AGE",        "quasi",  True,  [rf"{WB}двадцать три{WE}"]),
        ("f-profession",  "PROFESSION", "quasi",  True,  [rf"{WB}программист\w*{WE}", rf"{WB}студент\w*{WE}"]),
        ("f-kazan",       "LOCATION",   "quasi",  False, [rf"{WB}Казан[а-я]+{WE}"]),
        ("f-date-%V",     "DATE",       "quasi",  True,  [r"\b\d{1,2}\.\d{2}\.20\d{2}\b"]),
    ],
}

# Entity ids added during IAA adjudication (so they can be filtered/counted as v2).
ADJUDICATED = {"a-policy-spelled", "a-phone-spelled", "a-careerlevel",
               "b-ekaterinburg", "b-role", "b-igor-latin"}


def find_spans(text, entities):
    spans = []
    for ent_id, typ, cls, llm, patterns in entities:
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                # %V → per-value entity_id (e.g. distinct session dates are distinct entities)
                eid = ent_id.replace("%V", re.sub(r"\W+", "", m.group().lower())) if "%V" in ent_id else ent_id
                spans.append({
                    "start": m.start(), "end": m.end(),
                    "type": typ, "value": m.group(),
                    "identifier_class": cls, "entity_id": eid,
                    "llm_required": llm,
                    "adjudicated": ent_id in ADJUDICATED,
                })
    # De-duplicate exact-overlapping spans from multiple patterns; keep longest.
    spans.sort(key=lambda s: (s["start"], -(s["end"] - s["start"])))
    kept = []
    for s in spans:
        if kept and s["start"] < kept[-1]["end"] and s["entity_id"] == kept[-1]["entity_id"]:
            continue  # nested/overlapping same-entity match already covered
        kept.append(s)
    # Drop spurious spans fully contained inside a different-entity *structured*
    # span. A case-insensitive name pattern (e.g. "Timur") otherwise matches the
    # local-part of an email ("timur.kh@example.com"), producing a bogus PERSON
    # nested inside the EMAIL. Structured spans (EMAIL/URL/ID) are opaque atomic
    # identifiers — no real sub-entity lives inside them — so anything strictly
    # contained in one (and of a different entity) is dropped. Legitimate
    # same-text-different-context mentions elsewhere in the text are untouched,
    # because containment is checked per character offset, not per surface form.
    STRUCTURED = {"EMAIL", "URL", "ID"}
    structured = [s for s in kept if s["type"] in STRUCTURED]
    cleaned = []
    for s in kept:
        if s["type"] in STRUCTURED:
            cleaned.append(s)
            continue
        contained = any(
            st["entity_id"] != s["entity_id"]
            and st["start"] <= s["start"] and s["end"] <= st["end"]
            and (st["end"] - st["start"]) > (s["end"] - s["start"])
            for st in structured
        )
        if not contained:
            cleaned.append(s)
    return cleaned


# TAB-style protected-person roles per entity (review #2: person_role). The
# *protected person* is the client; others are third parties / institutions.
ROLE = {
    "a-marina": "client", "a-andrey": "partner", "a-petrova": "clinician",
    "a-boss": "third_party", "a-neuromed": "institution", "a-yandex": "institution",
    "b-igor": "client", "b-svetlana": "partner", "b-alexey": "relative",
    "b-pavel": "third_party", "b-kontur": "institution", "b-sber": "institution",
    "b-igor-latin": "client", "b-ekaterinburg": "institution",
    "c-alina": "client", "c-maksim": "partner", "c-zaytseva": "clinician",
    "c-boss": "third_party", "c-alliance": "institution", "c-avito": "institution",
    "d-roman": "client", "d-natalya": "partner", "d-morozov": "clinician",
    "d-artem": "third_party", "d-insight": "institution", "d-sibtrans": "institution",
    "e-vera": "client", "e-dmitry": "partner", "e-sonya": "relative",
    "e-sokolova": "clinician", "e-larisa": "third_party", "e-school": "institution",
    "f-timur": "client", "f-timur-latin": "client", "f-gulnara": "relative",
    "f-vasilyev": "clinician", "f-denis": "third_party", "f-kfu": "institution",
}

# CRITICAL overrides (HARM-TAXONOMY.md): entity_ids to escalate from their
# type-default level to "critical". CRITICAL is reserved for context-sensitive
# cases — an abuser/perpetrator's name, a survivor's location, or identity paired
# with a stigmatised/safety-relevant disclosure — NOT a type default. Add an
# entity_id here only when the synthetic narrative clearly justifies it. The
# current synthetic third parties (a-boss = an employer, b-pavel = a generic
# acquaintance) carry no abuse/safety framing, so this set is intentionally
# empty-but-present: the schema supports escalation without fabricating severity.
CRITICAL_ENTITY_IDS = set()  # e.g. {"x-abuser", "x-shelter-location"}


# Turn markers come in two forms across the corpus (Codex audit #2):
#   client-a inline:  **00:00:04 Т:**
#   client-b split:   **00:00** … Т:   (speaker on/after the bold timestamp)
# Both: a bold timestamp, then the speaker letter (Т=therapist, К=client) before
# the following colon, within a short window.
_TURN_INLINE = re.compile(r"\*\*\d{1,2}:\d{2}(?::\d{2})?\s*([ТК])\s*:\*\*")
_TURN_SPLIT = re.compile(r"\*\*\d{1,2}:\d{2}(?::\d{2})?\s*\*\*\s*([ТК])\s*:")


def _turns(text):
    """List of (char_offset, speaker) for each turn marker, sorted by position."""
    turns = [(m.start(), m.group(1)) for m in _TURN_INLINE.finditer(text)]
    turns += [(m.start(), m.group(1)) for m in _TURN_SPLIT.finditer(text)]
    return sorted(turns)


def enrich(span, text, turns):
    """Attach TAB/review-2 schema fields derived from type + identifier_class +
    role + transcript position. Synthetic-gold heuristics, documented as such."""
    typ, cls, eid = span["type"], span["identifier_class"], span["entity_id"]
    base = "-".join(eid.split("-")[:2])
    # person_role only applies to people/orgs (the ROLE map); None for medication/
    # date/age/profession/phone/email/id, which have no protected-person role.
    span["person_role"] = ROLE.get(base)
    # confidential_status: health attributes are confidential even when not identifying
    span["confidential_status"] = typ in ("MEDICATION",)
    # mask_decision: direct → MASK (remove); quasi → GENERALIZE (abstract, keep utility)
    span["mask_decision"] = "MASK" if cls == "direct" else "GENERALIZE"
    # utility_tag: clinical value of the underlying content for therapy analysis
    span["utility_tag"] = ("clinically_important" if typ == "MEDICATION"
                           else "narrative_context" if typ in ("AGE", "PROFESSION", "DATE", "LOCATION")
                           else "low_utility")
    # speaker_turn_id: index of the most recent turn marker before the span
    tid, spk = -1, None
    for i, (off, s) in enumerate(turns):
        if off <= span["start"]:
            tid, spk = i, s
        else:
            break
    span["speaker_turn_id"] = tid
    span["speaker"] = spk
    # harm: per-span qualitative severity for clinician review. Default = the
    # type's level from the shared HARM_LEVEL map (single source of truth in
    # score_bench.py); escalate to "critical" only for declared context-sensitive
    # entities (CRITICAL_ENTITY_IDS). typ is already canonical here.
    span["harm"] = ("critical" if eid in CRITICAL_ENTITY_IDS
                    else HARM_LEVEL.get(typ, "medium"))
    return span


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(RU, "pii-eval-ru.jsonl"))
    ap.add_argument("--review", action="store_true",
                    help="dump every matched span with context for verification")
    args = ap.parse_args()

    rows = []
    for client, entities in CLIENTS.items():
        for sess in range(1, 6):
            path = os.path.join(RU, f"client-{client}", f"session-0{sess}.md")
            text = open(path, encoding="utf-8").read()
            turns = _turns(text)
            spans = [enrich(s, text, turns) for s in find_spans(text, entities)]
            rows.append({
                "doc_id": f"ru-{client}-s0{sess}", "lang": "ru",
                "client": client, "session": sess,
                # Person-disjoint split: each client is a distinct synthetic person,
                # so splitting by client prevents profile/template leakage across
                # dev/test (per the research P0 recommendation). client-a = dev
                # (tuning), client-b = held-out test.
                "split": "dev" if client in ("a", "c", "e") else "test",
                "text": text, "spans": spans,
            })

    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    total = sum(len(r["spans"]) for r in rows)
    by_type = {}
    by_class = {"direct": 0, "quasi": 0}
    llm_req = 0
    for r in rows:
        for s in r["spans"]:
            by_type[s["type"]] = by_type.get(s["type"], 0) + 1
            by_class[s["identifier_class"]] += 1
            llm_req += int(s["llm_required"])
    print(f"[build-ru] wrote {len(rows)} sessions, {total} gold mention-spans -> {os.path.relpath(args.out)}")
    print(f"[build-ru] by type: {dict(sorted(by_type.items()))}")
    print(f"[build-ru] by class: {by_class}  | llm_required mentions: {llm_req}")

    if args.review:
        print("\n=== REVIEW: every matched span with ±25 char context ===")
        for r in rows:
            for s in r["spans"]:
                a, b = max(0, s["start"] - 25), min(len(r["text"]), s["end"] + 25)
                ctx = r["text"][a:b].replace("\n", " ")
                print(f"{r['doc_id']} [{s['type']:10} {s['identifier_class']:6} {s['entity_id']:13}] "
                      f"{s['value']!r:30} …{ctx}…")


if __name__ == "__main__":
    main()
