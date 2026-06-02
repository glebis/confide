#!/usr/bin/env python3
"""
Build the English PII eval dataset(s) for the OpenAI Privacy Filter eval.

Outputs two JSONL files under ../sessions-en/:
  1. pii-eval.jsonl        -- PRIMARY. Curated, synthetic, therapy-style snippets.
                              Authored by hand for the masterclass demo. Every entity
                              is gold-labeled against the model's 8 categories.
  2. pii-eval-ai4privacy.jsonl -- SECONDARY (optional, requires `datasets` + network).
                              A real slice of ai4privacy/pii-masking-300k (English),
                              label-mapped to the model's 8 categories. Generic
                              (non-therapy) content; kept as a real-data sanity check.

Each line in either file:
  {"text": "...", "spans": [{"start": int, "end": int, "type": "<one of 8>", "value": "..."}],
   "source": "curated-synthetic" | "ai4privacy-300k"}

The 8 model labels (openai/privacy-filter):
  private_person, private_address, private_email, private_phone,
  private_url, private_date, account_number, secret
"""
import json
import os

from confide_eval import paths

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.fspath(paths.SESSIONS_EN)
os.makedirs(OUT_DIR, exist_ok=True)

MODEL_LABELS = {
    "private_person", "private_address", "private_email", "private_phone",
    "private_url", "private_date", "account_number", "secret",
}


