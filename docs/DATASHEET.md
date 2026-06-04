# Datasheet & Data Statement — CONFIDE-Bench

Documentation for the **CONFIDE-Bench** bilingual (RU/EN) synthetic psychotherapy-transcript
de-identification benchmark, following *Datasheets for Datasets* (Gebru et al., 2021)
and *Data Statements for NLP* (Bender & Friedman, 2018). See `BENCHMARK.md` for results
and `SOURCES.md` for checked source links. `RESEARCH-FINDINGS.md` is a working
positioning memo and is explicitly marked needs-verification.

> **Not a compliance instrument.** Benchmark performance is **not** HIPAA or GDPR
> anonymisation certification. Types map loosely to HIPAA Safe-Harbor / GDPR identifier
> concepts for orientation only.

---

## Part A — Datasheet (Gebru et al.)

### 1. Motivation
- **Purpose.** Measure how well a local, privacy-first anonymization stack (regex +
  Russian NER + OpenAI Privacy Filter + local qwen LLM) redacts PII from psychotherapy
  session transcripts, and quantify which detector layer earns its compute — especially
  which PII types *require* an LLM. Secondary: residual re-identification risk and
  downstream clinical utility after redaction.
- **Gap addressed.** No public psychotherapy-*dialogue* de-identification benchmark
  exists, and Russian PII/de-id resources are thin (see `RESEARCH-FINDINGS.md` §3).
- **Created by / for.** Built for the Psychodemia 2026 masterclass.

### 2. Composition
- **Instances.** Four public runnable datasets plus one optional local-only dataset:
  - **RU-synth** — 30 synthetic Russian therapy sessions (6 fictional clients × 5),
    1,058 gold PII mention-spans (v2, post-IAA adjudication).
  - **RU-adversarial** — 16 short Russian snippets, 20 spans, probing hard forms
    (patronymics, transliteration, handles, SNILS/INN/passport, code-switching).
  - **EN-synth** — 32 curated English therapy-style snippets, 46 spans.
  - **EN-real (optional local)** — small slice of `ai4privacy/pii-masking-300k`
    (English validation; real, generic; in-distribution sanity check). **Not
    redistributed** (ai4privacy license): gold, detector caches, and result artifacts
    are local-only and gitignored. Build it locally with
    `python -m confide_eval.data.fetch_ai4privacy` only if you have rights to use it.
  - **RU-real (JayGuard)** — 60-doc slice of `just-ai/jayguard-ner-benchmark` (Just AI),
    77 spans of **real, anonymized conversational Russian** (NOT therapy).
    **License Apache-2.0** — redistribution permitted with attribution, so the
    **source text IS committed** (`data/sessions-ru-real/jayguard-ru.jsonl`).
    Gold is **machine-derived** from JayGuard's BIO labels (NOT human-adjudicated);
    **PERSON/LOCATION only** (JayGuard excludes phone/email/financial/medication/date).
    Reproduce: `python -m confide_eval.data.build_jayguard_ru_real --limit 60`.
    Attribution: *Jay Guard NER Benchmark*, Just AI, 2025, Hugging Face Datasets.
- **Label taxonomy (canonical).** PERSON, LOCATION, ORG, PHONE, EMAIL, URL, ID, DATE,
  MEDICATION, AGE, PROFESSION. Each RU span also carries: `identifier_class`
  (direct/quasi, TAB), `entity_id` (coreference grouping), `llm_required`,
  `person_role` (client/partner/relative/clinician/third_party/institution),
  `confidential_status`, `mask_decision` (MASK/GENERALIZE), `utility_tag`,
  `speaker_turn_id`/`speaker`, and `adjudicated` (v2 additions).
- **Real vs synthetic.** RU and EN-synth are **fully fictional** — no real patients.
  Optional local EN-real is real generic PII text (ai4privacy), not therapy. RU-real (JayGuard) is
  real *anonymized* conversational RU text, not therapy — a real-TEXT RU proxy.
- **Sensitive content.** Simulated mental-health disclosures (anxiety, perfectionism,
  family conflict). Fictional, but written to read as clinically plausible.
- **Splits.** Person-disjoint: RU clients a/c/e = `dev` (15 docs, 526 spans);
  clients b/d/f = `test` (15 docs, 532 spans).
- **Errors/noise.** Small N — per-type numbers are directional. Gold is located from
  answer-key surface forms then hand-verified; the seed LLM-assisted consistency check
  reports entity-F1 0.880 / κ 0.794 versus a single automated second annotator, with
  10 candidate blind spots queued for adjudication. This is not human IAA.

