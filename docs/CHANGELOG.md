# Changelog

All notable changes to CONFIDE — the anonymizer, the benchmark, the reports,
and the site. Dates are CET. The single source of truth is this file;
`make site-data` syncs it to the website's [/changelog](https://confide.salient.community/changelog) page.

## 2026-06-05

### Added
- **GLiNER-multi PII detector layer** (`gliner`): zero-shot multilingual NER
  (`urchade/gliner_multi_pii-v1`, Apache-2.0, ~1.2 GB) wired into
  `run_detectors.py` with windowed chunking for long transcripts, edge-trim and
  overlap dedupe; reserved detector name; unit tests + live RU/EN smoke test.
  Reported as an exploratory ◇ layer on the same footing as the Gemma swaps.
- **Run-variance study for cloud Gemma4 26B-A4B** (HF router, temp 0): 5
  independent replicates per dataset. EN-synth stack cov R 1.000 ± 0.000,
  cov F2 0.976 ± 0.000; RU-adv entity recall 1.000 ± 0.000, cov F2
  0.935 ± 0.004 (`results/cloud-gemma4-26b-variance-{en,ru-adv}.json`).
- **Standardized update pipeline**: `make site-data` (syncs report rows into
  `site/src/data/model-swaps.json` from the same source as the HTML report),
  `make site-deploy` (local prebuilt → Vercel prod), `make site-update` /
  `tools/update_site.sh` (reports → data → deploy → post-deploy verification).
  The site's model-swap table is now generated, not hand-maintained.
- This changelog (`docs/CHANGELOG.md`) and the site `/changelog` page.

### Changed
- **HF cloud Gemma4 EN run completed**: the 13 English requests cut off by the
  provider on 2026-06-02 were resumed and finished (32/32 docs, 0 empty).
  The complete stack now leads EN-synth (cov R 1.000, type-F2 0.962) — the
  partial-run caveat is gone from the report, site and experiment notes.
- Report section "LLM model comparison" renamed to **"Model comparison"**
  (it now includes a non-LLM NER layer); ◇ footnotes generalized accordingly
  (EN + RU).
- Detector-layers card on `/benchmark` now names Gemma alongside Qwen, plus a
  GLiNER card.

## 2026-06-04

### Added
- **Gemma ◇ rows in every ablation leaderboard** — exploratory Gemma3 /
  Gemma4 12B-MLX / Gemma4 26B-A4B (HF cloud) swaps of the ★ stack shown
  directly in the main tables of the EN/RU reports and BENCHMARK.md.
- **Gemma3/Gemma4 model-swap experiment**: separate detector caches and
  `score_llm_experiment.py` comparisons on RU-synth long, RU-adv, RU-real and
  EN-synth; results documented in `LOCAL-LLM-DEID-EXPERIMENT.md`.
- De-identification tools/benchmarks landscape research brief.

### Changed
- Reconnected granular local development history into the public repository
  (restricted blobs scrubbed); regenerated EN/RU reports.

## 2026-06-03

### Added
- **Astro static site** for CONFIDE-Bench (Tufte-styled): Home, About,
  Benchmark, Toolkit, Contribute pages with section illustrations and
  consent/ethics/RED stance throughout; `/whitepaper` page with
  scientific-paper layout; `/toolkit` catalogues all 10 skills with editorial
  illustrations; og:image and report→site links.
- **Practitioner-facing white paper** (Markdown + PDF) with disclosure and
  credit files; applied a 24-finding external audit.
- **RU-real (JayGuard) slice** wired into the report with adapted disclaimer
  and attribution.
- **Report i18n**: full Russian translation catalog (152 strings) for the
  Tufte report generator; plain-language accessible intro (BLUF standard).

### Fixed
- P0 provenance/licensing pass: corrected synthetic-vs-real and license
  claims (CC-BY, not CC0); removed AI4Privacy-derived EN-real artifacts from
  the repo (now built locally); trimmed the README epigraph to an attributed
  fair-use line; relocated internal docs out of the public repo.
- Site polish: ROC-AUC explained, jargon wrapped in `<abbr>`, EN-real
  gracefully omitted when absent.
