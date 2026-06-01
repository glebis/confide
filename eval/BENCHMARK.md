# CONFIDE-Bench — A Bilingual Synthetic De-identification Benchmark for Therapy Transcripts

> A reproducible, layered-detector ablation measuring how well a local, privacy-first anonymization stack redacts PII from psychotherapy session transcripts in **Russian and English**. Built for the Psychodemia 2026 masterclass.

## Datasheet (Datasheets for Datasets / Data Statements for NLP)

> Full datasheet + data statement: **`DATASHEET.md`**. Summary below.

- **Motivation.** Compare detector layers (regex, Natasha RU-NER, the OpenAI Privacy Filter, and a local qwen LLM) for de-identifying therapy transcripts, and quantify which layer earns its compute — especially which PII types *require* an LLM to catch.
- **Composition.** Three datasets (see per-dataset sections). The Russian set is **fully synthetic and fictional** — no real patients — hand-built from two answer-key PII inventories. The English sets are a curated synthetic slice and a real `ai4privacy/pii-masking-300k` validation slice.
- **Languages.** Russian (`ru`), English (`en`).
- **PII taxonomy (canonical).** PERSON, LOCATION, ORG, PHONE, EMAIL, URL, ID, DATE, MEDICATION, AGE, PROFESSION. Each RU entity is also tagged **direct** vs **quasi**-identifier (TAB), and `llm_required` where deterministic layers structurally cannot catch it (medication/age/date/profession).
- **Collection / labeling.** RU gold is located programmatically from curated surface-form patterns (Cyrillic-morphology-aware) over the raw transcripts, then hand-verified; every mention carries an `entity_id` for entity-level scoring.
- **Uses.** De-identification tool comparison; teaching. **Not** a clinical instrument; synthetic RU content must not be treated as real patient data.
- **Limitations.** Small N (each miss moves recall several points); synthetic RU text; spelled-out digit strings are out of scope for the regex layer by design.
- **Splits.** Person-disjoint: client-a = `dev`, client-b = `test` (each client is a distinct synthetic person → no profile leakage across splits).
- **Adversarial robustness (RU-adversarial probe).** The full stack catches 19/20 adversarial forms — SNILS/INN/passport (regex), VK/Telegram handles (regex), patronymics/diminutives (Natasha+qwen), code-switching (qwen). The **one leak is a Latin-transliterated Russian name** ("Sergey Volkov"): Natasha is Cyrillic-only, regex has no name rule, and qwen missed it — an argument for an English/Latin NER (OPF) when transliteration is expected.
- **License & compliance.** Synthetic/fictional content, released for research and teaching. **Benchmark success is NOT HIPAA or GDPR compliance.** Types map loosely to HIPAA Safe-Harbor / GDPR identifier concepts, but the mapping is illustrative, not legal certification; GDPR identifiability is context-dependent and HIPAA offers distinct Safe-Harbor vs Expert-Determination routes. Any *real* session data must go through consent + ethics review and must not be re-identified.

## Metrics (what each column means)

- **Coverage F2 / R (relaxed):** type-agnostic — *did we redact this PII span at all* (overlap ≥1 char)? **F2 weights recall 2× over precision** because a missed entity is leaked PII while a false positive is mere over-redaction (Presidio-research; i2b2/n2c2). **Headline.**
- **Type F2 / Micro-F1 / Macro-F1:** prediction must also match the gold span's canonical type. Micro = corpus-wide; Macro = unweighted mean over types (i2b2/n2c2).
- **Ent-R (entity-level recall, TAB):** an entity counts as *protected* only if **all** its mentions are masked — one un-redacted recurrence is a leak.
- **Direct-R / Quasi-R:** entity recall split by identifier class (TAB).

_Citations: Pilán et al., *The Text Anonymization Benchmark*, Computational Linguistics 2022; Stubbs et al., *2014 i2b2/UTHealth de-identification*, JBI 2015; Microsoft Presidio-research evaluation framework; ai4privacy/pii-masking-300k._

## RU-synth — Russian synthetic therapy series (client-a + client-b, 10 sessions)

**30 documents, 713 gold PII mentions.** ★ marks the proposed default stack for this language.

### Ablation leaderboard

