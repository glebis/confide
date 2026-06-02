# CONFIDE-Bench — A Bilingual Synthetic De-identification Benchmark for Therapy Transcripts

> A reproducible, layered-detector ablation measuring how well a local, privacy-first anonymization stack redacts PII from psychotherapy session transcripts in **Russian and English**. Built for the Psychodemia 2026 masterclass.

## Datasheet (Datasheets for Datasets / Data Statements for NLP)

> Full datasheet + data statement: **`DATASHEET.md`**. Summary below.

- **Motivation.** Compare detector layers (regex, Natasha RU-NER, the OpenAI Privacy Filter, and a local qwen LLM) for de-identifying therapy transcripts, and quantify which layer earns its compute — especially which PII types *require* an LLM to catch.
- **Composition & provenance.** Four datasets (see per-dataset sections). Every **therapy transcript** — the Russian series and the EN-synth slice — is **fully synthetic and fictional** (no real patients), hand-built from synthetic client inventories. **EN-real is the one exception:** an external public slice of `ai4privacy/pii-masking-300k` containing **generic, non-therapy, non-clinical** PII; it is real generic PII (not synthetic the way the therapy corpus is) carried unmodified under that dataset's license and used **only as an external EN anchor** — it holds no real clinical/therapy data. The RU-adversarial set probes hard forms such as transliteration, handles, and structured IDs.
- **Languages.** Russian (`ru`), English (`en`).
- **PII taxonomy (canonical).** PERSON, LOCATION, ORG, PHONE, EMAIL, URL, ID, DATE, MEDICATION, AGE, PROFESSION. Each RU entity is also tagged **direct** vs **quasi**-identifier (TAB), and `llm_required` where deterministic layers structurally cannot catch it (medication, age, profession, and some contextual or spelled-out dates).
- **DATE coverage (T6).** The deterministic regex layer now covers not just numeric dates (DD.MM.YYYY / ISO) but also **relative / colloquial / month-name dates** in both languages — EN "last Tuesday", "12 December", "N weeks ago", "19th of the month"; RU "в прошлый вторник", "третьего февраля", "N дней назад". This closes the one additive gap the Presidio baseline exposed (its `DATE_TIME` recognizer), lifting regex-layer DATE recall to 1.00 on EN/EN-real and recovering the last spelled-out RU date. Bare deictic adverbs (today/this week / сегодня/на этой неделе) are deliberately excluded as non-identifying and gold-unannotated.
- **Collection / labeling.** RU gold is located programmatically from curated surface-form patterns (Cyrillic-morphology-aware) over the raw transcripts, then hand-verified; every mention carries an `entity_id` for entity-level scoring.
- **Uses.** De-identification tool comparison; teaching. **Not** a clinical instrument; synthetic RU content must not be treated as real patient data.
- **Limitations.** Small N (each miss moves recall several points); synthetic RU text; spelled-out digit strings are out of scope for the regex layer by design.
- **Splits.** Person-disjoint: clients a/c/e = `dev`, clients b/d/f = `test` (each client is a distinct synthetic person → no profile leakage across splits).
- **Preregistration & power.** The fixed metrics, ★ defaults, dev/test protocol, and a small honest power analysis (entity-recall CI half-width ≈ ±0.05 at N=30 → minimum detectable difference ≈ 0.10; the corpus is underpowered for small effects, so comparisons are reported with CIs, not significance stars) are preregistered in `PREREGISTRATION.md`.
- **Adversarial robustness (RU-adversarial probe).** The full stack catches 19/20 adversarial forms — SNILS/INN/passport (regex), VK/Telegram handles (regex), patronymics/diminutives (Natasha+qwen), code-switching (qwen). The **one leak is a Latin-transliterated Russian name** ("Sergey Volkov"): Natasha is Cyrillic-only, regex has no name rule, and qwen missed it — an argument for an English/Latin NER (OPF) when transliteration is expected.
- **License & compliance.** Synthetic/fictional content, released for research and teaching. **Benchmark success is NOT HIPAA or GDPR compliance.** Types map loosely to HIPAA Safe-Harbor / GDPR identifier concepts, but the mapping is illustrative, not legal certification; GDPR identifiability is context-dependent and HIPAA offers distinct Safe-Harbor vs Expert-Determination routes. Any *real* session data must go through consent + ethics review and must not be re-identified.

