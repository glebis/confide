# External datasets — extend CONFIDE-Bench

Public, **easily downloadable** de-identification / PII datasets to grow the benchmark
beyond the bundled synthetic RU/EN sets. Fetch via the CLI:

```bash
python3 confide.py datasets list                 # registry (JSON)
python3 confide.py datasets fetch ai4privacy-300k --out eval/external/ai4privacy
```

`hf` = HuggingFace `datasets` (`pip install datasets`); `git` = clone; `url` = direct file.
**Verify each license before redistributing.** Several are synthetic; a couple are
research-only. None replaces the therapy-dialogue focus — they're for breadth/comparison.

| Key | Source | Lang | License | Why it's useful |
|---|---|---|---|---|
| `ai4privacy-300k` | HF `ai4privacy/pii-masking-300k` | en/fr/de/it/nl/es | custom/other (see HF `license.md`; commercial use gated) | broad synthetic PII; CONFIDE-Bench's EN-real slice comes from here |
| `ai4privacy-200k` | HF `ai4privacy/pii-masking-200k` | en/fr/de/it | varies | smaller synthetic PII |
| `nemotron-pii` | HF `nvidia/Nemotron-PII` | en | CC-BY-4.0 | synthetic, **50+ entity types** — taxonomy reference |
| `reddit-self-disclosure` | HF `douy/reddit-self-disclosure` | en | research-only | **19 disclosed-experience categories** — closest to therapy self-disclosure |
| `spy` | HF `mks-logic/SPY` | en | see card | synthetic medical+legal Q&A (semi-dialogue) |
| `tab` | git NorskRegnesentral/text-anonymisation-benchmark | en | MIT | ECHR legal; **direct/quasi/coref gold** (methodology ancestor) |
| `jobstack` | git kris927b/JobStack | en | open | job postings; profession/org entities |
| `open-legal-data-de` | HF `open-legal-data/german-court-decisions` | de | ODbL | court-anonymized; German quasi-identifier patterns |

**DUA / not-auto-fetchable (listed for completeness — see `RESEARCH-MULTILINGUAL.md`):**
MEDDOCAN (ES, Zenodo), CARMEN-I (ES+CA, PhysioNet DUA), GraSCCoPHI (de), eHOP/Rennes
(fr, RGPD-locked), MultiGraSCCo / PARHAF (CC, arXiv), JayGuard & PII-Bench RU (ru),
i2b2/n2c2 & MIMIC (en, credentialed).

To score a fetched set with CONFIDE-Bench, add a loader that maps it into the
`*-eval.jsonl` schema (per-doc `{text, spans:[{start,end,type}]}`) and register it in
`score_bench.py` GOLD/COMBOS.
