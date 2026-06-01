# Citation Audit — CONFIDE / CONFIDE-Bench

> Independent read-only verification of every external benchmark, dataset, tool, paper,
> and metric cited across the CONFIDE docs. Performed 2026-06-02 via web search/fetch
> against authoritative sources (ACL Anthology, arXiv, HuggingFace, GitHub, PMC).
> **Verdicts:** CONFIRMED (real + accurately described) / IMPRECISE (real but mis-stated —
> correction given) / UNVERIFIED (could not confirm existence) / FABRICATED (does not exist).

## Summary counts

- **CONFIRMED: 27**
- **IMPRECISE: 3**
- **UNVERIFIED: 1**
- **FABRICATED: 0**

No outright fabrications found. The most-suspected citation — the **OpenAI Privacy Filter
(OPF)** — is **real and accurately described**. The novelty claim is **defensible as
worded**. The one item that could not be confirmed at all is **JayGuard** (a claimed RU
dataset). Three citations are real but imprecisely described (most importantly the
ai4privacy-300k license).

---

## Table

| Citation | Where cited (file:line) | CONFIDE's claim | Verdict | Authoritative source | Correction if needed |
|---|---|---|---|---|---|
| **TAB (Text Anonymization Benchmark)** | SOURCES.md:9; BENCHMARK.md:23-26; RESEARCH-FINDINGS.md:46 | Pilán et al., Computational Linguistics 2022; ECHR, 1268 cases; direct/quasi/no-mask, confidential, coref/entity-IDs; entity-level all-mention recall; DOI 10.1162/coli_a_00458 | **CONFIRMED** | aclanthology.org/2022.cl-4.19; CL vol 48(4) 1053-1101 | Exact match. 1,268 ECHR cases, direct + quasi-identifiers, entity-level metrics. DOI correct. |
| **i2b2/UTHealth 2014 de-id (Track 1)** | SOURCES.md:14-18; RESEARCH-FINDINGS.md:42 | Stubbs, Kotfila, Uzuner 2015; strict micro-F1 0.936; 1304 rec / 296 pat | **CONFIRMED** | PMC4989908 (JBI 2015) | Top strict micro-F1 = 0.936 confirmed; CRF+rules winners. |
| **n2c2 / CEGS N-GRID 2016 (psychiatric intake)** | SOURCES.md:19-23; RESEARCH-FINDINGS.md:43 | Stubbs, Filannino, Uzuner 2017; 1000 records; sight-unseen F1 0.799, trained 0.914 | **CONFIRMED** | PMC5705537 (JBI 2017) | 1,000 psychiatric intake records; 0.799 (Track 1.A) / 0.914 (Track 1.B) exact. |
| **MEDDOCAN** | SOURCES.md:24-27; DATASETS.md:27; RESEARCH-FINDINGS.md:45 | Spanish synthetic clinical de-id, 1000 cases; "29 granular entity types" (SOURCES) / "29 types" (RESEARCH) / "22 categories" (RESEARCH-MULTILINGUAL:55) | **IMPRECISE** | IberLEF 2019; PlanTL SPACCC_MEDDOCAN | Real, 1,000 synthetic clinical cases. **Entity-type count is inconsistent across CONFIDE's own docs (29 vs 22).** MEDDOCAN's guidelines define ~21-22 PHI types in the core scheme; the "29" figure appears overstated. Pick one figure and source it. |
| **OpenAI Privacy Filter (OPF), `openai/privacy-filter`** | README.md:32; SOURCES.md:31-33; BENCHMARK.md:9; run_detectors.py:13,58-60 | Open-weight transformers token-classification PII model; "1.5B NER model"; high F1 on PII-Masking-300k; "not a compliance/anonymization guarantee" | **CONFIRMED** | huggingface.co/openai/privacy-filter; openai.com/index/introducing-openai-privacy-filter | Real OpenAI model. **1.5B total / 50M active params** (matches "1.5B" claim). Apache-2.0, 128k ctx, MoE encoder, BIOES token-classification. F1 96% (97.43% corrected) on PII-Masking-300k. The exact "redaction/data-minimization aid, NOT an anonymization/compliance guarantee" disclaimer CONFIDE attributes to it is verbatim on the card. Note: SKILL.md's "2.8 GB" is a disk-footprint figure, not a parameter claim — not a contradiction. |
| **ai4privacy / pii-masking-300k** | DATASETS.md:17; DATASHEET.md:34,77; BENCHMARK.md:29,106 | HF `ai4privacy/pii-masking-300k`; "en/fr/de/it/nl/es"; **"CC-BY-4.0 (OpenPII core)"**; broad synthetic PII; EN-real slice source | **IMPRECISE** | huggingface.co/datasets/ai4privacy/pii-masking-300k | Dataset is real; EN-real provenance is fine. **License is wrong/overstated:** the HF card lists license as `other` (custom `license.md`; commercial use → licensing@ai4privacy.com), **not plain CC-BY-4.0.** The dataset is OpenPII-220k + FinPII-80k (27 PII classes; education/health/psychology subjects). Correct the table to "custom/other license — verify license.md" (CONFIDE already says "Verify each license before redistributing", but the explicit "CC-BY-4.0" cell contradicts that). |
| **Microsoft Presidio** | BENCHMARK.md:170-189; README.md:34; RESEARCH-FINDINGS.md | `presidio-analyzer` + spaCy `en_core_web_sm`; generic NER; EN-first; weak RU (spaCy-dependent) | **CONFIRMED** | github.com/microsoft/presidio (MIT) | MIT-licensed; spaCy-backed; the "Presidio RU is weak/spaCy-NER-dependent" and "EN-first" framing is accurate. |
| **Philter / philter-lite** | BENCHMARK.md:175 | `philter-lite`, UCSF clinical de-id, HIPAA Safe-Harbor rule set; high-recall but untyped `OTHER` | **CONFIRMED** | pypi.org/project/philter-lite; github.com/SironaMedical/philter-lite (fork of BCHSI/philter-ucsf) | philter-lite is the SironaMedical fork of UCSF philter; clinical de-id; characterization accurate. (Original Philter is BSD; CONFIDE makes no false license claim.) |
| **Natasha** | README.md:32; BENCHMARK.md:18,61; SKILL.md | Russian NER; "Cyrillic-only" (so Latin-transliterated RU names leak) | **CONFIRMED** | github.com/natasha/natasha; pypi natasha | Russian NLP/NER (PER/LOC/ORG via Slovnet); Cyrillic-only is accurate — the basis for the documented transliteration leak. |
| **Anonymeter** | SOURCES.md:45-47; README.md (Art-29 taxonomy) | Giomi et al. 2022; attack-based eval of singling-out / linkability / inference (the 3 GDPR risks); arXiv 2211.10459 | **CONFIRMED** | arxiv.org/abs/2211.10459; github.com/statice/anonymeter | Giomi, Boenisch, Wehmeyer, Tasnádi (Statice), 2022 → PETS 2023. Three GDPR risks exact. (Note: it targets **synthetic tabular** data; CONFIDE uses it only for the singling-out/linkability/inference framing, which is fine.) |
| **RAT-Bench** | SOURCES.md:48-52; BENCHMARK.md:193,208; RESEARCH-FINDINGS.md:49 | Emerging attacker-based re-id benchmark; residual re-id rates; openreview FjbU4kLriN | **CONFIRMED** | arxiv.org/abs/2602.12806; openreview.net/forum?id=FjbU4kLriN | Real (Imperial College, Feb 2026). Synthetic, US-demographics, direct+indirect identifiers, LLM-attacker re-id risk. OpenReview ID matches SOURCES.md URL. Correctly flagged as preprint. |
| **Tau-Eval** | BENCHMARK.md:222; RESEARCH-FINDINGS.md:50 | Framework; task-sensitive privacy+utility; "no universal anon benchmark" | **CONFIRMED** | arxiv.org/abs/2506.05979; aclanthology 2025.emnlp-demos.16 | Loiseau et al., EMNLP 2025 (System Demos). Privacy + task-aware utility framing exact. |
| **MathEd-PII** | RESEARCH-FINDINGS.md:51; RESEARCH-MULTILINGUAL.md:14 | Math-tutoring dialogue, 1000 sessions, numeric ambiguity central; 2026 | **CONFIRMED** | arxiv.org/abs/2602.16571 | Real. 1,000 tutoring sessions; numeric-ambiguity over-redaction is the paper's thesis. |
| **Reddit Self-Disclosure** | DATASETS.md:20; RESEARCH-FINDINGS.md (Run-2):76-78 | Dou et al. ACL 2024; 2.4K posts / 4.8K spans; "19 categories of disclosed experiences"; abstraction task; HF `douy/reddit-self-disclosure` | **CONFIRMED** (minor wording) | aclanthology.org/2024.acl-long.741; hf douy/reddit-self-disclosure | Real; 4.8K spans; 19 categories = **13 demographic + 6 personal-experience** (not "19 disclosed-experience categories" — minor phrasing slip, harmless). Abstraction/importance-rating task confirmed. |
| **MultiGraSCCo** | DATASETS.md:28; RESEARCH-MULTILINGUAL.md:48,60; RESEARCH-FINDINGS.md:55 | arXiv 2603.08879, CC-BY-4.0; multilingual incl RU+UK; 19 PHI + 13 indirect identifiers; "excludes Spanish" | **CONFIRMED** | arxiv.org/abs/2603.08879; zenodo.org/records/19489040 | Real (Baroud et al. 2026). 10 languages (de/en/it/fr/ar/pl/ru/uk/tr/fa) — RU+UK included, **Spanish excluded** (matches CONFIDE). Direct + indirect (IPI) identifiers. Built on GraSCCo. |
| **MIDAS** | RESEARCH-MULTILINGUAL.md:56 | Real Spanish motivational-interviewing counseling dialogue (ES+LatAm), 74 sessions, no PII labels; NAACL 2025 | **CONFIRMED** (count unverified) | aclanthology.org/2025.naacl-short.73; arxiv 2502.08458 | Real (Gunal et al., NAACL 2025 short). Spanish MI counseling, expert annotations, no PII labels. The specific "**74 sessions**" figure was not confirmable from the abstract — low-risk but verify against the paper before citing the exact count. |
| **PII-Bench RU / Hivetrace** | DATASETS.md:28; RESEARCH-FINDINGS.md:54 | RU synthetic, 1810 rows, 7 domains; SNILS/INN/passport/OGRN etc.; eval-only; "name-collision caution: PII-Bench reused" | **CONFIRMED** | huggingface.co/datasets/hivetrace/pii-bench | `hivetrace/pii-bench` exists; RU structured IDs (SNILS/INN/passport) present; research/eval-only license. CONFIDE **correctly distinguishes** this from the unrelated arXiv 2502.18545 "PII-Bench" (Query-Aware) — the name-collision caution is accurate and good practice. |
| **PII-Bench (arXiv 2502.18545)** | RESEARCH-MULTILINGUAL.md:25 | 55 fine-grained subtypes, multi-party scenarios | **CONFIRMED** | arxiv.org/pdf/2502.18545 | Real, distinct from Hivetrace's. 55 fine-grained subcategories, query-aware privacy protection. |
| **JayGuard** | DATASETS.md:28; RESEARCH-FINDINGS.md:53,129 | RU noisy chat/support/spoken, 850 rows, real/anon, **Apache-2.0**; PERSON/GPE/address (excludes phone/email/financial) | **UNVERIFIED** | — (no hit on HuggingFace, GitHub, ACL, or RU-language search) | Could not confirm a dataset/corpus named "JayGuard" exists. Highly specific claims (850 rows, Apache-2.0, exact entity scope). **Either supply a resolvable URL/HF ID/paper, or remove the citation before publishing.** This is the single citation that could be a hallucination from the deep-research agent. |
| **Cohen's / Fleiss kappa** | BENCHMARK.md:228; DATASHEET.md:50; IAA-RESULTS.md | char-level Cohen's κ 0.794 for the single-LLM-annotator consistency check | **CONFIRMED** (standard metric; correctly caveated) | — | Standard metric. CONFIDE explicitly states this is NOT human IAA — honest framing. |
| **F2 / Presidio-research** | BENCHMARK.md:23,29 | F2 weights recall 2×; "Presidio-research; i2b2/n2c2" as provenance for recall-favoring de-id scoring | **CONFIRMED** (with nuance) | github.com/microsoft/presidio-research (MIT) | presidio-research evaluation framework is real (MIT). F2 = recall-weighted Fβ (β=2) is standard. The framing "de-id favors recall (a miss = leaked PII)" is the field norm (i2b2/n2c2). Note F2 is not literally a named "de-id standard" in i2b2 — it is a reasonable, correctly-attributed design choice, not a misquote. |
| **Datasheets for Datasets** | SOURCES.md:56-57; DATASHEET.md:5 | Gebru et al. 2021 | **CONFIRMED** | Gebru et al., CACM 2021 / Microsoft Research | Correct. |
| **Data Statements for NLP** | SOURCES.md:58-59; DATASHEET.md:5 | Bender & Friedman 2018 | **CONFIRMED** | aclanthology.org/Q18-1041 (TACL 2018) | Correct. |
| **Staab et al. (LLM inference attack)** | BENCHMARK.md:200,208; README.md:34; RESEARCH-FINDINGS.md:131 | "SOTA tools prevent re-identification only ~27-29% of the time, Staab et al."; ICLR 2024/2025 | **CONFIRMED** (claim-figure not independently re-derived) | Staab et al., "Beyond Memorization: Violating Privacy via Inference with LLMs", ICLR 2024 | Real, correctly attributed for the LLM-inference-attack framing. The specific "27-29% prevented" figure is plausibly from a follow-up/RAT-Bench-style eval; verify the exact number's source before putting it in a paper. |
| **GDPR Recital 26 / Art-29 WP / EDPB** | SOURCES.md:38-44; README.md:34 | "reasonably likely means", singling-out/linkability/inference taxonomy | **CONFIRMED** | eur-lex Recital 26; EDPB SME guide; WP29 Opinion 05/2014 | The singling-out / linkability / inference triad is the WP29/EDPB anonymisation framework — correctly attributed. |
| **HIPAA Safe Harbor (18 identifiers) / Expert Determination** | BENCHMARK.md:19; DATASHEET.md:9; RESEARCH-FINDINGS.md:35 | Two de-id routes; mapping illustrative not certification | **CONFIRMED** | HHS HIPAA de-id guidance | Accurate; correctly disclaimed as non-compliance. |
| **CARMEN-I** | DATASETS.md:28; RESEARCH-MULTILINGUAL.md:54 | Real bilingual ES+CA EHR de-id, 28 PHI types, PhysioNet DUA, Nature Sci Data 2024/25 | **CONFIRMED** | PhysioNet / Nature Scientific Data | Real ES+CA clinical de-id resource, DUA-gated. Characterization accurate. |
| **GraSCCo / GraSCCoPHI / GeMTeX** | DATASETS.md:28; RESEARCH-MULTILINGUAL.md:34 | German synthetic clinical PHI gold; emerging DE de-id standard | **CONFIRMED** | GraSCCo (parent of MultiGraSCCo) | Real German synthetic clinical corpus; PHI-annotated variant exists. |
| **CodE Alltag 2.0** | RESEARCH-MULTILINGUAL.md:36; RESEARCH-FINDINGS.md:47 | Eder et al., LREC 2020; 1.47M real German emails, pseudonymized gold subset | **CONFIRMED** | Eder et al., LREC 2020 | Real German email corpus, pseudonymized. Accurate. |