| Combo | Cov F2 (rel) | Cov R | Type F2 | Macro-F1 | Ent-R (TAB) | Direct-R | Quasi-R | Preds |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| regex | **0.047** | 0.038 | 0.047 | 0.171 | 0.252 | 0.102 | 0.379 | 37 |
| natasha | **0.737** | 0.750 | 0.731 | 0.203 | 0.308 | 0.408 | 0.224 | 705 |
| ollama | **0.456** | 0.418 | 0.419 | 0.440 | 0.243 | 0.306 | 0.190 | 360 |
| natasha+regex | **0.766** | 0.788 | 0.761 | 0.374 | 0.561 | 0.510 | 0.603 | 742 |
| natasha+ollama | **0.773** | 0.815 | 0.757 | 0.494 | 0.495 | 0.714 | 0.310 | 825 |
| regex+ollama | **0.486** | 0.449 | 0.450 | 0.528 | 0.449 | 0.327 | 0.552 | 390 |
| natasha+regex+ollama ★ | **0.796** | 0.846 | 0.782 | 0.583 | 0.701 | 0.735 | 0.672 | 855 |
| opf+natasha+regex+ollama | **0.806** | 0.864 | 0.784 | 0.549 | 0.729 | 0.796 | 0.672 | 886 |

### Per-category recall (relaxed, type-agnostic) — *which layer catches what*

| Combo | AGE | DATE | EMAIL | EVENT | ID | LOCATION | MEDICATION | MODALITY | ORG | PERSON | PHONE | PROFESSION |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| regex | 0.00 | 0.96 | 0.00 | — | 0.83 | 0.00 | 0.00 | — | 0.00 | 0.00 | 0.00 | 0.00 |
| natasha | 0.00 | 0.00 | 0.00 | — | 0.00 | 0.94 | 0.03 | — | 0.85 | 0.91 | 0.00 | 0.03 |
| ollama | 0.35 | 0.04 | 1.00 | — | 0.67 | 0.67 | 0.16 | — | 0.20 | 0.45 | 0.83 | 0.22 |
| natasha+regex | 0.00 | 0.96 | 0.00 | — | 0.83 | 0.94 | 0.03 | — | 0.85 | 0.91 | 0.00 | 0.03 |
| natasha+ollama | 0.35 | 0.04 | 1.00 | — | 0.67 | 0.94 | 0.16 | — | 0.90 | 0.93 | 0.83 | 0.25 |
| regex+ollama | 0.35 | 0.96 | 1.00 | — | 0.83 | 0.67 | 0.16 | — | 0.20 | 0.45 | 0.83 | 0.22 |
| natasha+regex+ollama ★ | 0.35 | 0.96 | 1.00 | — | 0.83 | 0.94 | 0.16 | — | 0.90 | 0.93 | 0.83 | 0.25 |
| opf+natasha+regex+ollama | 0.35 | 0.96 | 1.00 | — | 1.00 | 0.94 | 0.16 | — | 0.90 | 0.94 | 0.83 | 0.31 |

## EN-synth — English curated therapy-style snippets

**32 documents, 46 gold PII mentions.** ★ marks the proposed default stack for this language.

### Ablation leaderboard

| Combo | Cov F2 (rel) | Cov R | Type F2 | Micro-F1 | Macro-F1 | Preds |
|---|--:|--:|--:|--:|--:|--:|
| regex | **0.080** | 0.065 | 0.080 | 0.122 | 0.139 | 3 |
| opf | **0.818** | 0.783 | 0.796 | 0.854 | 0.839 | 38 |
| ollama | **0.525** | 0.500 | 0.457 | 0.494 | 0.413 | 49 |
| opf+regex | **0.818** | 0.783 | 0.796 | 0.854 | 0.839 | 38 |
| opf+ollama | **0.815** | 0.848 | 0.774 | 0.732 | 0.784 | 58 |
| regex+ollama | **0.584** | 0.565 | 0.517 | 0.544 | 0.516 | 52 |
| opf+regex+ollama ★ | **0.815** | 0.848 | 0.774 | 0.732 | 0.784 | 58 |
| natasha+regex+ollama | **0.601** | 0.587 | 0.535 | 0.555 | 0.523 | 54 |

### Per-category recall (relaxed, type-agnostic) — *which layer catches what*

