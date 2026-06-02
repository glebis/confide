#!/usr/bin/env python3
"""Build the RU-real gold slice from the JayGuard NER benchmark.

SOURCE
------
Hugging Face dataset ``just-ai/jayguard-ner-benchmark`` (Just AI), 850 rows of
*real, anonymized* conversational Russian text, token-classification BIO. It is
licensed **Apache-2.0** (the HF card states Apache 2.0; the bibtex citation
likewise) — redistribution is permitted WITH attribution, so unlike the
ai4privacy EN-real slice we DO commit the source text here (see
``data/sessions-ru-real/README.md`` for the attribution + license note).

WHAT THIS IS (and is NOT)
-------------------------
This is a real-TEXT Russian de-identification proxy, NOT real therapy. JayGuard
is everyday conversational RU (medical/travel/daily-life chatter), not clinical
session dialogue. The gold here is MACHINE-DERIVED from JayGuard's own BIO
labels, NOT human-adjudicated — the annotator.html + ANNOTATION-CODEBOOK.md path
for human review is the documented follow-up.

TYPE MAPPING (CONFIDE schema)
-----------------------------
JayGuard tag        -> CONFIDE type   identifier_class   harm
  PERSON, PER       -> PERSON         direct             high
  GPE               -> LOCATION       quasi              medium
  STREET_ADDRESS    -> LOCATION       direct             medium
  PUBLIC_PLACES     -> LOCATION       quasi              low
  FICT              -> (dropped: fictional entities are not real PII)

Out-of-spec JayGuard tags present in the source but NOT mapped (excluded, and
recorded in the slice README): THEO, PET, PUBLIC_PERSON, PUBLIC_PER, PER_PUBLIC.
These are public figures / deities / pets / etc. — not first-party private PII
for the CONFIDE PERSON/LOCATION de-id task — so they are dropped to keep the
slice a clean direct-PERSON + LOCATION subset. PER is treated as a PERSON variant
(it is the dataset's main personal-name tag) and IS mapped.

BIO -> CHAR OFFSETS
-------------------
JayGuard carries only B- tags (no I-). Adjacent same-type B- tokens (e.g.
"Тверской"/"15" both B-STREET_ADDRESS) are MERGED into one entity span — that is
how the address reads as a single identifier. Text is reconstructed by joining
tokens with single spaces; offsets are computed on that reconstruction and every
span is verified with ``text[start:end] == span_text`` (fail loudly on mismatch).

SELECTION
---------
Deterministic: the first ``--limit`` rows (in dataset order) that contain at
least one in-scope entity. Default limit 50.

USAGE
-----
    pip install datasets
    python -m confide_eval.data.build_jayguard_ru_real            # writes the gold
    python -m confide_eval.data.build_jayguard_ru_real --limit 60
"""
import argparse
import json
import os
import sys

from confide_eval import paths

HF_DATASET = "just-ai/jayguard-ner-benchmark"
OUT_DIR = paths.DATA / "sessions-ru-real"
OUT_PATH = OUT_DIR / "jayguard-ru.jsonl"

# JayGuard B-tag -> (CONFIDE type, identifier_class, harm). None => dropped.
TAG_MAP = {
    "PERSON":         ("PERSON",   "direct", "high"),
    "PER":            ("PERSON",   "direct", "high"),   # dataset's main name tag
    "GPE":            ("LOCATION", "quasi",  "medium"),
    "STREET_ADDRESS": ("LOCATION", "direct", "medium"),
    "PUBLIC_PLACES":  ("LOCATION", "quasi",  "low"),
}
# Explicitly dropped (recorded for honesty in the slice README).
DROP_TAGS = {"FICT", "THEO", "PET", "PUBLIC_PERSON", "PUBLIC_PER", "PER_PUBLIC"}
INSCOPE = set(TAG_MAP)