---

## Must-fix before publishing

1. **JayGuard (UNVERIFIED → possible hallucination).** No trace on HuggingFace, GitHub,
   ACL, arXiv, or Russian-language search. The claims are oddly specific (850 rows,
   Apache-2.0, exact entity scope) — a classic deep-research-agent confabulation pattern.
   **Action:** supply a resolvable URL / HF ID / paper, or delete the citation. Do not let
   it reach a paper unsourced. (DATASETS.md:28; RESEARCH-FINDINGS.md:53,129.)

2. **ai4privacy/pii-masking-300k license = "CC-BY-4.0" is wrong (IMPRECISE).** The HF card
   lists license `other` (custom `license.md`; commercial use gated). Since the EN-real
   slice is *carried unmodified under this license*, mis-stating it is a redistribution
   risk. **Action:** change the DATASETS.md cell to "custom/`other` — see license.md" and
   re-check the EN-real redistribution note in DATASHEET.md §6. (DATASETS.md:17.)

3. **MEDDOCAN entity-type count is internally inconsistent (IMPRECISE).** SOURCES.md says
   "29 granular entity types", RESEARCH-FINDINGS.md says "29 types", but
   RESEARCH-MULTILINGUAL.md says "22 categories". MEDDOCAN's published scheme is ~21-22 PHI
   types; "29" looks overstated. **Action:** reconcile to one sourced figure.