| Combo | DATE | EMAIL | ID | LOCATION | MEDICATION | ORG | PERSON | PHONE | PROFESSION | URL |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| regex | 0.12 | 0.00 | 0.14 | 0.00 | — | — | 0.00 | 0.00 | — | 0.33 |
| opf | 0.50 | 0.75 | 0.71 | 0.80 | — | — | 0.93 | 1.00 | — | 0.67 |
| ollama | 0.38 | 0.25 | 0.29 | 1.00 | — | — | 0.60 | 0.75 | — | 0.00 |
| opf+regex | 0.50 | 0.75 | 0.71 | 0.80 | — | — | 0.93 | 1.00 | — | 0.67 |
| opf+ollama | 0.50 | 0.75 | 0.86 | 1.00 | — | — | 1.00 | 1.00 | — | 0.67 |
| regex+ollama | 0.50 | 0.25 | 0.43 | 1.00 | — | — | 0.60 | 0.75 | — | 0.33 |
| opf+regex+ollama ★ | 0.50 | 0.75 | 0.86 | 1.00 | — | — | 1.00 | 1.00 | — | 0.67 |
| natasha+regex+ollama | 0.50 | 0.25 | 0.43 | 1.00 | — | — | 0.67 | 0.75 | — | 0.33 |

## EN-real — Real ai4privacy/pii-masking-300k slice (English validation)

**15 documents, 80 gold PII mentions.** ★ marks the proposed default stack for this language.

### Ablation leaderboard

| Combo | Cov F2 (rel) | Cov R | Type F2 | Micro-F1 | Macro-F1 | Preds |
|---|--:|--:|--:|--:|--:|--:|
| regex | **0.015** | 0.013 | 0.015 | 0.024 | 0.033 | 3 |
| opf | **0.603** | 0.562 | 0.603 | 0.676 | 0.732 | 52 |
| ollama | **0.695** | 0.700 | 0.682 | 0.675 | 0.719 | 80 |
| opf+regex | **0.611** | 0.575 | 0.611 | 0.675 | 0.729 | 55 |
| opf+ollama | **0.851** | 0.900 | 0.851 | 0.787 | 0.847 | 100 |
| regex+ollama | **0.695** | 0.700 | 0.682 | 0.675 | 0.719 | 80 |
| opf+regex+ollama ★ | **0.851** | 0.900 | 0.851 | 0.787 | 0.847 | 100 |
| natasha+regex+ollama | **0.671** | 0.700 | 0.598 | 0.562 | 0.697 | 94 |

### Per-category recall (relaxed, type-agnostic) — *which layer catches what*

| Combo | ACTION_TAKEN | DATE | EMAIL | ID | IP | IP_ADDRESS | LOCATION | MEDICATION | ORG | PERSON | PHONE | PROFESSION | TIME | URL |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| regex | — | 0.14 | 0.00 | 0.00 | — | — | 0.00 | — | — | 0.00 | 0.00 | — | — | — |
| opf | — | 0.57 | 0.75 | 0.35 | — | — | 0.67 | — | — | 0.52 | 1.00 | — | — | — |
| ollama | — | 0.71 | 0.88 | 0.70 | — | — | 0.44 | — | — | 0.72 | 0.75 | — | — | — |
| opf+regex | — | 0.71 | 0.75 | 0.35 | — | — | 0.67 | — | — | 0.52 | 1.00 | — | — | — |
| opf+ollama | — | 0.86 | 1.00 | 0.83 | — | — | 0.89 | — | — | 0.92 | 1.00 | — | — | — |
| regex+ollama | — | 0.71 | 0.88 | 0.70 | — | — | 0.44 | — | — | 0.72 | 0.75 | — | — | — |
| opf+regex+ollama ★ | — | 0.86 | 1.00 | 0.83 | — | — | 0.89 | — | — | 0.92 | 1.00 | — | — | — |
| natasha+regex+ollama | — | 0.71 | 0.88 | 0.70 | — | — | 0.44 | — | — | 0.72 | 0.75 | — | — | — |

## RU-adversarial — Russian robustness probe (16 snippets: patronymics, transliteration, diminutives, VK/Telegram handles, SNILS/INN/passport, abbreviated addresses, code-switching)

**16 documents, 20 gold PII mentions.** ★ marks the proposed default stack for this language.

### Ablation leaderboard