# ---------------------------------------------------------------------------
# PRIMARY: curated synthetic therapy-style snippets.
#
# We provide each snippet as text + a list of (value, type) entities.
# Spans are computed by locating each value in the text (first occurrence,
# advancing a cursor so repeated values resolve left-to-right). This keeps the
# source readable and the gold spans exact.
# ---------------------------------------------------------------------------
CURATED = [
    ("My therapist suggested I write to my mother, Margaret Halloran, before our next session.",
        [("Margaret Halloran", "private_person")]),
    ("I keep replaying the argument with David from last Tuesday and it won't let me sleep.",
        [("David", "private_person"), ("last Tuesday", "private_date")]),
    ("Can you send the intake form to elena.k.patient@gmail.com? I check that one daily.",
        [("elena.k.patient@gmail.com", "private_email")]),
    ("After the divorce I moved to 14 Birch Lane, Asheville, and the silence there is unbearable.",
        [("14 Birch Lane, Asheville", "private_address")]),
    ("If I have a panic attack at night I'm supposed to call my sister at 0151 496 0382.",
        [("0151 496 0382", "private_phone")]),
    ("On March 3rd, 2024 my father passed, and I still set a plate for him at dinner.",
        [("March 3rd, 2024", "private_date"), ("him", "private_person")]),  # 'him' is NOT a name; see note below
    ("I found his old emails by logging in with the password Sparrow1987 and I shouldn't have.",
        [("Sparrow1987", "secret")]),
    ("Dr. Okonkwo prescribed sertraline but I haven't filled it; the pharmacy is on Carlisle Road.",
        [("Dr. Okonkwo", "private_person"), ("Carlisle Road", "private_address")]),
    ("I read the support group posts at https://reddit.com/r/anxietyhelp every morning before work.",
        [("https://reddit.com/r/anxietyhelp", "private_url")]),
    ("My partner Yuki keeps the joint savings, account number 4471 9920 8835, and I feel powerless.",
        [("Yuki", "private_person"), ("4471 9920 8835", "account_number")]),
    ("I told my boss, Mr. Achterberg, that I needed leave, and he just stared at me.",
        [("Mr. Achterberg", "private_person")]),
    ("The anniversary is coming up on 12 December and I've already cancelled my plans.",
        [("12 December", "private_date")]),
    ("She texts me from +49 30 1234 5678 at 2am and I can't bring myself to block her.",
        [("+49 30 1234 5678", "private_phone")]),
    ("I emailed support@crisisline.org but no one wrote back, which made the spiral worse.",
        [("support@crisisline.org", "private_email")]),
    ("My old flat at 7B Kingsway Court, Leeds LS1 4DT, is where most of the flashbacks happen.",
        [("7B Kingsway Court, Leeds LS1 4DT", "private_address")]),
    ("I write everything in a journal app and the recovery key is 9F2A-77QX-LMP4 if I lose access.",
        [("9F2A-77QX-LMP4", "secret")]),
    ("Carla and her brother Tomas both said I overreacted, and now I doubt my own memory.",
        [("Carla", "private_person"), ("Tomas", "private_person")]),
    ("My GP, Dr. Saoirse Byrne, referred me on the 5th of January for an assessment.",
        [("Dr. Saoirse Byrne", "private_person"), ("5th of January", "private_date")]),
    ("I keep checking his profile at https://instagram.com/marcus.lindqvist even though it hurts.",
        [("https://instagram.com/marcus.lindqvist", "private_url")]),
    ("The clinic billed the wrong card, ending 8842, and the call about it triggered a meltdown.",
        [("8842", "account_number")]),
    ("My mum, Pauline, calls every Sunday and I dread it; you can reach her on 07700 900145.",
        [("Pauline", "private_person"), ("07700 900145", "private_phone")]),
    ("I moved back to 22 Rue des Lilas, Lyon, to care for my grandfather and lost my own life.",
        [("22 Rue des Lilas, Lyon", "private_address")]),
    ("He proposed on June 14 2019 and broke it off two years later by email to my old address.",
        [("June 14 2019", "private_date")]),
    ("Forward the assessment to dr.nakamura@northbridge-clinic.co.uk and copy my partner please.",
        [("dr.nakamura@northbridge-clinic.co.uk", "private_email")]),
    ("My ex still knows my banking PIN, 6471, and I keep meaning to change it but freeze.",
        [("6471", "secret")]),
    ("The session with Priya Venkataraman last Thursday was the first time I cried openly.",
        [("Priya Venkataraman", "private_person"), ("last Thursday", "private_date")]),
    ("I gave Liam my Netflix login, viewer4@proton.me, password Moonlit_42, and now I regret it.",
        [("Liam", "private_person"), ("viewer4@proton.me", "private_email"), ("Moonlit_42", "secret")]),
    ("Every 19th of the month I transfer rent to my landlord, Mrs. Okafor, from account 0098 5521.",
        [("19th of the month", "private_date"), ("Mrs. Okafor", "private_person"), ("0098 5521", "account_number")]),
    ("I drive past 88 Hillcrest Avenue, Dublin 4, where we used to live, and my chest tightens.",
        [("88 Hillcrest Avenue, Dublin 4", "private_address")]),
    ("My brother Sven shared the clinic link https://mindspace-therapy.de/booking and I froze.",
        [("Sven", "private_person"), ("https://mindspace-therapy.de/booking", "private_url")]),
    ("On 02/11/2023 I checked myself in; the duty nurse, Aaliyah, was the only one who was kind.",
        [("02/11/2023", "private_date"), ("Aaliyah", "private_person")]),
    ("If you can't reach me, my emergency contact is Theo on 020 7946 0991.",
        [("Theo", "private_person"), ("020 7946 0991", "private_phone")]),
]

# NOTE on the "him" entity above: third-person pronouns are NOT PII and the model
# is not expected to tag them. We drop any entity whose value is a bare pronoun so
# we never penalize the model for correctly ignoring it.
_PRONOUNS = {"him", "her", "them", "he", "she", "they"}


def compute_spans(text, entities):
    spans = []
    cursor = 0
    for value, etype in entities:
        if value.lower() in _PRONOUNS:
            continue
        assert etype in MODEL_LABELS, f"bad label {etype}"
        idx = text.find(value, cursor)
        if idx == -1:
            # fall back to global search (value may legitimately precede cursor)
            idx = text.find(value)
        assert idx != -1, f"value {value!r} not found in {text!r}"
        spans.append({"start": idx, "end": idx + len(value), "type": etype, "value": value})
        cursor = idx + len(value)
    # sort by start for determinism
    spans.sort(key=lambda s: s["start"])
    return spans