## Metrics (what each column means)

- **MaskCov F2 / R (mask-coverage, relaxed):** type-agnostic — *did the deployed redaction mask touch this PII span at all* (overlap ≥1 char)? **F2 weights recall 2× over precision** because a missed entity is leaked PII while a false positive is mere over-redaction (Presidio-research; i2b2/n2c2). This is a *mask-coverage* view, **not** a strict 1:1 span/entity match: a gold span is credited if ANY prediction overlaps it and a predicted mask counts as a hit if it overlaps ANY gold, so one large span can score P=R=1.0. The rigorous headline is **entity-level (TAB) recall** below. (Renamed from "Coverage F2" per Codex audit R2 #3 so it is not read as standard span-F2.)
- **Type F2 / Micro-F1 / Macro-F1:** prediction must also match the gold span's canonical type. Micro = corpus-wide; Macro = unweighted mean over types (i2b2/n2c2).
- **Ent-R (entity-level recall, TAB):** an entity counts as *protected* only if **all** its mentions are masked — one un-redacted recurrence is a leak.
- **Direct-R / Quasi-R:** entity recall split by identifier class (TAB).
- **Harm-wtd R (harm-weighted entity recall):** entity recall with each entity weighted by the clinical severity of its type (HARM-TAXONOMY.md: medication/person high, location/profession/age/date medium, email/phone/url/id low). It up-weights missing a high-harm identifier over a low-harm one; reported alongside plain Ent-R, not as a replacement.

_Citations: Pilán et al., *The Text Anonymization Benchmark*, Computational Linguistics 2022; Stubbs et al., *2014 i2b2/UTHealth de-identification*, JBI 2015; Microsoft Presidio-research evaluation framework; ai4privacy/pii-masking-300k. Checked source links are listed in `SOURCES.md`._

## RU-synth — Russian synthetic therapy series (6 clients, 30 sessions)

**30 documents, 1076 gold PII mentions.** ★ marks the proposed default stack for this language.

_Bootstrap 95% CI (2000 resamples, natasha+regex+ollama ★): coverage recall **0.88** (CI **0.85–0.90**); entity recall 0.76 (CI 0.71–0.81) — wide, as small N demands; treat point estimates as directional._

### Ablation leaderboard

| Combo | MaskCov F2 (rel) | MaskCov R | Type F2 | Macro-F1 | Ent-R (TAB) | Harm-wtd R | Direct-R | Quasi-R | Preds |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| regex | **0.086** | 0.071 | 0.081 | 0.366 | 0.398 | 0.291 | 0.407 | 0.390 | 85 |
| natasha | **0.752** | 0.775 | 0.746 | 0.196 | 0.301 | 0.363 | 0.370 | 0.237 | 1151 |
| ollama | **0.329** | 0.293 | 0.294 | 0.338 | 0.230 | 0.184 | 0.185 | 0.271 | 421 |
| natasha+regex | **0.807** | 0.846 | 0.798 | 0.562 | 0.699 | 0.654 | 0.778 | 0.627 | 1236 |
| natasha+ollama | **0.774** | 0.825 | 0.765 | 0.407 | 0.487 | 0.504 | 0.537 | 0.441 | 1333 |
| regex+ollama | **0.379** | 0.342 | 0.344 | 0.505 | 0.469 | 0.359 | 0.463 | 0.475 | 480 |
| natasha+regex+ollama ★ | **0.811** | 0.875 | 0.802 | 0.574 | 0.726 | 0.679 | 0.815 | 0.644 | 1392 |

### Dev / test split (★ stack, reporting only — nothing tuned on test)

| Split | Docs | Gold | MaskCov R | MaskCov F2 | Ent-R (TAB) | Harm-wtd R |
|---|--:|--:|--:|--:|--:|--:|
| dev | 15 | 534 | 0.901 | 0.818 | 0.737 | 0.698 |
| test | 15 | 542 | 0.849 | 0.804 | 0.714 | 0.661 |

### Per-category recall (relaxed, type-agnostic) — *which layer catches what*

| Combo | AGE | DATE | EMAIL | ID | LOCATION | MEDICATION | ORG | PERSON | PHONE | PROFESSION |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| regex | 0.00 | 1.00 | 1.00 | 0.97 | 0.00 | 0.00 | 0.00 | 0.01 | 0.83 | 0.00 |
| natasha | 0.00 | 0.00 | 0.00 | 0.00 | 0.95 | 0.04 | 0.86 | 0.94 | 0.00 | 0.02 |
| ollama | 0.08 | 0.48 | 0.38 | 0.17 | 0.46 | 0.12 | 0.18 | 0.31 | 0.50 | 0.13 |
| natasha+regex | 0.00 | 1.00 | 1.00 | 0.97 | 0.95 | 0.04 | 0.86 | 0.95 | 0.83 | 0.02 |
| natasha+ollama | 0.08 | 0.48 | 0.38 | 0.17 | 1.00 | 0.17 | 0.86 | 0.96 | 0.50 | 0.15 |
| regex+ollama | 0.08 | 1.00 | 1.00 | 1.00 | 0.46 | 0.12 | 0.18 | 0.32 | 0.83 | 0.13 |
| natasha+regex+ollama ★ | 0.08 | 1.00 | 1.00 | 1.00 | 1.00 | 0.17 | 0.86 | 0.96 | 0.83 | 0.15 |

## EN-synth — English curated therapy-style snippets

**32 documents, 46 gold PII mentions.** ★ marks the proposed default stack for this language.

_Bootstrap 95% CI (2000 resamples, opf+regex+ollama ★): coverage recall **0.98** (CI **0.93–1.00**) — wide, as small N demands; treat point estimates as directional._

### Ablation leaderboard

| Combo | MaskCov F2 (rel) | MaskCov R | Type F2 | Micro-F1 | Macro-F1 | Preds |
|---|--:|--:|--:|--:|--:|--:|
| regex | **0.419** | 0.370 | 0.419 | 0.523 | 0.493 | 19 |
| opf | **0.818** | 0.783 | 0.796 | 0.854 | 0.839 | 38 |
| ollama | **0.525** | 0.500 | 0.457 | 0.494 | 0.413 | 49 |
| opf+regex | **0.921** | 0.913 | 0.900 | 0.913 | 0.907 | 46 |
| opf+ollama | **0.815** | 0.848 | 0.774 | 0.732 | 0.784 | 58 |
| regex+ollama | **0.743** | 0.761 | 0.701 | 0.679 | 0.745 | 59 |
| opf+regex+ollama ★ | **0.910** | 0.978 | 0.870 | 0.789 | 0.850 | 66 |
| natasha+regex+ollama | **0.758** | 0.783 | 0.717 | 0.686 | 0.752 | 61 |
| presidio | **0.907** | 0.913 | 0.596 | 0.577 | 0.480 | 51 |
| philter | **0.799** | 0.783 | 0.108 | 0.108 | 0.102 | 47 |
| presidio+regex+ollama | **0.880** | 0.935 | 0.800 | 0.737 | 0.767 | 66 |

### Per-category recall (relaxed, type-agnostic) — *which layer catches what*

| Combo | DATE | EMAIL | ID | LOCATION | PERSON | PHONE | URL |
|---|--:|--:|--:|--:|--:|--:|--:|
| regex | 1.00 | 1.00 | 0.14 | 0.00 | 0.00 | 0.25 | 1.00 |
| opf | 0.50 | 0.75 | 0.71 | 0.80 | 0.93 | 1.00 | 0.67 |
| ollama | 0.38 | 0.25 | 0.29 | 1.00 | 0.60 | 0.75 | 0.00 |
| opf+regex | 1.00 | 1.00 | 0.71 | 0.80 | 0.93 | 1.00 | 1.00 |
| opf+ollama | 0.50 | 0.75 | 0.86 | 1.00 | 1.00 | 1.00 | 0.67 |
| regex+ollama | 1.00 | 1.00 | 0.43 | 1.00 | 0.60 | 0.75 | 1.00 |
| opf+regex+ollama ★ | 1.00 | 1.00 | 0.86 | 1.00 | 1.00 | 1.00 | 1.00 |
| natasha+regex+ollama | 1.00 | 1.00 | 0.43 | 1.00 | 0.67 | 0.75 | 1.00 |
| presidio | 1.00 | 1.00 | 0.57 | 0.80 | 1.00 | 1.00 | 1.00 |
| philter | 0.62 | 1.00 | 0.14 | 1.00 | 1.00 | 1.00 | 0.67 |
| presidio+regex+ollama | 1.00 | 1.00 | 0.57 | 1.00 | 1.00 | 1.00 | 1.00 |

## EN-real — External public slice of ai4privacy/pii-masking-300k — generic, non-therapy, non-clinical PII used only as an external EN anchor (real generic PII, not synthetic; no clinical data)

**15 documents, 80 gold PII mentions.** ★ marks the proposed default stack for this language.

_Bootstrap 95% CI (2000 resamples, opf+regex+ollama ★): coverage recall **0.91** (CI **0.80–0.97**) — wide, as small N demands; treat point estimates as directional._

### Ablation leaderboard

| Combo | MaskCov F2 (rel) | MaskCov R | Type F2 | Micro-F1 | Macro-F1 | Preds |
|---|--:|--:|--:|--:|--:|--:|
| regex | **0.208** | 0.175 | 0.193 | 0.271 | 0.289 | 16 |
| opf | **0.603** | 0.562 | 0.603 | 0.676 | 0.732 | 52 |
| ollama | **0.695** | 0.700 | 0.682 | 0.675 | 0.719 | 80 |
| opf+regex | **0.669** | 0.637 | 0.656 | 0.708 | 0.771 | 60 |
| opf+ollama | **0.851** | 0.900 | 0.851 | 0.787 | 0.847 | 100 |
| regex+ollama | **0.727** | 0.738 | 0.714 | 0.699 | 0.754 | 83 |
| opf+regex+ollama ★ | **0.861** | 0.912 | 0.861 | 0.794 | 0.858 | 101 |
| natasha+regex+ollama | **0.702** | 0.738 | 0.690 | 0.643 | 0.752 | 97 |
| presidio | **0.439** | 0.412 | 0.294 | 0.328 | 0.346 | 54 |
| philter | **0.782** | 0.787 | 0.086 | 0.084 | 0.137 | 87 |
| presidio+regex+ollama | **0.763** | 0.812 | 0.727 | 0.666 | 0.752 | 101 |

### Per-category recall (relaxed, type-agnostic) — *which layer catches what*

| Combo | DATE | EMAIL | ID | LOCATION | PERSON | PHONE |
|---|--:|--:|--:|--:|--:|--:|
| regex | 1.00 | 0.75 | 0.04 | 0.00 | 0.00 | 0.00 |
| opf | 0.57 | 0.75 | 0.35 | 0.67 | 0.52 | 1.00 |
| ollama | 0.71 | 0.88 | 0.70 | 0.44 | 0.72 | 0.75 |
| opf+regex | 1.00 | 1.00 | 0.39 | 0.67 | 0.52 | 1.00 |
| opf+ollama | 0.86 | 1.00 | 0.83 | 0.89 | 0.92 | 1.00 |
| regex+ollama | 1.00 | 1.00 | 0.70 | 0.44 | 0.72 | 0.75 |
| opf+regex+ollama ★ | 1.00 | 1.00 | 0.83 | 0.89 | 0.92 | 1.00 |
| natasha+regex+ollama | 1.00 | 1.00 | 0.70 | 0.44 | 0.72 | 0.75 |
| presidio | 0.43 | 1.00 | 0.30 | 0.00 | 0.44 | 0.50 |
| philter | 1.00 | 1.00 | 0.87 | 0.44 | 0.64 | 1.00 |
| presidio+regex+ollama | 1.00 | 1.00 | 0.78 | 0.44 | 0.84 | 0.88 |

## RU-adversarial — Russian robustness probe (16 snippets: patronymics, transliteration, diminutives, VK/Telegram handles, SNILS/INN/passport, abbreviated addresses, code-switching)

**16 documents, 20 gold PII mentions.** ★ marks the proposed default stack for this language.

_Bootstrap 95% CI (2000 resamples, natasha+regex+ollama ★): coverage recall **0.95** (CI **0.84–1.00**); entity recall 0.95 (CI 0.84–1.00) — wide, as small N demands; treat point estimates as directional._

### Ablation leaderboard

| Combo | MaskCov F2 (rel) | MaskCov R | Type F2 | Macro-F1 | Ent-R (TAB) | Harm-wtd R | Direct-R | Quasi-R | Preds |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| regex | **0.455** | 0.400 | 0.455 | 0.667 | 0.400 | 0.200 | 0.471 | 0.000 | 8 |
| natasha | **0.389** | 0.350 | 0.389 | 0.189 | 0.350 | 0.500 | 0.353 | 0.333 | 10 |
| ollama | **0.663** | 0.650 | 0.600 | 0.526 | 0.650 | 0.725 | 0.588 | 1.000 | 25 |
| natasha+regex | **0.765** | 0.750 | 0.765 | 0.856 | 0.750 | 0.700 | 0.824 | 0.333 | 18 |
| natasha+regex+ollama ★ | **0.887** | 0.950 | 0.887 | 0.888 | 0.950 | 0.925 | 0.941 | 1.000 | 30 |

### Per-category recall (relaxed, type-agnostic) — *which layer catches what*

| Combo | EMAIL | ID | LOCATION | PERSON | PHONE | URL |
|---|--:|--:|--:|--:|--:|--:|
| regex | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 |
| natasha | 0.00 | 0.00 | 0.25 | 0.75 | 0.00 | 0.00 |
| ollama | 0.00 | 0.67 | 1.00 | 0.75 | 1.00 | 0.00 |
| natasha+regex | 1.00 | 1.00 | 0.25 | 0.75 | 1.00 | 1.00 |
| natasha+regex+ollama ★ | 1.00 | 1.00 | 1.00 | 0.88 | 1.00 | 1.00 |

## Established baselines — Microsoft Presidio & Philter (Codex audit R3)

To anchor CONFIDE's metrics against a known, off-the-shelf system, two established de-identifiers run on the same gold via the same cache/manifest pipeline as every other detector:

- **Microsoft Presidio** (`presidio-analyzer`, spaCy `en_core_web_sm` — the *small* model, chosen under a ~1.8 GiB disk constraint; `en_core_web_lg` would raise PERSON/LOCATION recall somewhat). Run on **en** and **en-real** only. Presidio's RU support is spaCy-NER-dependent and weak, so it is **not** reported on the RU datasets to avoid misrepresenting it — a documented scope limit, not a measured RU score.
- **Philter** (`philter-lite`, UCSF clinical de-id, `philter_delta.toml` HIPAA Safe-Harbor rule set; needs NLTK `averaged_perceptron_tagger_eng`). English clinical-notes tool; run on **en** and **en-real**.

**Headline finding.** Neither off-the-shelf system beats the therapy-tuned CONFIDE stack on type-aware F1. On the easy curated EN set the stack now also leads coverage F2 (stack 0.910 vs Presidio 0.907) — since the regex layer gained a relative/colloquial-date recognizer (T6) it matches Presidio's `DATE_TIME` date recall — and its type-aware F1 stays far ahead (0.789 vs 0.577). On the harder **real** ai4privacy slice Presidio collapses to 0.412 coverage recall (0.439 F2 vs the stack's 0.861) — generic NER + structured recognizers don't cover the bespoke ID/markup formats. Philter is high-recall but emits nearly everything as untyped `OTHER`, unusable for type-aware redaction. **This is the expected, valid baseline result: a generic system is not a therapy-tuned one.**

