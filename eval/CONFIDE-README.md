```
  ___ ___  _  _ ___ ___ ___  ___
 / __/ _ \| \| | __|_ _|   \| __|
| (_| (_) | .` | _| | || |) | _|
 \___\___/|_|\_|_| |___|___/|___|
```

# CONFIDE — Confidential Filtering of Identifying Details

> _"Confide in me."_ — Kylie Minogue, _Confide in Me_ (1994).
> A problem understood is a problem shared — safely.

![lang](https://img.shields.io/badge/languages-RU%20%2F%20EN-2a9d8f)
![data](https://img.shields.io/badge/data-synthetic-457b9d)
![license](https://img.shields.io/badge/code-MIT-blue)
![status](https://img.shields.io/badge/not-HIPAA%2FGDPR%20clearance-e76f51)

A bilingual **(RU / EN)** de-identification benchmark for **session transcripts** from the helping
professions — therapy, coaching, mentoring. It measures how well a local, privacy-first
anonymization stack redacts personal data from session text, and which detector layer earns its
compute. Party-count-agnostic: it applies to 1:1 *and* group / family / multi-party sessions.
Built for the Psychodemia 2026 masterclass.

**Name.** `CONFIDE` = **CON**fidential **F**iltering of **I**dentifying **DE**tails. Cite it as
*"the CONFIDE benchmark"*; the short suffixed form is **`CONFIDE-Bench`** (not "CONFIDE-Benchmark").

---

## What it measures

A reproducible, **layered-detector ablation**: how much each layer — deterministic **regex**
(emails/URLs/phones/structured IDs), **Natasha** (Russian NER), the **OpenAI Privacy Filter**,
and a local **qwen** LLM — contributes to redacting PII, and crucially **which PII types
*require* an LLM** (medication, age, date, profession) versus those deterministic layers catch.

## Datasets (person-disjoint splits)

| Split | Source | Notes |
|---|---|---|
| `dev` | RU-synth, client-a | fully **fictional** therapy series (no real patients), hand-built from an answer-key PII inventory |
| `test` | RU-synth, client-b | distinct synthetic person → no profile leakage across splits |
| `en` | curated synthetic + `ai4privacy/pii-masking-300k` slice | English validation |

## PII taxonomy (canonical)

`PERSON · LOCATION · ORG · PHONE · EMAIL · URL · ID · DATE · MEDICATION · AGE · PROFESSION`.
Each RU entity is tagged **direct** vs **quasi**-identifier, and `llm_required` where deterministic
layers structurally cannot catch it.

## Metrics

- **Coverage F2 / Recall (relaxed) — headline.** Type-agnostic: *was the PII span redacted at all?*
  **F2 weights recall 2× over precision** — a missed entity is leaked PII; a false positive is mere
  over-redaction (Presidio-research; i2b2/n2c2).
- **Type F2 / Micro-F1 / Macro-F1** — prediction must also match the gold span's type.
- **Ent-R (entity-level recall)** — an entity counts as protected only if **all** its mentions are
  masked; one un-redacted recurrence is a leak. Split into **Direct-R / Quasi-R**.

## Headline result (OpenAI Privacy Filter, English)

| Dataset | Snippets | Gold PII | Recall | Precision | F1 | **F2** |
|---|--:|--:|--:|--:|--:|--:|
| curated therapy-style | 32 | 46 | 0.76 | 0.92 | 0.83 | **0.79** |
| ai4privacy (in-distribution) | 15 | 80 | 0.55 | 0.85 | 0.67 | **0.59** |

> Measured on a CPU laptop — our own numbers, not vendor marketing (the model card claims F1 96%).
> The Privacy Filter was **subsequently dropped from the shipped anonymizer** (≈2 s/line on CPU,
> brittle JSON) in favour of a deterministic regex layer; it remains in the benchmark as a
> comparison point.

## Adversarial robustness (RU probe)

The full stack catches **19/20** adversarial forms (СНИЛС/ИНН/passport, VK/Telegram handles,
patronymics/diminutives, code-switching). The one leak: a **Latin-transliterated Russian name**
("Sergey Volkov") — Natasha is Cyrillic-only, regex has no name rule — an argument for an
English/Latin NER layer when transliteration is expected.

## Quickstart

```bash
pip install -r requirements.txt
python make_benchmark.py        # build/refresh gold + run detectors
# per-language results land in *-bench-results.json / RESULTS.md
```

See `BENCHMARK.md` for the full datasheet and `DATASHEET.md` for the data statement.

## ⚠️ Disclaimer

The Russian corpus is **synthetic and fictional** — it must not be treated as real patient data.
**Benchmark success is NOT HIPAA or GDPR compliance**: type coverage maps loosely to Safe-Harbor /
GDPR identifier concepts, but that mapping is illustrative, not legal clearance. Any *real* session
data must go through consent + ethics review and must never be re-identified.

## Citation

```bibtex
@misc{confide2026,
  title  = {CONFIDE: Confidential Filtering of Identifying Details —
            a bilingual de-identification benchmark for helping-session transcripts},
  author = {Kalinin, Gleb},
  year   = {2026},
  note   = {Psychodemia 2026},
  url    = {https://github.com/glebis/psychodemia-2026}
}
```

## License

Code & prompts: **MIT**. Synthetic data: **CC0**. Use it, fork it, improve it.

## Acknowledgements

Named for the act of confiding — what every client does, in any modality. The benchmark exists so
those words can be *studied without exposing anyone*. ♪ _Confide in me._
