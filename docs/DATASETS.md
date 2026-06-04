# External datasets — extend CONFIDE-Bench

Public, **easily downloadable** de-identification / PII datasets to grow the benchmark
beyond the bundled synthetic RU/EN sets. Fetch via the CLI:

```bash
python3 confide.py datasets list                 # registry (JSON)
python3 confide.py datasets fetch ai4privacy-300k --out data/external/ai4privacy
```

`hf` = HuggingFace `datasets` (`pip install datasets`); `git` = clone; `url` = direct file.
**Verify each license before redistributing.** Several are synthetic; a couple are
research-only. None replaces the therapy-dialogue focus — they're for breadth/comparison.

| Key | Source | Lang | License | Why it's useful |
|---|---|---|---|---|
| `ai4privacy-300k` | HF `ai4privacy/pii-masking-300k` | en/fr/de/it/nl/es | custom/other (see HF `license.md`; commercial use gated) | broad synthetic PII; CONFIDE-Bench's EN-real slice comes from here. **Source text not redistributed** — see note below |
| `ai4privacy-200k` | HF `ai4privacy/pii-masking-200k` | en/fr/de/it | varies | smaller synthetic PII |
| `nemotron-pii` | HF `nvidia/Nemotron-PII` | en | CC-BY-4.0 | synthetic, **50+ entity types** — taxonomy reference |
| `reddit-self-disclosure` | HF `douy/reddit-self-disclosure` | en | research-only | **19 disclosed-experience categories** — closest to therapy self-disclosure |
| `spy` | HF `mks-logic/SPY` | en | see card | synthetic medical+legal Q&A (semi-dialogue) |
| `tab` | git NorskRegnesentral/text-anonymisation-benchmark | en | MIT | ECHR legal; **direct/quasi/coref gold** (methodology ancestor) |
| `jobstack` | git kris927b/JobStack | en | open | job postings; profession/org entities |
| `open-legal-data-de` | HF `open-legal-data/german-court-decisions` | de | ODbL | court-anonymized; German quasi-identifier patterns |

**Integrated as a benchmark slice:** `just-ai/jayguard-ner-benchmark` (ru, **Apache-2.0**,
real anonymized conversational, 850 rows) is now CONFIDE's **RU-real** slice — see the
dedicated section below and `data/sessions-ru-real/`.

**DUA / not-auto-fetchable (listed for completeness — see `RESEARCH-MULTILINGUAL.md`):**
MEDDOCAN (ES, Zenodo), CARMEN-I (ES+CA, PhysioNet DUA), GraSCCoPHI (de), eHOP/Rennes
(fr, RGPD-locked), MultiGraSCCo / PARHAF (CC, arXiv),
PII-Bench RU (ru, HF `hivetrace/pii-bench`, eval-only, synthetic),
i2b2/n2c2 & MIMIC (en, credentialed). See `DATASET-LANDSCAPE.md` for the
full ranked RU/EN/DE/FR/ES acquisition map.

To score a fetched set with CONFIDE-Bench, add a loader that maps it into the
`*-eval.jsonl` schema (per-doc `{text, spans:[{start,end,type}]}`) and register it in
`score_bench.py` GOLD/COMBOS.

## RU-real (JayGuard) — real-text RU, redistributed WITH attribution

CONFIDE's **RU-real** slice (`data/sessions-ru-real/jayguard-ru.jsonl`, 60 docs / 77
spans) is built from `just-ai/jayguard-ner-benchmark` (Just AI), 850 rows of **real,
anonymized conversational Russian**, token-classification BIO.

- **License: Apache-2.0** (HF card + citation). Apache-2.0 **permits redistribution
  with attribution**, so — unlike EN-real — the **source text IS committed** here.
- **Attribution:** *Jay Guard NER Benchmark*, Just AI, 2025, Hugging Face Datasets,
  `https://huggingface.co/datasets/just-ai/jayguard-ner-benchmark`.
- **Honest framing:** real **TEXT, not real therapy** (everyday conversational RU);
  **machine-derived gold** from JayGuard's BIO labels, **not human-adjudicated**;
  **PERSON/LOCATION only** (JayGuard excludes phone/email/financial/medication/date).
- **Reproduce:** `python -m confide_eval.data.build_jayguard_ru_real --limit 60`
  (deterministic first-N rows with an in-scope entity; offsets verified
  `text[start:end]==value` for 100% of spans). Type mapping + dropped tags are
  documented in `data/sessions-ru-real/README.md` and the build script.

Numbers + the synthetic→real transfer-gap discussion: `BENCHMARK.md` §"RU-real
(JayGuard)".

## EN-real (ai4privacy) — source text is NOT redistributed

CONFIDE-Bench's **EN-real** slice is 15 documents sampled from
`ai4privacy/pii-masking-300k`, whose license restricts redistribution of its source
text and derivatives. **This repo therefore does not ship EN-real gold, detector
caches, or result artifacts.** The path `data/sessions-en/pii-eval-ai4privacy.jsonl`
is gitignored and exists only in local worktrees after an explicit fetch/build step.

To make EN-real runnable, build it locally **under ai4privacy's own license**:

```bash
pip install datasets            # one-time, if needed
python -m confide_eval.data.fetch_ai4privacy
```

This re-downloads ai4privacy from Hugging Face, deterministically samples 15 English
validation rows, and writes a local, **gitignored**
`data/sessions-en/pii-eval-ai4privacy.jsonl` (`{text, spans, source}`). The scorer and
detectors use this local file only when present (see `paths.en_real_gold()`). If it is
absent, EN-real is **skipped gracefully** — RU, EN-synth, RU-adversarial, and RU-real are
unaffected, and `make test` / `make check` still pass without any EN-real artifact.