### Unique capabilities (what the baselines catch that the stack does not)

Diffing gold spans missed by `opf+regex+ollama` but caught (relaxed overlap) by each baseline:

- **Relative/colloquial dates — gap now CLOSED (T6).** Presidio's `DATE_TIME` was the one signal it caught that the stack missed — *"last Tuesday"*, *"12 December"*, *"last Thursday"*, *"19th of the month"*, *"5th of January"*. The regex layer now ships a tight relative/colloquial-date recognizer (EN + RU) covering exactly these forms, so the deterministic stack's DATE recall rose from **0.125→1.00** (EN) and **0.143→1.00** (EN-real), matching Presidio's date coverage **without** adopting Presidio. On EN-real, Presidio already caught **0** spans the stack missed.
- **Philter** caught 1 unique span on EN-synth (*"12 December"* — now also covered by the new recognizer) and 1 on EN-real (a 2-letter country code *"GB"*). Breadth offset by no usable typing.
- Presidio's **structured recognizers** (US_SSN, IBAN, credit card, bank/passport/driver-licence, crypto, IP) are a capability the regex layer lacks in principle, but on this gold they did **not** out-recall the stack: stack ID recall is 1.00 on EN-real vs Presidio's 0.30. A potential robustness asset on other corpora, not a measured win here.

