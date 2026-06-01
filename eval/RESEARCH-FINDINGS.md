# Deep-Research Findings — De-identification Benchmarks, Methods & Datasets

> **Provenance:** external deep-research agent (pasted 2026-06-01), produced from
> `eval/RESEARCH-PROMPT.md`. Citations in the original were footnote markers (￼)
> without resolved URLs — **treat every claim as needs-verification** before it
> goes into a paper. This file is the working record; verify sources against the
> annotated bibliography (§10) before citing.

## 1. Executive summary

CONFIDE-Bench has a strong positioning claim only if it refuses to be "yet another PII
NER benchmark." The defensible novelty is: RU+EN psychotherapy-style dialogue,
layered detector ablation, direct/quasi taxonomy, all-mention masking, and
re-identification plus utility scoring in one benchmark. Existing anchors cover
clinical notes, legal text, email, broad synthetic PII, and emerging attacker-based
evaluation, but there is **no public dedicated psychotherapy/counseling dialogue
de-identification benchmark**. Nearest neighbors: n2c2 2016 psychiatric intake
notes (notes, not dialogue), mental-health dialogue datasets (not de-id benchmarks),
and MathEd-PII (dialogue but math tutoring).

Methodologically, inherit TAB's direct/quasi/no-mask + coreference schema,
i2b2/n2c2 strict/relaxed/token discipline, and RAT-Bench/Tau-Eval/Staab attacker +
privacy-utility framing. Main weakness: synthetic-only risk. Roadmap: **P0** schema,
splits, IAA, ablation harness; **P1** attacker/utility + RU adversarial; **P2**
consented/paraphrased real validation + public leaderboard.

## 2. Source-quality notes
Peer-reviewed papers / official dataset cards / institutional docs = primary.
Vendor pages (OpenAI Privacy Filter, John Snow Labs, AWS, Azure, GCP) describe
functionality, not neutral performance. OPF reports high F1 on PII-Masking-300k but
states it is **not** a compliance/anonymization guarantee. 2025–2026 preprints
(RAT-Bench, Tau-Eval, MathEd-PII, MultiGraSCCo, PII-Bench variants) are relevant but
not as settled as i2b2/n2c2, TAB, MEDDOCAN, MIMIC, Philter. Legal: HIPAA Safe Harbor
(18-identifier rule) vs Expert Determination; GDPR identifiability is
context-dependent.

## 3. Benchmark comparison (key rows)

| Benchmark | Domain / lang / size | Real/synth | Taxonomy | Relevance |
|---|---|---|---|---|
| i2b2 2006 | EN discharge summaries, 889 rec | real, surrogate | HIPAA-like PHI | canonical strict span scoring |
| i2b2/n2c2 2014 | EN longitudinal, 1304 rec/296 pat | real | 7 cat / 25 subcat, double-annot+arbitration | strict micro-F1 ~.936; CRF+rules win |
| n2c2 CEGS N-GRID 2016 | EN **psychiatric intake notes**, 1000 rec | real | 7 cat / 30 subcat | closest mental-health ancestor; sight-unseen F1 .799 → trained .914 (domain shift) |
| MIMIC-III/IV(-Note) | EN critical-care EHR/notes | real, DUA | rule+neural de-id pipeline | PHI realism + access norms |
| MEDDOCAN 2019 | ES clinical cases, 1000 synth | synth | 29 types (GDPR/HIPAA) | non-EN clinical precedent, guidelines |
| **TAB 2022** | EN ECHR legal, 1268 cases | real | direct/quasi/no-mask, confidential, coref/entity-IDs | **best methodological ancestor** (DOI 10.1162/coli_a_00458) |
| CodE Alltag (S/XL) | DE email, ~800 + XL | real, pseudonymized | people/loc/date/IDs/social | informal/message-like de-id |
| ai4privacy 200k/300k/2M | broad synth chat/business; 2M multilingual | synth | 2M: 32 locales, 98 types | broad taxonomy; dataset-card evidence |
| RAT-Bench 2026 | synth multi-domain/lingual | synth | direct + indirect, US demographics | **re-id as attacker success** (emerging) |
| Tau-Eval 2025 | framework | OSS | task-sensitive privacy+utility | "no universal anon benchmark" — utility is task-relative |
| MathEd-PII 2026 | math-tutoring dialogue, 1000 sess | HITL LLM | numeric ambiguity central | best non-therapy dialogue PII ref |
| MentalChat16K / CounseLLMe | mental-health dialogue | synth/anon | QA/quality, **not** de-id | "near miss" — gap evidence |
| **JayGuard 2025** | **RU** noisy chat/support/spoken, 850 | real, anon, Apache-2.0 | PERSON/GPE/address (excludes phone/email/financial) | RU names, inflection, messy syntax |
| **Hivetrace / PII-Bench RU** | **RU** synth, 1810, 7 domains | synth (Claude 4.5), eval-only | NAME/PHONE/EMAIL/ADDRESS/card/CVC/INN/KPP/OGRN/OGRNIP/SNILS/passport/token | RU structured identifiers |
| MultiGraSCCo 2026 | multilingual incl **RU+UK** clinical, >2500 annot | synth/translated, CC-BY-4.0 | direct + indirect | RU within multilingual clinical |