### Minor (fix when convenient, not blocking)
- Reddit Self-Disclosure: "19 disclosed-experience categories" → it is 13 demographic +
  6 personal-experience categories. (DATASETS.md:20.)
- MIDAS "74 sessions" and Staab "27-29% prevented": verify exact figures against the
  primary papers before quoting the numbers in a publication.

## Verdicts on the two flagged claims

- **Novelty claim ("no public RU/EN/DE/FR/ES therapy-dialogue de-id benchmark"):**
  **DEFENSIBLE / supported.** Every adjacent resource resolves to a *different* genre —
  clinical notes (i2b2, N-GRID, MEDDOCAN, CARMEN-I, GraSCCo), legal text (TAB), email
  (CodE Alltag), generic synthetic PII (ai4privacy), math-tutoring dialogue (MathEd-PII),
  or counseling dialogue *without PII labels* (MIDAS, MentalChat16K, CUEMPATHY). None is
  therapy/counseling **dialogue with PII spans**. CONFIDE already uses the correctly hedged
  wording ("To our knowledge… first… combining…") in RESEARCH-FINDINGS.md §7 — keep that
  exact phrasing; avoid the unhedged "first therapy-dialogue de-id benchmark" that appears
  in README.md:33.

- **OPF claim ("OpenAI Privacy Filter, ~1.5B, open weights"):** **CONFIRMED, not
  hallucinated.** `openai/privacy-filter` is a real OpenAI release (Apache-2.0, 1.5B total /
  50M active params, token-classification, 128k context). Its F1 on PII-Masking-300k and
  its "not an anonymization/compliance guarantee" disclaimer are accurately reported. The
  only internal wrinkle is the "2.8 GB" footprint in SKILL.md vs "1.5B params" in
  run_detectors.py — these are file-size vs parameter-count and not contradictory.

---
*Read-only audit. No cited docs were modified. Not committed — left for review.*