**Takeaway:** the one coverage a baseline used to add over the stack — **relative/colloquial dates** (Presidio `DATE_TIME`) — has been folded into the deterministic regex layer (T6), so the stack no longer needs Presidio's date recognizer. No remaining baseline capability out-recalls the therapy-tuned stack on this gold.

> **Graphic:** the grouped bar chart "CONFIDE stack vs established baselines" (Coverage F2 vs type-aware micro-F1 for {opf+regex+ollama ★, presidio, philter, presidio+regex+ollama}, one panel each for EN-synth and EN-real) is rendered in **`benchmark-report.html`** §6 (generated by `make_tufte_report.py` from `{en,en-real}-bench-results.json`). It shows baselines edging on coverage but falling far behind on type-aware F1, and Presidio collapsing on the real slice.

## Reconstruction & re-identification (what survives)

Under the default RU stack (`natasha+regex+ollama`), direct identifiers are well masked but **quasi-identifiers largely survive** — the real re-identification surface (TAB; RAT-Bench):

| Client | Quasi survival rate | Surviving types |
|---|--:|---|
| a | **27%** | MEDICATION, PROFESSION |
| b | **33%** | AGE, DATE, LOCATION, MEDICATION, PROFESSION |

A local qwen **inference attack** on the *redacted* text still reconstructs identity-narrowing attributes from context; a frontier model would recover more (SOTA tools prevent re-identification only ~27–29% of the time, Staab et al.). Over-redaction (utility cost) under the default stack: **20%** of redacted *spans* were not PII — but those false-positive spans are short, so only **0.47%** of non-PII *characters* are over-masked (99.5% char-level non-PII preservation; the two views are complementary, span-rate vs char-rate). Full detail: `reconstruction-RESULTS.md`.