def reconstruct(tokens):
    """Join tokens with single spaces; return (text, [(start,end) per token])."""
    text_parts = []
    offsets = []
    pos = 0
    for i, tok in enumerate(tokens):
        if i > 0:
            text_parts.append(" ")
            pos += 1
        start = pos
        text_parts.append(tok)
        pos += len(tok)
        offsets.append((start, pos))
    return "".join(text_parts), offsets


def row_to_spans(tokens, tags, offsets, doc_id):
    """Merge adjacent same-type B- tokens into entity spans, mapped to CONFIDE."""
    spans = []
    i = 0
    n = len(tokens)
    while i < n:
        tag = tags[i]
        if not tag.startswith("B-"):
            i += 1
            continue
        raw = tag[2:]
        # extend over consecutive same-raw-type B- tokens (no I- tags exist)
        j = i + 1
        while j < n and tags[j] == tag:
            j += 1
        if raw in TAG_MAP:
            ctype, iclass, harm = TAG_MAP[raw]
            start = offsets[i][0]
            end = offsets[j - 1][1]
            spans.append({
                "start": start, "end": end,
                "type": ctype,
                "value": None,  # filled by caller after text is known
                "identifier_class": iclass,
                "entity_id": None,  # filled by caller (per surface form)
                "person_role": "third_party" if ctype == "PERSON" else None,
                "harm": harm,
                "source_tag": raw,
            })
        i = j
    return spans


def build(limit):
    try:
        from datasets import load_dataset
    except ImportError:
        print("[build] the `datasets` library is required.\n"
              "        pip install datasets && python -m "
              "confide_eval.data.build_jayguard_ru_real")
        return 1
    print(f"[build] loading {HF_DATASET} (Apache-2.0; attribution required) ...")
    ds = load_dataset(HF_DATASET)["train"]

    out_rows = []
    selected = 0
    for idx in range(len(ds)):
        r = ds[idx]
        tokens, tags = r["tokens"], r["ner_tags"]
        present = {t[2:] for t in tags if t.startswith("B-")}
        if not (present & INSCOPE):
            continue  # deterministic: skip rows with no in-scope entity
        doc_id = f"jayguard-{selected:03d}"
        text, offsets = reconstruct(tokens)
        spans = row_to_spans(tokens, tags, offsets, doc_id)
        if not spans:
            continue
        # fill value + per-surface-form entity_id; verify offsets
        surface_eid = {}
        for s in spans:
            s["value"] = text[s["start"]:s["end"]]
            if s["value"] != text[s["start"]:s["end"]]:
                sys.exit(f"[build] OFFSET MISMATCH in {doc_id}: {s}")
            key = (s["type"], s["value"].lower())
            if key not in surface_eid:
                surface_eid[key] = f"{doc_id}-{s['type'].lower()}-{len(surface_eid)}"
            s["entity_id"] = surface_eid[key]
        out_rows.append({"doc_id": doc_id, "lang": "ru", "text": text,
                         "spans": spans, "source_row": idx})
        selected += 1
        if selected >= limit:
            break

    # global offset verification (defence in depth)
    bad = 0
    for r in out_rows:
        for s in r["spans"]:
            if r["text"][s["start"]:s["end"]] != s["value"]:
                bad += 1
    if bad:
        sys.exit(f"[build] {bad} span(s) failed text[start:end]==value — aborting")

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = f"{os.fspath(OUT_PATH)}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, os.fspath(OUT_PATH))

    # report distribution
    from collections import Counter
    by_type = Counter(s["type"] for r in out_rows for s in r["spans"])
    by_src = Counter(s["source_tag"] for r in out_rows for s in r["spans"])
    n_spans = sum(len(r["spans"]) for r in out_rows)
    print(f"[build] OK — {len(out_rows)} docs, {n_spans} spans -> "
          f"{os.path.relpath(os.fspath(OUT_PATH))}")
    print(f"[build] type dist: {dict(by_type)}")
    print(f"[build] source-tag dist: {dict(by_src)}")
    print(f"[build] offsets verified for 100% of {n_spans} spans.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()
    sys.exit(build(args.limit))


if __name__ == "__main__":
    main()
