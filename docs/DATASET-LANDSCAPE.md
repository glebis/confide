# Dataset Landscape for CONFIDE

> Scope: annotated corpora **relevant to CONFIDE's therapy-transcript de-identification**
> task — span/entity-level PII or de-id gold, ideally dialogue / clinical / mental-health.
> Goal: identify (a) real/proxy real-data gold for **T1/R7**, (b) public PII-labelled
> **baseline anchors**, (c) **DE/FR/ES** clinical de-id sets for **T9**.
> Produced 2026-06-02 by landscape-research agent (web-verified). **Adds to**, not repeats,
> `DATASETS.md`, `DATASHEET.md`, `RESEARCH-MULTILINGUAL.md`, `RESEARCH-FINDINGS.md`.
> New items vs. prior docs are flagged **[NEW]**. Mark facts UNVERIFIED where noted.
>
> **PRIORITY: Russian (RU) is the most important axis** — see §0 below, which leads. The
> RU track is CONFIDE's hardest sourcing problem; other languages follow in §1–2.

---

## 0. RUSSIAN (RU) — priority axis

CONFIDE's Russian track is the bottleneck: RU therapy-dialogue PII gold does not exist
publicly, and RU PII/de-id resources are thin. Below is a verified inventory across
(a) RU PII/de-id/NER corpora, (b) RU therapy/mental-health dialogue, (c) RU clinical/EHR
de-id, with a ranked acquisition list. **Every row was web-checked 2026-06-02.**

### 0a. RU PII / de-identification / NER corpora (annotated)