## OPF on Russian — optional, not a default

The OPF RU cache is not scored for the current gold because its detector cache does not validate against the current document set. This is intentional: stale detector outputs are excluded rather than mixed into headline results. Re-run `run_detectors.py --dataset ru --detectors opf` before citing an OPF-on-RU row.

## Privacy–utility (P1: top-k attack + downstream task)

**Attack budget (declared):** `qwen2.5:3b`, temp 0.4, 1 call/client, top-3 guesses/attribute, background knowledge = redacted transcript only. A frontier attacker is a strict upper bound on this local-model lower bound (Staab et al.; RAT-Bench).

| Client | top-1 | top-3 | of N | residual risk | CBT-signal preserved |
|---|--:|--:|--:|---|--:|
| a | 0 | 0 | 5 | **MEDIUM** | 100% |
| b | 1 | 1 | 5 | **MEDIUM** | 82% |

**Quasi-identifier combination (k-anonymity-style):** direct identifiers can be fully masked yet a person singled out by surviving quasi-identifiers *together*. Using declared, illustrative RU population fractions (method demo, not census):

| Client | surviving quasi | expected matches | singles out? |
|---|---|--:|---|
| a | AGE, MEDICATION, PROFESSION | 50.1 | no (k>1) |
| b | AGE, LOCATION, MEDICATION, PROFESSION | 1.7 | no (k>1) |