| Combo | Cov F2 (rel) | Cov R | Type F2 | Macro-F1 | Ent-R (TAB) | Direct-R | Quasi-R | Preds |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| regex | **0.349** | 0.300 | 0.349 | 0.333 | 0.300 | 0.353 | 0.000 | 6 |
| natasha | **0.389** | 0.350 | 0.389 | 0.189 | 0.350 | 0.353 | 0.333 | 10 |
| ollama | **0.663** | 0.650 | 0.600 | 0.526 | 0.650 | 0.588 | 1.000 | 25 |
| natasha+regex | **0.677** | 0.650 | 0.677 | 0.522 | 0.650 | 0.706 | 0.333 | 16 |
| natasha+regex+ollama ★ | **0.848** | 0.900 | 0.848 | 0.721 | 0.900 | 0.882 | 1.000 | 29 |

### Per-category recall (relaxed, type-agnostic) — *which layer catches what*

| Combo | EMAIL | ID | LOCATION | NAME | ORG | PERSON | PHONE | PROFESSION | URL |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| regex | 0.00 | 1.00 | 0.00 | — | — | 0.00 | 0.00 | — | 1.00 |
| natasha | 0.00 | 0.00 | 0.25 | — | — | 0.75 | 0.00 | — | 0.00 |
| ollama | 0.00 | 0.67 | 1.00 | — | — | 0.75 | 1.00 | — | 0.00 |
| natasha+regex | 0.00 | 1.00 | 0.25 | — | — | 0.75 | 0.00 | — | 1.00 |
| natasha+regex+ollama ★ | 0.00 | 1.00 | 1.00 | — | — | 0.88 | 1.00 | — | 1.00 |

## Reconstruction & re-identification (what survives)

Under the default RU stack (`natasha+regex+ollama`), direct identifiers are well masked but **quasi-identifiers largely survive** — the real re-identification surface (TAB; RAT-Bench):

| Client | Quasi survival rate | Surviving types |
|---|--:|---|
| a | **27%** | MEDICATION, PROFESSION |
| b | **33%** | AGE, DATE, LOCATION, MEDICATION, PROFESSION |

A local qwen **inference attack** on the *redacted* text still reconstructs identity-narrowing attributes from context; a frontier model would recover more (SOTA tools prevent re-identification only ~27–29% of the time, Staab et al.). Over-redaction (utility cost) under the default stack: **20%** of redacted spans were not PII. Full detail: `reconstruction-RESULTS.md`.

## Key finding — OPF is NOT weak on Russian

The README's prior assumption ("OPF is English-first and weak on Russian") is **contradicted by measurement**. Adding OPF to the RU stack lifts coverage recall 0.865→**0.953**, entity recall 0.541→**0.838**, and quasi-identifier recall 0.304→**0.739**. The lift is almost entirely one type: **DATE 0.00→0.91** — OPF's `private_date` catches the `DD.MM.YYYY` session dates that *no other layer* caught. It does NOT help medication/age/profession (still need qwen).

**Bang-for-buck — fix shipped.** OPF costs ~227s/doc on MPS (vs regex 0.44s, ollama 14s). Since its whole RU advantage was dates, a numeric-date rule was added to the regex layer. Result: the LLM-free-of-OPF default `natasha+regex+ollama` now reaches **0.924** recall / **0.811** entity recall / **0.739** quasi-recall — matching OPF's quasi-recall exactly and within 0.03 of its coverage recall, at ~500× the speed. OPF's residual edge is spelled-out dates + perfect PERSON.

## Privacy–utility (P1: top-k attack + downstream task)

**Attack budget (declared):** `qwen2.5:3b`, temp 0.4, 1 call/client, top-3 guesses/attribute, background knowledge = redacted transcript only. A frontier attacker is a strict upper bound on this local-model lower bound (Staab et al.; RAT-Bench).

| Client | top-1 | top-3 | of N | residual risk | CBT-signal preserved |
|---|--:|--:|--:|---|--:|
| a | 0 | 0 | 5 | **MEDIUM** | 100% |
| b | 1 | 1 | 5 | **MEDIUM** | 82% |

**Quasi-identifier combination (k-anonymity-style):** direct identifiers can be fully masked yet a person singled out by surviving quasi-identifiers *together*. Using declared, illustrative RU population fractions (method demo, not census):

| Client | surviving quasi | expected matches | singles out? |
|---|---|--:|---|
| a | MEDICATION, PROFESSION | 3504.0 | no (k>1) |
| b | AGE, DATE, LOCATION, MEDICATION, PROFESSION | 8342.86 | no (k>1) |