| Name | Domain | Annotation (PII? span?) | Size | Real/Synth | Access & License | Verified | Path for CONFIDE RU track |
|---|---|---|---|---|---|---|---|
| **PII-Bench (ru)** **[NEW, VERIFIED]** | general (formal/business text) | **span-level, char indices; 13 PII types incl. NAME/PHONE/EMAIL/ADDRESS/INN/KPP/OGRN/OGRNIP/SNILS/PASSPORT/BANK_CARD/CVC/TOKEN** | 1,810 examples / 156.8K chars | **Synthetic** (Claude 4.5 Sonnet) | HF `hivetrace/pii-bench`; **license "Other" — EVALUATION-ONLY** (no training/derivatives/commercial) | ✅ HF + arXiv 2605.05277 (HiveTraceLab) | **Best RU structured-ID anchor.** Maps directly to CONFIDE's ID/PHONE/EMAIL/PERSON/LOCATION. Use as external RU baseline to score the regex+Natasha+LLM stack on INN/SNILS/passport/OGRN. License blocks redistribution of a derived gold → use for *scoring*, not for building gold. |
| **JayGuard NER benchmark** **[VERIFIED — EXISTS, prior audit's "hallucination" flag is WRONG]** | conversational (chat logs, support, speech transcripts) | **span-level BIO; PERSON/PUBLIC_PERSON/STREET_ADDRESS/GPE/PUBLIC_PLACES/FICT** (no phone/email/financial) | 850 examples | **Real** (anonymized conversational logs) | HF `just-ai/jayguard-ner-benchmark`; **Apache-2.0** (open) | ✅ HF (Just AI), updated 2025-09-03 | **Closest RU genre to therapy** (real noisy conversational Russian, first/second person). Open license → can build a derived gold. Label remaining CONFIDE types (PHONE/EMAIL/DATE/MED/AGE) on top of its PERSON/LOCATION spans. |
| **NEREL** **[NEW]** | news/wiki | nested NER + relations; **29 types incl. PERSON/AGE/PROFESSION/FAMILY/DATE/ORG/CITY/COUNTRY** | 56K entities / 39K relations | **Real** | HF `iluvvatar/NEREL`; github nerel-ds/NEREL (open; confirm license file) | ✅ arXiv 2108.13112, RANLP 2021 | **Best RU span-NER anchor for quasi-IDs** — AGE/PROFESSION/FAMILY overlap CONFIDE exactly. Quasi-baseline for the Natasha layer; nested spans test patronymic/nested-name handling. |
| **RuNNE** **[NEW]** | news | nested NER, few-shot subtask (NEREL-derived) | NEREL subset | **Real** | open | ✅ arXiv 2205.11159 | RU **nested-entity** eval — directly relevant to patronymics / «Иван Иванович Иванов» nesting in CONFIDE RU-adversarial. |
| **RURED** **[NEW]** | finance/econ news | NER + relations; entities incl. **Names/Age/Geo/Currency** | 536 texts / 5K+ relations | **Real** | open (research) | ✅ (RuREBus-2020 proceedings) | Secondary RU NER anchor; has AGE + PERSON. |
| **RuREBus** **[NEW]** | e-government / econ docs | 8 entity + 11 relation types (domain entities, not PII) | 300 texts | **Real** | HF `iluvvatar/RuREBus`; open | ✅ RuREBus-2020 | Low PII relevance (domain entities); listed for completeness. |
| **Nerus** | news (Lenta.ru) | silver PER/LOC/ORG | ~700K articles | **Real, silver** | open (CC, via Natasha/corus) | ✅ | Large RU NER for the Natasha layer (silver labels only). |
| **Natasha eval sets: Collection3, FactRuEval-2016, Persons-1000, Gareev, BSNLP-ru** **[NEW]** | news | PER/LOC/ORG gold | varied | **Real** | open | ✅ natasha.github.io | Gold RU NER to benchmark the Natasha/Slovnet detector layer (no PII-specific types). |
| **Taiga** **[NEW]** | literary/news/**social-media+forums** | raw + meta (NO PII spans) | 480M words | **Real** | open-source (HSE; CC-style) | ✅ tatianashavrina.github.io | Substrate only: its social-media/forum register is the closest *informal RU* text; inject synthetic PII if a larger RU base is needed. |

### 0b. RU therapy / counselling / mental-health DIALOGUE (T1 base — needs PII labelling)

| Name | Domain | Annotation | Size | Real/Synth | Access & License | Verified | Path |
|---|---|---|---|---|---|---|---|
| **— (NONE public)** | therapy/helpline dialogue | — | — | — | — | ✅ searched: only live helpline *contact pages* (124, HSE CPC, telefon-doveriya), **no transcript corpus** | **Gap confirmed.** No published RU psychotherapy/help-line transcript dataset exists. RU therapy gold must be **synthetic** (CONFIDE's existing approach) or built from a non-therapy RU dialogue base. |
| **JayGuard** (see 0a) | conversational RU | PERSON/LOC spans | 850 | Real | Apache-2.0 | ✅ | **Best available real RU dialogue substrate** for a T1-style slice (support/chat, not therapy). |
| **Toloka Persona Chat Rus** **[NEW]** | persona dialogue | persona facts; no PII | 10K dialogues | crowd-authored | open (Kaggle/Yandex Research) | ✅ | RU dialogue base to inject synthetic PII; not therapy genre. |
| **Den4ikAI/russian_dialogues, RuPersonaChat** **[NEW]** | general RU dialogue | none | large | mixed | open (HF) | ✅ (HF listing) | Filler dialogue substrate; no clinical/therapy framing. |

### 0c. RU clinical / EHR de-identification

| Name | Domain | Annotation | Size | Real/Synth | Access & License | Verified | Path |
|---|---|---|---|---|---|---|---|
| **RuMedPrimeData / RuMedPrime** **[NEW]** | outpatient visit records | symptoms text + ICD-10; **records "anonymized" but NO PII-span gold** | 7,625 records (Siberian State Medical Univ.) | **Real, pre-anonymized** | public (RuMedBench family) | ✅ arXiv 2201.06499 | Real RU clinical register; PII already removed → realism/utility anchor, not PII gold. |
| **GENEXOM** **[NEW]** | exome/clinical-genetics reports | "encoded fragments"; no formal PHI scheme | 318 real + 5,000 synth | **Hybrid** | GitHub (public) | ✅ Frontiers AI 2026 (10.3389/frai.2026.1766899) | Evidence that RU clinical corpora are ~94–95% synthetic due to no real anonymized data — supports CONFIDE's synthetic stance. |
| **NEREL-BIO, RuCCoN, RuMedNLI, MedSyn, RuDReC** **[NEW]** | biomed/clinical | concept/NER (not PHI de-id) | varied | real/synth | public | ✅ (Frontiers survey) | RU clinical NER, but **none annotate PHI/PII for de-id** — no RU analogue of MEDDOCAN/i2b2 exists. |
| **152-FZ / GDPR shared task** | — | — | — | — | — | ✅ none found | **No public RU de-id shared task or 152-ФЗ-driven anonymization gold dataset exists.** |

### 0d. RU verdict & ranked "best RU acquisitions for T1"

**Existence rulings:**
- **JayGuard — EXISTS** (`just-ai/jayguard-ner-benchmark`, Apache-2.0, real RU conversational PII spans). A prior audit's "possibly hallucinated" flag is **incorrect**; the resolvable HF ID confirms it.
- **PII-Bench RU — EXISTS** (`hivetrace/pii-bench`, eval-only license, synthetic, 13 structured-ID types).
- **No public RU therapy-dialogue corpus, no RU clinical PHI de-id gold, no 152-ФЗ de-id shared task.**

**Ranked RU acquisitions for the CONFIDE RU track:**
1. **JayGuard** (`just-ai/jayguard-ner-benchmark`, **Apache-2.0**, real, conversational) — *highest value.* Real noisy conversational Russian with PERSON/LOCATION/GPE spans; open license permits a derived gold. **Path:** adopt as a real RU substrate, extend its labels with the full CONFIDE codebook (add PHONE/EMAIL/DATE/MEDICATION/AGE/PROFESSION/ID, identifier_class, roles) → CONFIDE's first *real-text* RU de-id slice, complementing the synthetic RU-synth set.
2. **PII-Bench RU** (`hivetrace/pii-bench`, eval-only, synthetic) — *best external baseline.* **Path:** score the regex+Natasha+OPF+LLM stack against its 13 structured-ID types (INN/SNILS/OGRN/passport/bank-card) as an independent RU anchor — fills CONFIDE's current lack of any external RU baseline. Do **not** redistribute derived data (license).
3. **NEREL** (`iluvvatar/NEREL`, open, real) — *best quasi-ID anchor.* AGE/PROFESSION/FAMILY/PERSON/DATE overlap CONFIDE's quasi-identifier design. **Path:** map NEREL types → CONFIDE types; use as a RU NER baseline and a nested-name (patronymic) stress test via RuNNE.
4. **Natasha gold eval sets** (Collection3 / FactRuEval / Persons-1000, open) — **Path:** benchmark the Natasha detector layer's PER/LOC/ORG recall in isolation (layer-attribution, per DATASHEET motivation).
5. **RuMedPrimeData** (real outpatient RU, pre-anonymized) — **Path:** clinical-register realism/utility anchor only (no PII gold).

> Synthetic remains the only path to RU *therapy* gold — confirmed by the absence of any
> public RU help-line/counselling transcript corpus. JayGuard (real conversational) +
> PII-Bench/NEREL (anchors) are the strongest real RU resources to *validate* that synthetic.

---

## 1. Master table

Columns: Name | Lang | Domain | Annotation | Size | Real/Synth | Access & License | Relevance | URL/ID

### A. Therapy / counselling / mental-health DIALOGUE (closest domain — T1)

| Name | Lang | Domain | Annotation | Size | Real/Synth | Access & License | Relevance | URL/ID |
|---|---|---|---|---|---|---|---|---|
| **AnnoMI** **[NEW]** | EN | dialogue (MI counselling) | MI dialogue-acts/attributes; **no PII** | 133 convs / ~9.7K utterances | **Real** (expert-transcribed from public MI demo videos) | Open; **CC-BY-4.0** per source paper (HF mirror mislabels as `openrail` — UNVERIFIED which governs redistribution) | **Top T1**: real counselling dialogue, free, label PII w/ CONFIDE codebook | github.com/uccollab/AnnoMI ; HF `to-be/annomi-...` |
| **HOPE** **[NEW]** | EN | dialogue (CBT/family/child therapy) | 12 dialogue-act labels; **no PII** | ~12.9K utts / 202–212 sessions | **Real** (YouTube counselling videos) | Request-based (authors); videos public; license UNVERIFIED (likely research-only) | T1 proxy: real multi-modality therapy; needs PII labelling; sourcing/consent caveat | arXiv 2111.06647 (Malhotra et al.) |
| **MentalChat16K** **[NEW]** | EN | dialogue (behavioral-health coaching) | Q-A pairs; **anonymized**, no PII spans | 16,113 pairs (6.3K **real** PISCES-trial transcripts + 9.7K GPT) | **Mixed**; real part is IRB clinical-trial, **already de-identified** | Open; check card (research). PISCES = consented clinical trial | T1: real coach↔caregiver transcripts w/ ethics provenance; already-deid = realism/utility check not PII gold | github.com/PennShenLab/MentalChat16K ; arXiv 2503.13509 |
| **Psych8k / ChatCounselor** **[NEW]** | EN | dialogue (counseling) | instruction pairs; **no PII spans** | ~8K instr. from ~260 real sessions | **Real** source, GPT-4 reshaped | Gated HF (accept terms); **CC-BY-NC-SA-4.0** | T1 proxy (NC limits redistribution); real counseling register | HF `EmoCareAI/Psych8k` ; arXiv 2309.15461 |
| **Counseling & Psychotherapy Transcripts (Alexander Street / Stanford Redivis)** | EN | dialogue (psychotherapy) | full text; **no PII gold** | thousands of sessions | **Real** | **Paywalled / institutional**; Stanford Redivis access-gated | Realism anchor only (not acquirable as open gold) | stanford.redivis.com/datasets/4ew0-9qer43ndg |
| **MIDAS** | ES | dialogue (motivational interviewing) | MI labels; **no PII** | 74 sessions | **Real** | see card | Spanish therapy seed for T9 pilot (already in RESEARCH-MULTILINGUAL) | NAACL 2025 |
| **PriMock57** **[NEW]** | EN | dialogue (primary-care consult) | audio+transcript+notes; **no PII spans** (mock, named actors) | 57 consults | **Synthetic-acted** (mock patients) | Open; **CC** w/ attribution (babylonhealth repo) | Clinical-dialogue base to inject synthetic PII; consent-free (acted) | github.com/babylonhealth/primock57 ; arXiv 2204.00333 |
| **Reddit Self-Disclosure** | EN | social | **19 disclosed-experience categories, span-level** | 2.4K posts / 4.8K spans | **Real** | research-only | Closest *self-disclosure* taxonomy to therapy (already cited) | HF `douy/reddit-self-disclosure` |

### B. Clinical/medical de-id gold (baseline + T9)

| Name | Lang | Domain | Annotation | Size | Real/Synth | Access & License | Relevance | URL/ID |
|---|---|---|---|---|---|---|---|---|
| **i2b2/n2c2 2006/2014/2016 de-id** | EN | clinical notes | PHI spans (HIPAA-like) | thousands of records | **Real** | **DUA / credentialed** (DBMI portal) | Canonical EN de-id baseline (gated) | n2c2 / DBMI |
| **MIMIC-III/IV de-id** | EN | clinical notes | PHI tags | large | **Real** | **PhysioNet credentialed DUA** | EN baseline (gated) | physionet.org |
| **MEDDOCAN** | ES | clinical (synthetic case reports) | 22 PHI categories, span-level | 1,000 docs | Synthetic-ish (real-derived) | Open; **CC-BY-4.0** (Zenodo) | **Best open ES de-id baseline + T9 anchor** | IberLEF 2019 / Zenodo |
| **CARMEN-I** | ES+CA | clinical EHR | 28 PHI types, mask+replace | real EHR | **Real** | **PhysioNet DUA** | Strongest real ES (mirrors CONFIDE mask/generalize); gated | PhysioNet / Nature Sci Data 2024 |
| **MEDDOPLACE** **[NEW]** | ES | clinical | geographic/place PHI | — | mixed | Open (Zenodo) | ES geo-PHI augmentation for T9 | Zenodo |
| **CARDIO:DE / BRONCO150** **[NEW]** | DE | clinical letters | PHI/clinical | 500 / 150 docs | **Real** | **DUA** | Real DE de-id references (gated) | DUA |
| **GraSCCoPHI / GeMTeX** | DE | clinical (synthetic) | PHI gold, α≈0.97 | — | **Synthetic-shareable** | Open / CC | **Best freely-shareable DE de-id; emerging DE standard** | arXiv / GeMTeX |
| **PARHAF** | FR | clinical reports (synthetic) | PHI scheme | large | **Synthetic-shareable** | **CC-BY-4.0** | **Best open FR base** to inject synthetic PII | arXiv 2603.20494 |
| **MultiGraSCCo** | DE/FR/+ | clinical (synthetic) | **19 PHI + 13 indirect IDs** | — | Synthetic | **CC-BY-4.0** | Cross-lingual + quasi-ID schema template (excludes ES) | arXiv 2603.08879 |
| **QUAERO / DEFT (French Med)** **[NEW]** | FR | clinical/biomed | entity NER (not pure PHI) | — | Real | Open (research) | FR NER quasi-anchor for T9 | QUAERO corpus |

### C. General PII / privacy NER (baseline anchors)

| Name | Lang | Domain | Annotation | Size | Real/Synth | Access & License | Relevance | URL/ID |
|---|---|---|---|---|---|---|---|---|
| **ai4privacy pii-masking-300k/200k** | en/fr/de/it/nl/es | general | span-level PII, many types | 200–300K | **Synthetic** | **custom/other license — see HF license.md; redistribution restricted** | Already CONFIDE EN-real slice; multilingual baseline | HF `ai4privacy/...` |
| **Text Anonymization Benchmark (TAB)** | EN | court (ECHR) | direct/quasi/coref spans | 1,268 docs | **Real** | **MIT** | Methodology ancestor; direct/quasi gold | git NorskRegnesentral/TAB |
| **Microsoft Presidio eval data** **[NEW]** | EN(+) | general | PII spans (synthetic generator) | configurable | **Synthetic** | **MIT** | **Direct baseline harness** to score Presidio | github.com/microsoft/presidio-research |
| **PII-Bench** | EN(+) | multi-party | 55 fine-grained subtypes | — | Synthetic | see card | Fine-grained taxonomy anchor (name-collision caution) | arXiv 2502.18545 |
| **Nemotron-PII** | EN | general | 50+ entity types, spans | large | **Synthetic** | **CC-BY-4.0** | Taxonomy-mapping anchor | HF `nvidia/Nemotron-PII` |
| **WikiAnn / CoNLL / WikiNeural** | many | general/news | PER/LOC/ORG only | large | Real | open | Quasi-baseline (no PII-specific types) | HF |

### D. Self-disclosure / re-identification (red-team)

| Name | Lang | Domain | Annotation | Size | Real/Synth | Access | Relevance | URL/ID |
|---|---|---|---|---|---|---|---|---|
| **PANORAMA** | EN | social profiles | profile-consistent linkage | 384K posts | Synthetic | open (arXiv) | Cross-document linkage (multi-session client analogue) | arXiv 2505.12238 |
| **CanaryBench** **[NEW]** | EN | conversation summaries | canary/leakage | — | synthetic | preprint | **Session-note leakage** red-team (exact CONFIDE artifact) | preprint 2601.18834 (UNVERIFIED) |
| **LLM-PBE / PII-Scope** | EN | attack benchmarks | leakage/attack | — | — | open | Downstream-risk axis for red-team | VLDB 2024 / IJCNLP 2025 |
| **WildChat-4.8M** | many | human–LLM chat | Presidio-deid'd | 4.8M | Real | open (AI2) | Conversational PII-pattern + pipeline reference | HF AI2 |

### E. Russian-specific (hardest to source — T1 RU + red-team)

> **See §0 (priority axis) for the full, verified RU inventory + ranked acquisitions.**
> This is the cross-reference summary only.

| Name | Lang | Domain | Annotation | Size | Real/Synth | Access & License | Relevance | URL/ID |
|---|---|---|---|---|---|---|---|---|
| **PII-Bench (ru)** **[NEW, VERIFIED]** | RU | general/business | **span-level; 13 IDs incl. INN/SNILS/OGRN/passport/bank-card/PERSON/PHONE/EMAIL** | 1,810 ex | **Synthetic** | HF `hivetrace/pii-bench`; **eval-only license** | **Best RU structured-ID baseline** | arXiv 2605.05277 |
| **JayGuard** **[VERIFIED — EXISTS]** | RU | conversational (chat/support/speech) | **span BIO; PERSON/GPE/STREET_ADDRESS/PUBLIC_PLACES** | 850 ex | **Real** (anon. logs) | HF `just-ai/jayguard-ner-benchmark`; **Apache-2.0** | **Top RU acquisition** — real conversational, open, label-extendable | HF just-ai |
| **NEREL** **[NEW]** | RU | news/wiki | 29 types incl. **PERSON/AGE/PROFESSION/FAMILY/DATE/ORG**, nested + relations | 56K entities | **Real** | open (github/HF) | Best RU quasi-ID span anchor | HF `iluvvatar/NEREL` |
| **RuNNE (NEREL-based)** **[NEW]** | RU | news | nested NER, few-shot subtask | subset of NEREL | Real | open | RU nested-entity (patronymic) eval | arXiv 2205.11159 |
| **RURED** **[NEW]** | RU | finance/econ news | NER+rel; Names/Age/Geo/Currency | 536 texts | Real | open | Secondary RU anchor (has AGE) | RuREBus-2020 |
| **Nerus** | RU | news (Lenta.ru) | silver PER/LOC/ORG | ~700K articles | **Real, silver** | open (CC, via Natasha) | Large RU NER (silver) | github.com/natasha/nerus |
| **Natasha gold (Collection3, FactRuEval-2016, Persons-1000)** **[NEW]** | RU | news | PER/LOC/ORG gold | varied | Real | open | Score Natasha detector layer | natasha.github.io |
| **Taiga** **[NEW]** | RU | literary/news/**social** | raw + meta; **no PII** | 480M words | Real | open (HSE) | Informal-RU substrate for synthetic-PII injection | tatianashavrina.github.io |
| **RuMedPrimeData** **[NEW]** | RU | clinical (outpatient) | ICD-10; pre-anonymized, **no PII gold** | 7,625 records | Real | public | Clinical-register realism anchor | arXiv 2201.06499 |
| **Toloka Persona Chat Rus** **[NEW]** | RU | dialogue (persona) | persona facts; **no PII gold** | 10K dialogues | crowd | open (Kaggle/Yandex) | RU dialogue substrate (not therapy) | kaggle / research.yandex |

---

## 2. Synthesis

### Top candidates for T1 (real / proxy therapy gold), ranked

1. **AnnoMI** — *best overall.* Real, expert-transcribed **motivational-interviewing
   counselling** dialogue, 133 conversations, freely downloadable (CC-BY-4.0 per the
   source paper; confirm the HF mirror's `openrail` tag is a mislabel before relying on
   it). **No PII labels.** **Path:** treat AnnoMI as the real-dialogue substrate, run the
   CONFIDE codebook over it to hand-label PERSON/LOCATION/ORG/DATE/etc. spans → a *real*
   (non-synthetic) English therapy de-id gold slice with no consent/IRB burden (already-
   public demo content). This directly retires the "no real therapy gold" gap for EN.
2. **MentalChat16K (PISCES real subset)** — real behavioral-health coach↔caregiver
   transcripts from a **consented clinical trial**, already de-identified. **Path:** use
   the 6.3K real transcripts as a realism/utility anchor and as a *de-id-already-applied*
   reference; can't yield fresh PII spans (PII removed) but gives an ethics-clean real
   register and downstream-utility test set.
3. **HOPE** — real multi-modality (CBT/family/child) therapy, 202+ sessions, richer
   genre coverage than AnnoMI. **Path:** request access, label PII with CONFIDE codebook.
   Caveat: YouTube-sourced → consent/sourcing scrutiny; rank below AnnoMI on access clarity.
4. **Psych8k / ChatCounselor** — real-sourced counseling, but **CC-BY-NC-SA** (non-
   commercial, share-alike) and GPT-reshaped. **Path:** secondary proxy; license limits
   redistribution of a derived gold set.
5. **PriMock57** — acted (not real) primary-care consults, but **clinical dialogue with
   open CC license and zero consent risk**. **Path:** inject synthetic PII to create a
   clinical-dialogue de-id slice that complements therapy.

### Best baseline-anchor datasets (public, PII-labelled) to score Presidio/the stack

- **Microsoft Presidio-research eval data (MIT)** — the native harness to benchmark
  Presidio itself; gives an apples-to-apples external baseline.
- **TAB (MIT)** — real, direct/quasi/coref span gold; the methodological anchor for
  CONFIDE's identifier_class (direct/quasi) design.
- **MEDDOCAN (CC-BY-4.0)** — open clinical PHI span gold; best open de-id F1 anchor.
- **ai4privacy 300k (custom/other license — see HF license.md; redistribution restricted)** — multilingual synthetic PII (already the EN-real slice).
- **RU anchors (currently CONFIDE has none):** **PII-Bench RU** (`hivetrace/pii-bench`,
  span-level 13 structured IDs incl. INN/SNILS/OGRN/passport — eval-only), **NEREL**
  (`iluvvatar/NEREL`, PERSON/AGE/PROFESSION/LOCATION/ORG/DATE), and **Natasha gold**
  (Collection3/FactRuEval/Persons-1000) for the detector layer. See §0.

### DE/FR/ES options for T9 (clinical de-id)

- **ES:** **MEDDOCAN** (open, CC-BY-4.0) for baseline; **CARMEN-I** (real, PhysioNet DUA)
  for the strongest real anchor; **MIDAS** (real MI counselling, ES) as the therapy seed.
- **DE:** **GraSCCoPHI / GeMTeX** (open, synthetic, emerging DE standard) as the de-id
  base; **CARDIO:DE / BRONCO150 / 3000PA** (DUA) as real references.
- **FR:** **PARHAF** (open CC-BY-4.0 synthetic clinical) as the injectable base;
  **MultiGraSCCo** (CC-BY-4.0, 19 PHI + 13 indirect IDs) as the quasi-ID schema template;
  **QUAERO/DEFT** as FR NER quasi-anchors. (MultiGraSCCo excludes ES.)

### Gaps — verdict on the therapy-dialogue de-id novelty claim

**The claim holds.** After surveying therapy/counselling dialogue corpora (AnnoMI, HOPE,
MentalChat16K, Psych8k, MIDAS, PriMock57, Alexander Street) and every clinical/general/
court/social PII set above, **no public corpus pairs *therapy/counselling dialogue* with
*span-level PII / de-identification gold* in RU, EN, DE, FR, or ES.** The two axes exist
only separately:
- Therapy-dialogue corpora (AnnoMI, HOPE, MIDAS, MentalChat16K) carry MI/dialogue-act or
  Q-A labels — **never PII spans** (MentalChat16K is pre-deid'd, so PII is removed, not
  labelled).
- PII/de-id span gold lives in **clinical notes** (i2b2, MEDDOCAN, CARMEN-I, GraSCCo),
  **court** (TAB), **social** (Reddit Self-Disclosure), or **synthetic general** (ai4privacy)
  text — **not therapy dialogue.**

**Closest existing thing:** **Reddit Self-Disclosure** (real first-person mental-health
self-disclosure + span-level taxonomy, but social-media monologue, not dialogue) and
**SPY** (synthetic *medical*-dialogue with fine-grained PII spans — closest on *form*, wrong
*genre*). CONFIDE's therapy-dialogue + PII-span + harm-weighting + RU/EN red-team combination
is, as of this survey, **genuinely unoccupied**.

---

## 3. Recommended next acquisitions (concrete)

**RU first (priority):**
1. **JayGuard** (`just-ai/jayguard-ner-benchmark`, **Apache-2.0**, real conversational RU)
   → adopt as the real RU substrate; extend its PERSON/GPE/STREET_ADDRESS spans with the
   full CONFIDE codebook → CONFIDE's first *real-text* RU de-id slice. **Existence confirmed
   — overturn the prior "hallucinated" flag.**
2. **PII-Bench RU** (`hivetrace/pii-bench`, eval-only) → wire into `score_bench.py` as the
   external RU baseline over 13 structured IDs (INN/SNILS/OGRN/passport/bank-card). Score
   only; do not redistribute derived data.
3. **NEREL** (`iluvvatar/NEREL`, open) + **RuNNE** → RU quasi-ID anchor (AGE/PROFESSION/
   FAMILY) and nested-name (patronymic) stress test for the Natasha layer.

**Then cross-language:**
4. **AnnoMI** (CC-BY-4.0) → label a ~20–40 conversation slice → **first real-therapy-dialogue
   PII gold (EN)** (T1/R7). Verify HF-mirror vs GitHub license before release.
5. **Microsoft Presidio-research eval data** (MIT) → external Presidio baseline anchor.
6. **MEDDOCAN + ai4privacy** → cross-corpus PHI/PII comparability table.
7. **For T9:** GraSCCoPHI (DE), PARHAF (FR), MEDDOCAN/MIDAS (ES).
8. **Realism/ethics anchors (no PII gold):** MentalChat16K (consented real coaching),
   PriMock57 (acted clinical), RuMedPrimeData (real RU clinical register).

> Verification notes: **JayGuard CONFIRMED real** (HF `just-ai/jayguard-ner-benchmark`,
> Apache-2.0). **PII-Bench RU CONFIRMED** (HF `hivetrace/pii-bench`, eval-only license).
> AnnoMI HF mirror license (`openrail` vs paper's CC-BY) — **confirm**. HOPE redistribution
> terms — **UNVERIFIED**. CanaryBench preprint 2601.18834 — **UNVERIFIED**. NEREL exact
> license file — **confirm on repo**. No public RU therapy-dialogue corpus, RU clinical PHI
> de-id gold, or 152-ФЗ de-id shared task exists (searched).