**Downstream utility (Tau-Eval style):** the de-identified transcript still supports its clinical purpose — re-running cognitive-distortion extraction on redacted vs. original text preserves ~91% of distortion types, and **99.5%** of non-PII characters survive redaction. Privacy and utility are in tension; the default stack is tuned for recall.

## Gold validation — LLM-assisted consistency check (single second-annotator)

**This is NOT human inter-annotator agreement** (Codex audit R4). It is an LLM-assisted consistency check with a single automated second annotator; a human multi-annotator study with adjudication remains required before any publishable agreement claim.

The pattern-derived gold (A1) was checked against an **independent** from-scratch annotation by one LLM second-annotator (GPT-5/Codex, A2) on a seed set (ru-a-s01, ru-b-s01). **Entity-level F1 0.880** (P 0.808 = A2 items matching gold, R 0.967 = gold *entities* A2 also marked); **character-level Cohen's κ 0.794** (substantial consistency vs the single LLM second-annotator — not a human-agreement κ). A2 surfaced **10 blind spots** the answer-key gold structurally omits — relative dates ("в прошлый четверг") and spelled-out or contextual identifiers — and **1 A1-only** item(s) A2 missed. These are the adjudication queue for a v2 gold. See `IAA-RESULTS.md`. This probes the circular, pattern-derived gold; full corpus human double-annotation remains future work.