**Direct answers:** (a) no public psychotherapy/counseling dialogue de-id benchmark
exists; (b) RU coverage is thin/fragmented — JayGuard (conversational names/addr),
PII-Bench RU (structured IDs), MultiGraSCCo (multilingual clinical) — none is RU
psychotherapy dialogue with direct/quasi + all-mention + ablation + re-id.

## 4–5. Methods / per-type winners (condensed)
- **Regex/rules** win structured IDs (email/phone/URL/date/cards/SNILS/INN/passport);
  brittle to numeric ambiguity (MathEd-PII warning).
- **CRF/feature** dominated early clinical de-id; **neural NER** improved robustness
  (N-GRID LSTM > CRF); **LLMs** win **quasi-identifiers / inference-prone facts**
  (occupation, family structure, rare events, combinations).
- **Hybrid/layered is the historical winning pattern** — CONFIDE-Bench's stack is well
  aligned; must score over-redaction + utility, not just recall.
- Per-type: structured→regex; names/patronymics→NER+LLM review; addresses→gazetteer+
  NER+LLM; dates/ages→regex+contextual; employer/school/clinic→NER+LLM quasi;
  family-role graph→LLM inference; trauma/migration/rare-dx→LLM+attacker sim;
  all-mentions→coreference/entity-ID; RU↔EN code-switch→layered multilingual+rules.

## 6. Methodology cheat-sheet (what to adopt)
- **Schema:** char offsets + entity_type (fine-grained) + identifier_type
  (DIRECT/QUASI/NO_MASK) + **confidential_status** + entity_id + **speaker_turn_id**
  + language + **mask_decision** (MASK/GENERALIZE/KEEP/SURROGATE/REVIEW) +
  surrogate_constraints.
- **Scoring levels:** strict entity-F1 (micro+macro+per-type), relaxed overlap,
  token-level binary recall/F2 (primary privacy), type-aware micro+macro, TAB
  all-mention recall, direct/quasi split, over-redaction, reconstruction score.
- **Re-id axis:** quasi survival (+ combinations), LLM inference attack with
  **top-k attribute guesses**, fixed attack budget (model/prompt/attempts/knowledge),
  residual-risk class (low/med/high).
- **Utility axis:** therapy-summary preservation, risk/safety-signal preservation,
  speaker-role coherence, temporal coherence, concept preservation, surrogate
  consistency.
- **Splits/docs:** session/person/template-disjoint splits; Datasheet + Data
  Statement; double-annotation + arbitration (IAA); published guidelines; HIPAA/GDPR
  mapping with explicit "not compliance" disclaimer; PHI/consent norms for any real
  data.

## 7. Novelty verdict
Real white space. **Safe wording:** "To our knowledge, CONFIDE-Bench is the first public
RU+EN synthetic psychotherapy-transcript de-identification benchmark combining
layered detector ablation, direct/quasi identifier scoring, all-mention recall, and
re-identification/utility evaluation." Do **not** claim "first therapy PII dataset
ever" or legal anonymization/compliance.

