# RU-real slice — JayGuard (real-TEXT Russian de-identification proxy)

`jayguard-ru.jsonl` — **60 documents, 77 gold PII spans** of *real, anonymized*
conversational Russian text, mapped into the CONFIDE gold schema. This is
CONFIDE's first **real-text** Russian de-id slice; the rest of the RU corpus is
synthetic.

## Honest framing — read this first

- **Real TEXT, not real therapy.** JayGuard is everyday conversational Russian
  (medical/travel/daily-life chatter), *not* clinical session dialogue. Treat it
  as a **real-text RU proxy** for the de-id detectors, not as evidence about
  therapy transcripts specifically.
- **Machine-derived gold, NOT human-adjudicated.** The spans here are converted
  mechanically from JayGuard's own BIO token labels. They have **not** been
  re-annotated or adjudicated against the CONFIDE annotation codebook. The
  `annotator.html` + `docs/ANNOTATION-CODEBOOK.md` human-review path is the
  documented follow-up.
- **PERSON / LOCATION only.** JayGuard labels personal names and places. It does
  **not** label phone / email / financial / medication / date entities, so this
  slice scores recall on PERSON and LOCATION only. Detector false positives on
  *other* types (DATE, PROFESSION, MEDICATION, …) are expected and depress
  precision but not the recall-vs-truth headline.

## Source & license

- **Source:** Hugging Face dataset
  [`just-ai/jayguard-ner-benchmark`](https://huggingface.co/datasets/just-ai/jayguard-ner-benchmark)
  (Just AI), 850 rows, token-classification BIO.
- **License:** **Apache-2.0** (per the HF dataset card and its citation).
  Apache-2.0 permits redistribution **with attribution**, so — unlike the
  ai4privacy EN-real slice, which is fetch-gated — the source text **is**
  committed here.
- **Attribution:** *Jay Guard NER Benchmark*, Just AI, 2025. Hugging Face Datasets.
  `https://huggingface.co/datasets/just-ai/jayguard-ner-benchmark`

## How this slice was built

Deterministic, reproducible via
`python -m confide_eval.data.build_jayguard_ru_real --limit 60`:

1. Scan JayGuard rows **in dataset order**; keep the first 60 that contain at
   least one in-scope entity (`PERSON`/`PER`/`GPE`/`STREET_ADDRESS`/`PUBLIC_PLACES`).
   Selected source rows span indices 0–64.
2. Reconstruct each document's text by joining tokens with single spaces, compute
   character offsets on that reconstruction, and verify `text[start:end] == value`
   for **every** span (the build fails loudly on any mismatch — 0 mismatches here).
3. JayGuard has only `B-` tags (no `I-`); adjacent same-type `B-` tokens (e.g.
   `Тверской` `15`, both `B-STREET_ADDRESS`) are **merged** into one entity span.
4. `entity_id` is assigned per surface form (case-insensitive) within a document.

### Type mapping (JayGuard → CONFIDE)

| JayGuard tag     | CONFIDE type | identifier_class | harm   |
|------------------|--------------|------------------|--------|
| `PERSON`, `PER`  | PERSON       | direct           | high   |
| `GPE`            | LOCATION     | quasi            | medium |
| `STREET_ADDRESS` | LOCATION     | direct           | medium |
| `PUBLIC_PLACES`  | LOCATION     | quasi            | low    |
| `FICT`           | — *(dropped: fictional entities are not real PII)* |

**Dropped tags** (not first-party private PII for the CONFIDE PERSON/LOCATION
task; excluded for honesty): `FICT`, `THEO`, `PET`, `PUBLIC_PERSON`,
`PUBLIC_PER`, `PER_PUBLIC`. `PER` is the dataset's main personal-name tag and is
mapped to PERSON.

## Distribution of this slice

- Types: **LOCATION 65, PERSON 12** (77 spans, 60 docs).
- Source tags: STREET_ADDRESS 55, PERSON 12, GPE 9, PUBLIC_PLACES 1.

See `docs/BENCHMARK.md` § "Real-text RU slice (JayGuard)" for the recall numbers
and the synthetic-vs-real transfer-gap discussion.
