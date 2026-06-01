# English Anonymization Eval — OpenAI Privacy Filter

A small, reproducible evaluation of the **OpenAI Privacy Filter**
(`openai/privacy-filter` on HuggingFace) on **English** therapy-style text.
Built for a masterclass demo. Written so a non-ML clinical audience can read it.

> **What is being measured?** When we run an automatic de-identification tool
> over a session transcript, how many of the real pieces of personal
> information (PII) does it actually catch — and how many does it miss?
> A *missed* item is leaked PII.

---

## TL;DR — what actually ran

This eval **was executed** on a CPU laptop (Apple Silicon, 26 GB RAM).
The numbers in `RESULTS.md` are our own measurement, not vendor marketing.

| Dataset | Snippets | Gold PII | Recall | Precision | F1 | **F2 (headline)** |
|---|--:|--:|--:|--:|--:|--:|
| `pii-eval.jsonl` (curated therapy-style) | 32 | 46 | **0.76** | 0.92 | 0.83 | **0.79** |
| `pii-eval-ai4privacy.jsonl` (real slice, in-distribution) | 15 | 80 | **0.55** | 0.85 | 0.67 | **0.59** |

(Relaxed/overlap mode. Strict exact-span numbers are in `RESULTS.md`.)

Performance on CPU: model loads in ~8 s from local cache (first run downloads
~2.8 GB of weights, ~4-5 min), inference ~2-3 s per snippet. Peak RAM ~6-7 GB.

The vendor's own model card claims **F1 96% / P 94% / R 98%** on the full
PII-Masking-300k benchmark. That is their in-distribution number on 300k generic
examples — see the "Vendor claim" section of `RESULTS.md` for why our harder,
tiny, therapy-flavoured set scores lower. We never mix their number into ours.

---

## Why recall is the safety-critical metric

In de-identification the two ways to be wrong are **not** symmetric:

- A **false negative (missed entity)** means real PII — a name, an address, a
  phone number — survives into the "anonymized" output. That is a **privacy
  breach**. In a clinical setting it can be a reportable data incident.
- A **false positive (over-redaction)** means the tool blacked out a word that
  wasn't actually PII. The cost is only **readability** — the transcript is a
  little harder to read. Nobody's privacy is harmed.

Because a miss is far more expensive than an over-redaction, de-identification
is evaluated with **recall weighted above precision**:

- **Recall** = of all the real PII, what fraction did we catch?
- **Precision** = of everything we flagged, what fraction was really PII?
- **F2** = a single score that blends both but weights **recall 2× over
  precision**. (F1 weights them equally; F2 is the recall-favouring sibling.)

We report **F2 as the headline**, following:

- **Microsoft Presidio-research**, whose evaluation framework treats recall as
  the primary de-id metric and scores predictions as
  *correct / partial / missed / spurious* at the entity level.
- The **i2b2 / n2c2 clinical de-identification** shared-task tradition, where
  recall (sensitivity) is the headline because a single leaked identifier can
  re-identify a patient.

---

## How scoring works (entity-level, two modes)

We compare the tool's predicted PII spans against hand-labeled **gold** spans,
one entity at a time, following the Presidio-research method. Each prediction is:

- **correct** — same type, and the span matches gold,
- **wrong-type** — overlaps a gold span but labels it the wrong category
  (penalized as both a false positive and a false negative),
- **spurious** — flagged something with no gold PII there (false positive),
- and any gold entity with no matching prediction is **missed** (false negative).

Two strictness settings:

- **Strict** — a prediction only counts if its start *and* end exactly match
  gold. Punishes boundary disagreements (e.g. including a trailing comma).
- **Relaxed** — a prediction counts if it *overlaps* the gold span by at least
  one character. This answers the real question: *"did we catch the PII at all?"*
  This is our **headline mode**.

For this model the two modes are close (curated: strict F2 0.74 vs relaxed 0.79),
which means once trailing punctuation is trimmed the boundaries are mostly exact.

### A note on honest post-processing

`run_opf.py` applies two standard, model-agnostic cleanups to the raw pipeline
output before scoring: it (1) trims leading/trailing whitespace and edge
punctuation from each span (punctuation is never PII), and (2) merges adjacent
same-type subword fragments (e.g. `Margaret Hall` + `oran` → `Margaret Halloran`).
These are normal de-id deployment steps, **not** score-gaming — they change span
boundaries, never which entities the model detected. Without them, strict F2 was
artificially 0.00 purely from token-boundary artifacts.

---

## Reproduce it

```bash
cd eval
pip install -r requirements.txt          # transformers, torch (datasets optional)

python build_dataset.py                  # writes ../sessions-en/pii-eval.jsonl
                                         # (+ real ai4privacy slice if datasets installed)

python run_opf.py                        # downloads ~2.8 GB weights, runs on CPU,
                                         # writes predictions.jsonl + run_meta.json

python score.py                          # writes RESULTS.md + results.json

# Optional: the real, in-distribution ai4privacy slice
python run_opf.py --input ../sessions-en/pii-eval-ai4privacy.jsonl \
                  --output predictions-ai4privacy.jsonl
python score.py   --gold  ../sessions-en/pii-eval-ai4privacy.jsonl \
                  --pred  predictions-ai4privacy.jsonl --out-prefix ai4privacy-
```

The model loads directly via the transformers pipeline (Route B) — **no repo
install, no `opf` CLI needed**:

```python
from transformers import pipeline
nlp = pipeline("token-classification", "openai/privacy-filter",
               aggregation_strategy="first")
```

> Requires **transformers ≥ 5.x** — the `openai_privacy_filter` model type is
> not registered in transformers 4.x. `pip install -U transformers` fixes it.

---

## The dataset

The model recognizes **8 PII categories**:
`private_person`, `private_address`, `private_email`, `private_phone`,
`private_url`, `private_date`, `account_number`, `secret`.

- **`../sessions-en/pii-eval.jsonl`** — PRIMARY. 32 short, **curated synthetic**
  therapy-style snippets (1–2 sentences each), hand-labeled with 46 gold
  entities across all 8 categories. Synthetic so it contains no real patient
  data; therapy-flavoured so the demo lands with a clinical audience. Includes
  deliberately hard cases (relative dates like *"last Tuesday"*, short numeric
  PINs / account tails) — which is where the model's recall actually drops.
- **`../sessions-en/pii-eval-ai4privacy.jsonl`** — SECONDARY. A **real** 15-row
  slice of `ai4privacy/pii-masking-300k` (English `validation` split), with its
  native labels mapped down to the model's 8 categories. Generic
  (non-therapy) content; kept as an in-distribution sanity check.

Each line:
```json
{"text": "...", "spans": [{"start": 45, "end": 62, "type": "private_person", "value": "Margaret Halloran"}], "source": "curated-synthetic"}
```

---

## For RUSSIAN transcripts — use Presidio + spaCy instead

The OpenAI Privacy Filter is **English-first and weak on Russian**, which is the
whole reason this eval is English-only. For Russian session transcripts we use
**Microsoft Presidio** with a Russian spaCy NER model:

```bash
pip install presidio-analyzer presidio-anonymizer spacy
python -m spacy download ru_core_news_lg
```

Presidio combines `ru_core_news_lg` NER (names, locations, orgs) with regex/
checksum recognizers (phones, emails, IBANs, etc.) and is configurable per
language — a better fit for Russian than the English-tuned filter. The same
`score.py` methodology (entity-level, recall-weighted F2, strict + relaxed)
applies; only the detector and the language model change.