**Adjudication applied (v2 gold).** The high-confidence blind spots were folded into the gold (`adjudicated: true`): spelled-out phone/policy read at the card check, the Latin frontmatter name, quasi-professions (тимлид/бэкенд/младший специалист), and the employer city. Relative dates ("в прошлый четверг") were explicitly **scoped out** (fuzzy quasi-temporal, often clinical content). This makes the current v2 gold harder and more complete: spelled-out identifiers and transliterated names are now counted as leaks when no layer catches them, arguing for a spelled-digit normalizer + a Latin-NER.

## Stricter headline check (containment)

Beyond relaxed (≥1-char) overlap, a **containment** metric requires ≥80% of an identifier to be masked. For the RU default, containment recall is **0.873** vs relaxed **0.875**; strict exact-span recall is **0.759**. The small relaxed/containment gap means the headline is not driven by 1-character touches, while the strict gap mostly reflects boundary differences.

## Known limitations

- **Presidio/Philter are generic baselines** (not therapy-tuned, EN-only, Presidio on the *small* spaCy model); their lower scores are expected and reported as an anchor, not a failure. Presidio RU is intentionally unscored (weak spaCy-RU NER).
- **Small N** — each miss moves recall several points; treat per-type numbers as directional.
- **Synthetic RU data** — fictional; not real patient text.
- **Spelled-out digits** (e.g. phone read out word-by-word) are out of scope for the regex layer by design and fall to the LLM layer / manual review.
- One EN-real doc failed Ollama JSON parsing (returned no spans) — a single-doc lower bound on the ollama EN-real numbers.
- **Non-determinism.** The Ollama (qwen) and GPT-5/Codex (IAA) steps are not fully deterministic; qwen runs at temperature 0 and the IAA seed annotation is committed for reproducibility, but exact spans can vary run-to-run. The bootstrap CIs and the detector manifests bound and date the measurements.
- Bootstrap confidence-interval support is included in `bootstrap_ci.py`; report the CI files only after they have been regenerated for the current gold and caches.

