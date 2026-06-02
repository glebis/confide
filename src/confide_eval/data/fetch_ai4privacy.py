#!/usr/bin/env python3
"""Fetch-on-demand reconstruction of the EN-real (ai4privacy) source text.

WHY THIS EXISTS
---------------
CONFIDE-Bench's EN-real slice is a 15-row sample of the public Hugging Face
dataset ``ai4privacy/pii-masking-300k``. That dataset's license restricts
*redistribution* of its source text, so this repo does NOT commit the text.
The committed gold (``data/sessions-en/pii-eval-ai4privacy.jsonl``) ships only
span offsets, the gold ``value`` strings, ``source``, ``text_len`` and a
``text_sha256`` of each original document.

This script re-downloads ai4privacy from Hugging Face *under that dataset's own
license*, locates the 15 source rows our gold was built from, verifies each
reconstructed document against its recorded sha256, and writes a LOCAL,
text-bearing runnable gold:

    data/sessions-en/pii-eval-ai4privacy.local.jsonl   (gitignored)

with records ``{doc_id, text, spans}``. score_bench / run_detectors prefer this
local file automatically when it exists (see paths.en_real_gold()).

USAGE
-----
    pip install datasets            # one-time, if not already installed
    python -m confide_eval.data.fetch_ai4privacy

If ``datasets`` is not installed or the network is unavailable, the script
prints a clear instruction and exits non-zero WITHOUT touching the repo.

MATCHING APPROACH
-----------------
The committed gold stores, per doc, ``text_len`` and ``text_sha256`` of the
exact (possibly truncated) document the spans were annotated against. We scan
the ai4privacy English rows and, for each, hash the first ``text_len``
characters of its source text; a row matches a gold doc iff that sha256 equals
the recorded ``text_sha256``. This is robust: it never trusts a brittle row
index and fails loudly if any of the 15 documents cannot be reconstructed
byte-for-byte.
"""
import hashlib
import json
import os
import sys

from confide_eval import paths

HF_DATASET = "ai4privacy/pii-masking-300k"
# Candidate field names that hold the document text across ai4privacy revisions.
_TEXT_FIELDS = ("source_text", "unmasked_text", "text", "full_text")
# Candidate splits to scan (English rows live in the standard splits).
_SPLITS = ("train", "validation", "test")


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_stripped_gold():
    rows = []
    with open(os.fspath(paths.EN_REAL_STRIPPED), encoding="utf-8") as f:
        for i, line in enumerate(f):
            r = json.loads(line)
            r.setdefault("doc_id", f"en-real-{i:03d}")
            if "text_sha256" not in r or "text_len" not in r:
                sys.exit(
                    "[fetch] committed gold lacks text_sha256/text_len — cannot "
                    "reconstruct. Is this the stripped EN-real gold?"
                )
            rows.append(r)
    return rows


def _doc_text(row):
    for fld in _TEXT_FIELDS:
        if fld in row and isinstance(row[fld], str) and row[fld]:
            return row[fld]
    return None


def fetch():
    try:
        from datasets import load_dataset
    except ImportError:
        print(
            "[fetch] the `datasets` library is required to fetch ai4privacy.\n"
            "        Install it with:  pip install datasets\n"
            "        Then re-run:      python -m confide_eval.data.fetch_ai4privacy"
        )
        return 1

    gold = _load_stripped_gold()
    # Index gold docs by their recorded sha256 so a single pass over the HF rows
    # can match all 15 at once.
    want = {}  # text_sha256 -> gold record
    for r in gold:
        want[r["text_sha256"]] = r
    found = {}  # text_sha256 -> reconstructed text

    print(f"[fetch] loading {HF_DATASET} from Hugging Face "
          f"(under ai4privacy's license; not redistributed by this repo) ...")
    try:
        ds = load_dataset(HF_DATASET)
    except Exception as e:  # network / auth / gated
        print(f"[fetch] could not download {HF_DATASET}: {e}\n"
              f"        Check your network and `huggingface-cli login` if gated.")
        return 1

    splits = [s for s in _SPLITS if s in ds] or list(ds)
    for split in splits:
        for row in ds[split]:
            if len(found) == len(want):
                break
            text = _doc_text(row)
            if not text:
                continue
            for r in gold:
                h = r["text_sha256"]
                if h in found:
                    continue
                cand = text[: r["text_len"]]
                if len(cand) == r["text_len"] and _sha256(cand) == h:
                    found[h] = cand
        if len(found) == len(want):
            break

    missing = [r["doc_id"] for r in gold if r["text_sha256"] not in found]
    if missing:
        print(f"[fetch] FAILED to reconstruct {len(missing)} / {len(gold)} docs "
              f"(sha256 not found in {HF_DATASET}): {', '.join(missing)}\n"
              f"        The dataset revision may have changed. Aborting; the repo "
              f"is untouched.")
        return 1

    # Write the runnable, text-bearing local gold (doc_id, text, spans).
    out_path = paths.EN_REAL_LOCAL
    tmp = f"{os.fspath(out_path)}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in gold:
            text = found[r["text_sha256"]]
            # Defence-in-depth: re-verify sha256 + length before writing.
            assert _sha256(text) == r["text_sha256"], r["doc_id"]
            assert len(text) == r["text_len"], r["doc_id"]
            f.write(json.dumps(
                {"doc_id": r["doc_id"], "text": text, "spans": r["spans"]},
                ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, os.fspath(out_path))
    print(f"[fetch] OK — reconstructed + sha256-verified {len(gold)} docs -> "
          f"{os.path.relpath(os.fspath(out_path))}\n"
          f"        (gitignored; EN-real is now runnable: `make rescore` / detectors)")
    return 0


def main():
    sys.exit(fetch())


if __name__ == "__main__":
    main()
