# Deep-Research Prompt — De-identification Benchmarks, Methods & Datasets

> Paste the block below into a deep-research agent (Claude/ChatGPT/Gemini deep research,
> or the local `deep-research` skill). It is written to position and strengthen
> **CONFIDE-Bench** — a bilingual (Russian + English) synthetic **psychotherapy-transcript**
> de-identification benchmark that scores a *layered detector ablation* (regex +
> NER + OpenAI Privacy Filter + local LLM) with recall-first, entity-level (TAB),
> direct/quasi-identifier, and re-identification-risk metrics.

---

## ROLE
You are a research analyst specializing in NLP privacy, de-identification, and
text anonymization. Produce a rigorous, citation-backed survey that I can use to
(a) position a new benchmark against prior art, (b) adopt the strongest evaluation
methodology, and (c) decide what to add next.

## CONTEXT (the benchmark this research serves)
CONFIDE-Bench evaluates how well a *local, privacy-first* anonymization stack redacts
PII from therapy session transcripts. Detector layers: deterministic regex
(emails/URLs/phones/IDs/dates via scrubadub + libphonenumber), Russian NER
(Natasha), the OpenAI Privacy Filter (transformers NER), and a local LLM (qwen via
Ollama). Combinations are composed by span-union → merged redaction mask. Gold is
located from answer-key PII inventories (a "planted-signal recovery" eval, not yet
independently annotated). Metrics: coverage recall/F2 (relaxed + strict), type-aware
micro/macro-F1, TAB-style entity-level recall (all mentions masked), direct vs
quasi-identifier split, plus a reconstruction axis (quasi-identifier survival, an
LLM inference attack on redacted text, over-redaction/utility cost).

## RESEARCH QUESTIONS (answer each, with sources)

### A. Benchmarks & corpora
1. Catalogue the major **text de-identification / anonymization benchmarks and
   corpora**: TAB (Text Anonymization Benchmark), i2b2/n2c2 2006/2014/2016
   de-identification tracks, ai4privacy PII-Masking-200k/300k/2M, PHEE, MIMIC-based
   de-id sets, CodE Alltag/German, Spanish MEDDOCAN, and any 2023–2026 additions
   (RAT-Bench, Tau-Eval, MathEd-PII, and others). For each: domain, language(s),
   size, label taxonomy, real vs synthetic, license, and the official metric.
2. Which benchmarks target **conversational / dialogue / counseling / mental-health**
   text specifically (vs. clinical notes or generic web text)? Is there ANY
   psychotherapy-transcript de-identification benchmark? (Check MentalChat16K,
   counseling datasets, tutoring dialogue de-id.)
3. What exists for **Russian-language** PII detection / de-identification (datasets,
   NER for PII, Natasha/DeepPavlov/SpaCy-ru, any RU clinical or conversational sets)?

### B. Methods & systems
4. Survey de-identification **method families**: rule/regex, CRF/feature-based,
   neural NER (BiLSTM-CRF, BERT/transformer token classification), and **LLM-based**
   anonymizers (prompted, fine-tuned, agentic). What does the evidence say about
   **hybrid / layered / ensemble** systems (the CONFIDE-Bench premise)? Quantify where
   each family wins/loses by PII type.
5. How do leading tools compare — **Microsoft Presidio**, OpenAI Privacy Filter,
   Philter, spaCy/Stanza pipelines, commercial (AWS Comprehend Medical, Azure,
   Google DLP, John Snow Labs)? Note multilingual coverage and quasi-identifier
   handling.

### C. Evaluation methodology (most important)
6. Compare **scoring conventions**: entity- vs token- vs mention-level; strict vs
   relaxed/partial spans; micro vs macro; recall-weighting (why F2 / recall-first in
   de-id); binary "PHI vs not" tracks. Cite how TAB and i2b2/n2c2 each define a
   "protected" entity and how they handle coreference (all-mentions-masked).
7. **Direct vs quasi-identifier** treatment and **re-identification-risk** evaluation:
   how do TAB, RAT-Bench, Tau-Eval, and Staab et al. ("Beyond Memorization", LLM
   attribute inference) measure privacy as *attacker success* rather than detector
   recall? What attacker protocols, background-knowledge assumptions, and
   k-anonymity / singling-out / linkage metrics are standard?
8. **Privacy–utility tradeoff**: standard ways to measure utility loss /
   over-redaction and downstream-task preservation after de-identification.
9. **Dataset documentation & rigor norms** for a *publishable* benchmark: Datasheets
   for Datasets, Data Statements for NLP, inter-annotator agreement (κ/F1),
   train/dev/test splits, adjudicated gold, HIPAA-18 / GDPR identifier taxonomies.

### D. Positioning & gaps
10. Given all the above, where are the **white spaces**? Specifically assess the
    novelty of: (i) therapy-*dialogue* domain, (ii) Russian therapy de-id, (iii) a
    *layered-detector ablation* framing, (iv) integrating reconstruction/re-id risk +
    utility into one harness. What would a reviewer say is missing or already done?
11. Recommend a **prioritized list of concrete additions** to CONFIDE-Bench drawn from
    the strongest prior art (metrics, attacker protocols, taxonomy, splits, IAA,
    multilingual extension via ai4privacy real slices for DE/FR/ES/IT/NL).

## SOURCE & QUALITY REQUIREMENTS
- Prefer peer-reviewed venues (ACL/EMNLP/NAACL/COLING, *Computational Linguistics*,
  JAMIA/JBI, NeurIPS Datasets & Benchmarks) and primary dataset cards; include arXiv
  with dates. Give a direct link/DOI and year for every claim.
- Distinguish **vendor/model-card claims** from independent measurements.
- Flag retracted, non-reproducible, or AI-generated "slop" sources.
- Note licenses and any PHI/consent constraints for each dataset.

## OUTPUT FORMAT
1. **Executive summary** (≤250 words): the landscape and where CONFIDE-Bench fits.
2. **Comparison table** of benchmarks: name | domain | language(s) | size | taxonomy |
   real/synthetic | metric | license | link.
3. **Methods synthesis** with a per-PII-type "which family wins" table.
4. **Methodology cheat-sheet**: the recommended scoring + re-identification + utility
   protocol, with citations.
5. **Gap analysis & novelty verdict** for CONFIDE-Bench (honest, reviewer's-eye).
6. **Prioritized adoption roadmap** (P0/P1/P2) of additions, each tagged with its
   source benchmark.
7. **Annotated bibliography** (grouped: benchmarks, methods, re-identification,
   documentation standards).