## 8. P0/P1/P2 roadmap (verbatim priorities)
**P0 (before release):** TAB schema fields (direct/quasi/no-mask, entity_id,
confidential_status, mask_decision); strict+relaxed+token+micro/macro+F2+direct/quasi
dashboards; all-mention recall; **session/person/template-disjoint splits**;
**double annotation + arbitration (IAA) on a seed set**; baseline ablations (have);
vendor-claim separation (have); license/use card.
**P1 (first paper/leaderboard):** LLM inference attack + top-k reconstruction;
quasi-combination scoring; task-specific utility tests; **RU adversarial suite**
(patronymics, inflection, transliteration, VK/Telegram, SNILS/INN, address abbrev,
mixed scripts); dialogue stress tests (cross-turn, nicknames); surrogate generation;
cloud/vendor baselines where permitted.
**P2 (defensibility):** small consented/paraphrased real therapy sample; human
therapist utility study; population-uniqueness risk modeling; multilingual extension
(UK/DE/ES); TAB/Tau-compatible harness; external red-team.

## 9. Recommended benchmark definition
"CONFIDE-Bench is a bilingual Russian-English synthetic psychotherapy-transcript
benchmark for text de-identification and residual re-identification risk. It contains
span-level direct and quasi-identifier annotations, entity-level coreference,
speaker-turn metadata, and masking decisions. We evaluate layered systems (regex,
Russian NER, open-weight privacy filters, local LLMs) using strict and relaxed entity
metrics, token-level recall/F2, type-aware micro/macro-F1, all-mention recall,
direct/quasi breakdowns, over-redaction, and LLM-based reconstruction attacks."

## 10. Bibliography (verify before citing)
Uzuner i2b2 2006/2007 · Stubbs et al. i2b2 2014 (JBI 2015) · Stubbs et al. N-GRID
2016/2017 · Dernoncourt et al. neural de-id 2016/17 · MIMIC-III/IV (PhysioNet) ·
MEDDOCAN (IberLEF 2019) · Pilán et al. TAB (CL 2022, DOI 10.1162/coli_a_00458) · Eder
et al. CodE Alltag (LREC 2020) · ai4privacy PII-Masking 200k/300k/2M · JayGuard 2025 ·
Hivetrace/raft-security-lab PII-Bench RU 2026 · MultiGraSCCo 2026 · MentalChat16K
2025 / CounseLLMe · MathEd-PII 2026 · RAT-Bench 2026 · Tau-Eval 2025 · Staab et al.
ICLR 2024/2025 · Presidio/Philter/OPF/AWS/Azure/GCP/JSL docs · Datasheets for Datasets
· Data Statements for NLP · HIPAA de-id guidance · GDPR Recital 26 / EDPB.

---

## Actionable deltas from review #2 (2026-06-01)

Review #2 confirms the novelty verdict and overlaps review #1. The genuinely NEW,
actionable items (not already in the roadmap above):

**Schema (fold into the TAB-schema work):**
- `person_role` per span — client / therapist / relative / third-party / institution
  (who is the *protected* person vs. a mentioned third party).
- `utility_tag` per span — clinically-important / narrative-context / low-utility.
- `mask_action` should include **GENERALIZE / PSEUDONYMIZE**, not just REDACT
  ("Berlin" → "large European city"; exact date → "early 2020s").

**Privacy axis:**
- Attacker must **cite evidence spans** from the surviving text for each guess
  (not just emit a guess) — strengthens the inference-attack credibility.
- **Cross-lingual attack** (RU text leaks via EN translation and vice versa). [P2]
- **Relation-level quasi-identifiers** ("my ex-wife's brother", "my daughter's
  school") as their own quasi class — the therapy social graph.

**Utility axis (expand beyond CBT-distortion preservation):**
- affect/emotion preservation, intervention/technique preservation, risk-context
  preservation, dialogue-coherence (speaker turns/references still followable).

**Robustness:**
- **Noisy-transcript condition** — ASR errors, lost punctuation, speaker-label
  errors (therapy data is dialogue/speech, not clean notes). A sibling of the
  RU-adversarial probe.

**Surrogate consistency [P2]:** "Anna" / "my sister" / "she" → one consistent
pseudonym, for longitudinal pseudonymization.

**Extra adjacent dataset:** CUEMPATHY (156 counseling sessions, 39 dyads) — another
"therapy data exists but no PII benchmark" data point.

Acting on now (within the before-publishable goal): person_role, utility_tag,
GENERALIZE/PSEUDONYMIZE mask_action (schema); attacker evidence-spans (privacy).
Deferred to P2: cross-lingual attack, surrogate consistency, noisy-transcript
condition, relation-level quasi class.