def build_curated(path):
    n_ent = 0
    with open(path, "w") as f:
        for text, entities in CURATED:
            spans = compute_spans(text, entities)
            n_ent += len(spans)
            f.write(json.dumps({"text": text, "spans": spans,
                                "source": "curated-synthetic"}, ensure_ascii=False) + "\n")
    print(f"[curated]   {len(CURATED)} snippets, {n_ent} entities -> {path}")


# ---------------------------------------------------------------------------
# SECONDARY: real ai4privacy slice, label-mapped to the 8 model categories.
# ai4privacy label -> model label. Unmapped labels are dropped (the model has
# no category for them, so they would only add noise).
# ---------------------------------------------------------------------------
AI4_MAP = {
    "GIVENNAME1": "private_person", "GIVENNAME2": "private_person",
    "LASTNAME1": "private_person", "LASTNAME2": "private_person",
    "LASTNAME3": "private_person", "TITLE": None,  # honorific alone is weak PII; drop
    "EMAIL": "private_email",
    "TEL": "private_phone",
    "DATE": "private_date", "BOD": "private_date",  # birth-of-date
    "TIME": None,  # bare time-of-day is not in the model's date category reliably; drop
    "STREET": "private_address", "BUILDING": "private_address",
    "SECADDRESS": "private_address", "CITY": "private_address",
    "STATE": "private_address", "COUNTRY": "private_address",
    "POSTCODE": "private_address", "GEOCOORD": "private_address",
    "USERNAME": None,  # model has no username category; drop
    "IP": None, "DRIVERLICENSE": "account_number", "IDCARD": "account_number",
    "PASSPORT": "account_number", "SOCIALNUMBER": "account_number",
    "PASS": "secret",  # password
    "SEX": None,
}


def build_ai4privacy(path, n=15, seed=13):
    try:
        from datasets import load_dataset
    except Exception as e:  # pragma: no cover
        print(f"[ai4privacy] SKIPPED (datasets not importable: {e})")
        return False
    import itertools
    import random
    rng = random.Random(seed)
    try:
        ds = load_dataset("ai4privacy/pii-masking-300k", split="validation", streaming=True)
        # take a buffer of English rows of reasonable length, then sample
        buf = []
        for r in itertools.islice(ds, 1500):
            if r.get("language") != "English":
                continue
            txt = r["source_text"]
            if not (40 <= len(txt) <= 320):
                continue
            buf.append(r)
            if len(buf) >= 200:
                break
    except Exception as e:  # pragma: no cover
        print(f"[ai4privacy] SKIPPED (load failed: {e})")
        return False
    rng.shuffle(buf)
    chosen, n_ent = [], 0
    for r in buf:
        spans = []
        for m in r["privacy_mask"]:
            mapped = AI4_MAP.get(m["label"])
            if mapped is None:
                continue
            spans.append({"start": m["start"], "end": m["end"],
                          "type": mapped, "value": m["value"]})
        if not spans:
            continue
        spans.sort(key=lambda s: s["start"])
        chosen.append({"text": r["source_text"], "spans": spans,
                       "source": "ai4privacy-300k"})
        n_ent += len(spans)
        if len(chosen) >= n:
            break
    with open(path, "w") as f:
        for row in chosen:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[ai4privacy] {len(chosen)} snippets, {n_ent} entities -> {path}")
    return True


if __name__ == "__main__":
    build_curated(os.path.join(OUT_DIR, "pii-eval.jsonl"))
    build_ai4privacy(os.path.join(OUT_DIR, "pii-eval-ai4privacy.jsonl"))