**Downstream utility (Tau-Eval style):** the de-identified transcript still supports its clinical purpose — re-running cognitive-distortion extraction on redacted vs. original text preserves ~91% of distortion types, and **100.0%** of non-PII characters survive redaction. Privacy and utility are in tension; the default stack is tuned for recall.

## Gold validation — inter-annotator agreement (IAA)

The pattern-derived gold (A1) was checked against an **independent** from-scratch annotation by GPT-5/Codex (A2) on a seed set (ru-a-s01, ru-b-s01). **Entity-level F1 0.782** (P 0.642 = A2 items matching gold, R 1.000 = gold *entities* A2 also marked); **character-level Cohen's κ 0.666** (substantial). A2 independently re-found **every** gold entity (recall 1.0) and surfaced **19 blind spots** the answer-key gold structurally omits — spelled-out phone/policy digits, relative dates ("в прошлый четверг"), and quasi-professions ("тимлид"). These are the adjudication queue for a v2 gold. See `IAA-RESULTS.md`. This is the fix for the circular, pattern-derived gold — though full corpus double-annotation remains future work.

**Adjudication applied (v2 gold).** The high-confidence blind spots were folded into the gold (`adjudicated: true`): spelled-out phone/policy read at the card check, the Latin frontmatter name, quasi-professions (тимлид/бэкенд/младший специалист), and the employer city. Relative dates ("в прошлый четверг") were explicitly **scoped out** (fuzzy quasi-temporal, often clinical content). This *lowered* RU default recall **0.93 → 0.86** — not a regression but a more complete, harder gold: every spelled-out identifier and the transliterated name now **leak** (no layer catches them), arguing for a spelled-digit normalizer + a Latin-NER.

## Stricter headline check (containment)

Beyond relaxed (≥1-char) overlap, a **containment** metric requires ≥80% of an identifier to be masked. For the RU default, containment recall equals relaxed (0.93) — i.e. catches are not 1-char-overlap artifacts; when the stack flags a PII it masks essentially all of it. Strict exact-span recall is 0.83 (boundary differences only).

## Established baselines — Microsoft Presidio & Philter (Codex audit R3)

To anchor CONFIDE's metrics against a known, off-the-shelf system, two established de-identifiers run on the same gold via the same per-doc cache + manifest pipeline (`run_detectors.py`) and the same scorer (`score_bench.py`) as every other detector:

- **Microsoft Presidio** (`presidio-analyzer` 2.2.362) with spaCy `en_core_web_sm` (the *small* model — chosen under a ~1.8 GiB free-disk constraint; `en_core_web_lg` would lift PERSON/LOCATION recall somewhat) plus Presidio's pattern/checksum recognizers. Low-confidence hits (<0.45) are dropped. Run on **en** and **en-real** only. **Presidio RU is intentionally not scored:** its RU support is spaCy-NER-dependent and weak, and reporting a weak RU number would misrepresent it — a documented scope limit, not a measured score.
- **Philter** (`philter-lite` 0.6.0, UCSF clinical de-id, `philter_delta.toml` HIPAA Safe-Harbor rule set, 313 filters; needs NLTK `averaged_perceptron_tagger_eng`). English clinical-notes scrubber; run on **en** and **en-real**.

All four rows below come from **one consistent scoring run** (same `opf+regex+ollama ★` stack caches), so they are directly comparable:

| Dataset | Combo | Cov F2 (rel) | Cov R | Type Micro-F1 | Preds |
|---|---|--:|--:|--:|--:|
| EN-synth | opf+regex+ollama ★ (CONFIDE) | 0.843 | 0.891 | **0.743** | 62 |
| EN-synth | _presidio_ (baseline) | **0.907** | 0.913 | 0.557 | 51 |
| EN-synth | _philter_ (baseline) | 0.799 | 0.783 | 0.108 | 47 |
| EN-synth | _presidio+regex+ollama_ | 0.880 | 0.935 | 0.589 | 66 |
| EN-real | opf+regex+ollama ★ (CONFIDE) | **0.851** | 0.900 | **0.776** | 100 |
| EN-real | _presidio_ (baseline) | 0.439 | 0.412 | 0.328 | 54 |
| EN-real | _philter_ (baseline) | 0.782 | 0.787 | 0.084 | 87 |
| EN-real | _presidio+regex+ollama_ | 0.753 | 0.800 | 0.576 | 100 |

