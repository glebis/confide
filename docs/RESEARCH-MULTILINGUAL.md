# Multilingual Dataset Survey — EN(additional) / DE / FR / ES

> Produced by four parallel research agents (2026-06-01) to extend `RESEARCH-FINDINGS.md`
> for additional English datasets and a future DE/FR/ES extension. **Verify all sources
> before citing** — several are 2025–2026 preprints or vendor cards. Provenance: web search.

## Headline
There is **no public therapy/counseling-dialogue de-identification corpus with PII spans
in English, German, French, or Spanish.** Each language has clinical-note de-id corpora,
generic NER, and synthetic multilingual PII sets — but the therapy-*dialogue* + PII-span
combination is an open gap everywhere. This confirms and extends CONFIDE-Bench's novelty and
makes a multilingual extension a clear contribution.

## English — additional (beyond TAB/i2b2/ai4privacy/MathEd/etc.)
- **SPY** (NAACL-SRW 2025) — medical-dialogue, fine-grained-PII-vs-NER, placeholder+Faker
  generation. *Best methodological precedent for CONFIDE-Bench.* HF `mks-logic/SPY`.
- **ASQ-PHI** (Data in Brief 2026) — 1,051 synthetic clinical LLM queries, 13 HIPAA
  Safe-Harbor types; "safe handoff before leaving the boundary" framing.
- **CRAPII / PIILO** (Learning Agency Lab 2024) — real, human-annotated student essays
  (first-person narrative ≈ client self-disclosure); spaCy-JSON span format.
- **PANORAMA** (arXiv 2505.12238) — 384k profile-consistent synthetic posts; cross-document
  linkage risk (≈ multi-session client).
- **Nemotron-PII** (NVIDIA, CC-BY-4.0) / **Gretel finance multilingual** / **rungalileo/pii**
  — large synthetic span-level PII; *vendor cards* (taxonomy-mapping anchors, not indep. eval).
- **PII-Bench** (arXiv 2502.18545) — 55 fine-grained subtypes, multi-party scenarios.
- **LLM-PBE** (VLDB 2024) / **PII-Scope** (IJCNLP 2025) — privacy-attack/leakage benchmarks
  (downstream-risk axis beyond span-F1).
- **Counseling & Psychotherapy Transcripts** (Alexander Street) — the only large *real* English
  therapy-transcript corpus, but paywalled and **no gold PII spans** (realism check only).
- Name-collision caution: "PII-Bench" reused by multiple efforts.

## German
- **GraSCCoPHI / GeMTeX** — only *freely shareable* German clinical PHI gold (α≈0.97); emerging
  German de-id standard. Adopt taxonomy + substitution policy.
- **3000PA** — highest-quality *real* German clinical PHI (F1 0.96) but **not shareable**.
- **CodE Alltag 2.0** (LREC 2020) — 1.47M real German emails, pseudonymized gold subset; closest
  register to therapy (first-person, dialogic). *Best non-clinical reuse.*
- **ai4privacy OpenPII (de)** — out-of-the-box German IBAN/address/phone/email spans (synthetic).
- Gaps: **Steuer-ID / KV-Nummer** poorly covered; German compound-word/inflected names are the
  hardest de-id challenge.

## French
- **PARHAF** (arXiv 2603.20494, CC-BY-4.0) — large *synthetic, shareable* French clinical reports;
  ideal substrate to inject synthetic French PII. *Best French base.*
- **AP-HP CDW corpus** — real, 12 entities incl. **NIR**/hospital/visit IDs, F1 0.99; **not
  shareable** (reuse taxonomy + method).
- **MultiGraSCCo** (arXiv 2603.08879, CC-BY-4.0) — cross-lingual incl. French; **19 PHI + 13
  indirect identifiers** (quasi-IDs matter for therapy). Closest comparator/method template.
- **TypicaAI/pii-masking-60k_fr** — best French-only generic PII (synthetic; no NIR/SIREN).
- Gaps: **NIR, SIREN/SIRET, INSEE-coded addresses** unlabeled in any public set → differentiator.

## Spanish
- **CARMEN-I** (PhysioNet, Nature Sci Data 2024/25) — real bilingual **ES+CA** EHR de-id, 28 PHI
  types, dual mask/replace (= CONFIDE-Bench pattern). *Strongest real Spanish resource* (DUA-gated).