### 3. Collection / generation process
- RU transcripts and their PII inventories were authored as masterclass demo material
  (the answer keys explicitly label themselves "planted signal, not exact ground truth").
- Gold spans are located programmatically (Cyrillic-morphology-aware regex over the raw
  transcripts) from six answer-key inventories, then hand-verified.
- EN-synth is curated; optional local EN-real is sampled from ai4privacy's published validation split.

### 4. Preprocessing / labeling
- No text normalization — detectors and gold operate on the raw transcript characters
  (including YAML frontmatter), so scoring matches the deployed redaction surface.
- Adjudication (v2): high-confidence IAA blind spots (spelled-out phone/policy, Latin
  name, quasi-professions, employer city) added with `adjudicated: true`; relative
  dates explicitly scoped out.

### 5. Uses
- **Intended.** De-identification tool/layer comparison; teaching; methodology research.
- **Out of scope.** Clinical decisions; treating synthetic content as real patient data;
  claiming legal anonymisation.
- **Impact of composition.** Synthetic-only means it benchmarks detector *behavior*, not
  population uniqueness or real conversational leakage — validate on consented real data
  before strong claims.

### 6. Distribution
- Synthetic RU/EN-synth: releasable for research/teaching with this datasheet. EN-real
  inherits ai4privacy's license; **its gold, caches, and results are NOT redistributed
  by this repo.** Users may build it locally under ai4privacy's own license via
  `python -m confide_eval.data.fetch_ai4privacy` (writes a gitignored
  `data/sessions-en/pii-eval-ai4privacy.jsonl`). Consult ai4privacy's dataset card
  before any redistribution. **RU-real (JayGuard)** is licensed **Apache-2.0**, which
  permits redistribution **with attribution** — so its source text IS committed
  (`data/sessions-ru-real/jayguard-ru.jsonl`), with attribution to **Just AI** in
  `data/sessions-ru-real/README.md`.

### 7. Maintenance
- Versioned in-repo (`data/sessions-ru/*.jsonl`, `src/confide_eval/`). v2 = post-IAA-adjudication. Detector
  caches carry manifests (code/docs sha) so stale results are detectable. Future work:
  full-corpus double annotation, citation verification (several 2026 preprints).

---

## Part B — Data Statement (Bender & Friedman)

- **Curation rationale.** Sessions were authored to exhibit realistic, clinically *messy*
  therapy dialogue (distortions on a clarity spectrum, an imperfect therapist, embedded
  PII spoken naturally) so a de-id stack is tested on dialogue, not clean clinical notes.
- **Language variety.** Russian (`ru-RU`) — colloquial therapy dialogue with morphology,
  patronymics, diminutives, transliteration and RU↔EN code-switching; English (`en-US/GB`)
  — curated therapy-style text, plus optional local generic ai4privacy text when built.
- **Speaker / author demographic.** Fictional clients: "client-a" (Марина, ~34,
  marketer), "client-b" (Игорь, ~41, backend developer), "client-c" (Алина, ~29,
  UX designer), "client-d" (Роман, ~45, entrepreneur), "client-e" (Вера, ~37,
  teacher), and "client-f" (Тимур, ~23, student-programmer). No real individuals;
  demographics are invented narrative scaffolding.
- **Annotator demographic / provenance.** A1 gold: pattern-derived from author-written
  answer keys, hand-verified by the benchmark author. A2 (IAA): independent zero-shot
  annotation by GPT-5 (via Codex), committed at `results/iaa-annotator2-seed.json`.
- **Speech situation.** Simulated 1:1 psychotherapy sessions (CBT-leaning), written text
  presented as session transcripts with timestamped turns (therapist Т / client К).
- **Text characteristics.** Turn-taking dialogue with self-disclosure, family/social-graph
  references, and narrative quasi-identifiers — the material that makes therapy text both
  useful and re-identifying.
- **Provenance appendix.** RU answer keys: `data/sessions-ru/client-{a..f}/ANSWER-KEY.md`.
  Optional local EN-real: `ai4privacy/pii-masking-300k` — not redistributed; build via
  `python -m confide_eval.data.fetch_ai4privacy`. Reconstruction/utility method: Staab et al.,
  RAT-Bench, Tau-Eval (see `RESEARCH-FINDINGS.md` §10; verify before citing).