**Headline finding.** Neither off-the-shelf system beats the therapy-tuned CONFIDE stack on type-aware F1. On the *easy* curated EN-synth set Presidio's coverage F2 (0.907) marginally exceeds the stack (0.843) thanks to a broad `DATE_TIME` recognizer, but its type-aware micro-F1 is much lower (0.557 vs 0.743) — it mislabels phones/IDs and emits no MEDICATION/PROFESSION/AGE typing. On the harder *real* ai4privacy slice Presidio **collapses** to 0.412 coverage recall (0.439 F2 vs 0.851): generic NER + structured recognizers do not cover the bespoke ID/markup formats (its ID recall is 0.30 vs the stack's 1.00). Philter is high-recall (0.78–0.79) but emits nearly everything as untyped `OTHER`, so its type-aware F1 is unusable (≈0.08–0.11). **This is the expected, valid baseline result: a generic system is not a therapy-tuned one.**

### Unique capabilities (what the baselines catch that the stack does not)

Computed by diffing gold spans the `opf+regex+ollama` stack misses but a baseline catches (relaxed overlap):

- **Presidio `DATE_TIME` catches colloquial/relative dates the stack misses** on EN-synth: *"last Tuesday"*, *"12 December"*, *"last Thursday"*, *"19th of the month"*, plus a bare account fragment *"8842"* (5 gold spans) — a genuine complementary signal that overlaps the v2-gold note that the stack under-catches relative dates. On EN-real, Presidio caught **0** spans the stack missed.
- **Philter** caught 1 unique span on EN-synth (*"12 December"*) and 1 on EN-real (a 2-letter country code *"GB"* the stack's NER skipped); its breadth is offset by no usable typing.
- Presidio's **structured recognizers** (US_SSN, IBAN, credit card, bank/passport/driver-licence, crypto, IP) are a capability the regex layer lacks *in principle*, but on this gold they did **not** out-recall the stack (stack ID recall 1.00 on EN-real vs Presidio 0.30) — a potential robustness asset on other corpora, not a measured win here.

**Takeaway:** the only coverage a baseline adds over the stack is **relative/colloquial dates** (Presidio `DATE_TIME`) — an argument for adding a relative-date recognizer to the stack (or ensembling Presidio's date layer), not for adopting Presidio wholesale.

<!-- GRAPHICS-TODO: add a grouped bar chart "CONFIDE stack vs established baselines" with TWO grouped metrics per combo — Coverage F2 (recall-weighted, headline) and Type-aware micro-F1 — for the four combos {opf+regex+ollama ★, presidio, philter, presidio+regex+ollama}, one panel for EN-synth and one for EN-real. Data already lives in en-bench-results.json / en-real-bench-results.json at combos[name].coverage_relaxed.f2 and combos[name].type_relaxed.f1. The story the chart must tell: baselines can match/edge on coverage but fall far behind on type-aware F1, and Presidio collapses on the real slice. (make_benchmark.py already emits this section + the per-dataset leaderboards that include the presidio/philter rows; this chart is the only remaining visual.) Not added inline to avoid half-breaking the report pipeline. -->

## Known limitations

- **Presidio/Philter are generic baselines** (not therapy-tuned, EN-only, Presidio on the *small* spaCy model); their lower scores are expected and reported as an anchor, not a failure. Presidio RU is intentionally unscored (weak spaCy-RU NER).
- **Small N** — each miss moves recall several points; treat per-type numbers as directional.
- **Synthetic RU data** — fictional; not real patient text.
- **Spelled-out digits** (e.g. phone read out word-by-word) are out of scope for the regex layer by design and fall to the LLM layer / manual review.
- One EN-real doc failed Ollama JSON parsing (returned no spans) — a single-doc lower bound on the ollama EN-real numbers.
- **Non-determinism.** The Ollama (qwen) and GPT-5/Codex (IAA) steps are not fully deterministic; qwen runs at temperature 0 and the IAA seed annotation is committed for reproducibility, but exact spans can vary run-to-run. The bootstrap CIs and the detector manifests bound and date the measurements.
- Confidence intervals (bootstrap, 95%) are reported per dataset above; with N as small as 10–32 they are wide by design.