- **MEDDOCAN** (IberLEF 2019, CC-BY-4.0) — canonical Spanish clinical de-id, 22 categories.
- **MIDAS** (NAACL 2025) — real Spanish **motivational-interviewing counseling** dialogue (ES+LatAm),
  74 sessions — **no PII labels** but the closest genre; best seed for a Spanish therapy-PII pilot.
- **ai4privacy (es + mx locales)** — only set with explicit ES+MX, ID/TAX/SOCIAL slots (synthetic).
- Gaps: **DNI/NIE/NSS (ES), CURP/RFC (MX)** unvalidated; clinical corpora are all European Spanish.
- Note: **MultiGraSCCo excludes Spanish**.

## Implications for CONFIDE-Bench
- **Taxonomy alignment:** map our canonical types to MEDDOCAN(22)/AP-HP(12)/GraSCCoPHI/HIPAA-18
  for cross-corpus comparability; adopt MultiGraSCCo's **indirect-identifier** schema for quasi-IDs.
- **Extension recipe per language:** reuse a shareable synthetic clinical base (PARHAF/GraSCCo) or
  a counseling-dialogue seed (MIDAS) + inject locale-specific structured IDs (NIR, Steuer-ID,
  DNI/NIE/CURP) that no public set labels — a concrete contribution.
- **Downstream-risk axis:** cite LLM-PBE / PII-Scope / Staab for attacker-based evaluation.
- **Realism check:** Alexander Street (EN) / CodE Alltag (DE) / MIDAS (ES) as register anchors.

---

## Run-2 additions (2026-06-01, second parallel sweep — new items only)

**English (new):**
- **Reddit Self-Disclosure** (Dou et al., ACL 2024) — 2.4K posts / 4.8K spans, **19 categories
  of disclosed experiences + attributes** and an explicit *abstraction* (rephrase-to-preserve)
  task. The single most therapy-relevant taxonomy found; real, HF `douy/reddit-self-disclosure`.
- **WildChat-4.8M** (AI2) — real human–LLM dialogue, already Presidio-de-id'd; conversational
  PII-pattern + pipeline reference.
- **CanaryBench** *(preprint 2601.18834)* — PII leakage in conversation **summaries** (the exact
  session-note artifact); canary/regex leakage checks.
- **JobStack** (NoDaLiDa 2021) — 22K job-posting sentences; Profession/Organization entities
  (work-context disclosures), real & open.
- BRATsynthetic / Transformer-DeID (PhysioNet) — surrogate-substitution + reproducible baselines.

**German (new):** **Open Legal Data** (104K court decisions, court-anonymized, on HF) — real
quasi-identifier patterns; **USENIX 2023** (Deuber et al.) shows initials/role-replacement are
re-identifiable → direct evidence for the direct/quasi design. **CARDIO:DE** (500 cardiology
letters, DUA), **BRONCO150** (oncology, DUA) as real clinical de-id references.

**French (new):** **eHOP/Rennes** clinical de-id (8 HIPAA-like cats, F1 0.97; RGPD-locked but
taxonomy reusable, PMC10870625); **Etalab `pseudo_conseil_etat` / Cour de cassation** — MIT
open-source legal pseudonymisation tooling (Flair); **88milSMS** — 90K real anonymised SMS
(conversational register, closest to therapy-chat informality).

**Spanish (new):** **MEDDOPLACE** (geographic PHI, Zenodo), **SPACCC** (parent corpus, open),
**Chilean Waiting List Corpus** (LatAm, nested entities), **MAPA** (open Spanish legal
anonymisation NERC). Confirms CARMEN-I as the strongest real post-MEDDOCAN resource.

**Cross-language tooling/needs (concrete):** NER exists everywhere (spaCy/Flair/clinical-BERT per
lang); the universal gap is **locale structured-ID regex** — DE: Steuer-IdNr/SV-Nr/KV-Nr/DE-IBAN;
FR: NIR/SIREN-SIRET/INSEE; ES: DNI/NIE/NSS/CIF **+ LatAm** RUT/CURP/RFC/CUIL — none built into
default Presidio. And **no language has usable real therapy de-id data** → synthetic generation
(the CONFIDE-Bench approach) is the only path in every language.
