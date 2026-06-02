# Core Sources Checked for Publishing

This file records the primary or near-primary sources used for the publishable
methodology claims. `RESEARCH-FINDINGS.md` remains a working literature map and should
not be treated as fully verified until each row has a source URL.

## De-identification Benchmarks and Scoring

- Pilán et al. (2022), **The Text Anonymization Benchmark (TAB)**:
  <https://aclanthology.org/2022.cl-4.19/>
  - Supports direct vs quasi vs no-mask identifiers, confidential attributes,
    entity IDs/coreference, and entity-level recall where an entity is protected only
    if all mentions are masked.
- Stubbs, Kotfila, and Uzuner (2015), **2014 i2b2/UTHealth de-identification shared
  task Track 1**:
  <https://pubmed.ncbi.nlm.nih.gov/26225918/>
  - Supports strict entity-based evaluation and the reported top strict micro-F1
    of 0.936 for the 2014 clinical de-identification shared task.
- Stubbs, Filannino, and Uzuner (2017), **2016 CEGS N-GRID psychiatric intake
  de-identification task**:
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC5705537/>
  - Supports the psychiatric-intake-note comparison point, 1,000-record corpus,
    and top F1 values around 0.799 sight-unseen and 0.914 trained.
- MEDDOCAN / SPACCC_MEDDOCAN:
  <https://github.com/PlanTL-GOB-ES/SPACCC_MEDDOCAN>
  - Supports the Spanish synthetic clinical-case de-identification benchmark,
    1,000 cases, and 29 granular entity types.

## Privacy Filter and Dataset Claims

- OpenAI Privacy Filter model card:
  <https://huggingface.co/openai/privacy-filter>
  - Supports the model purpose, vendor PII-Masking-300k metrics, and limitation
    language.

## Re-identification / Residual-Risk Framing

- GDPR Recital 26:
  <https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng>
  - Supports the "reasonably likely means" and singling-out framing for
    identifiability.
- European Data Protection Board SME guide, anonymisation examples:
  <https://www.edpb.europa.eu/sme-data-protection-guide/secure-personal-data_en>
  - Supports the singling-out, linkability, and inference examples.
- Giomi et al. (2022), **Anonymeter**:
  <https://arxiv.org/abs/2211.10459>
  - Supports attack-based evaluation of singling-out, linkability, and inference.
- RAT-Bench preprint:
  <https://openreview.net/pdf?id=FjbU4kLriN>
  - Supports the emerging attacker-based benchmark framing and the cited residual
    re-identification rates for some anonymizers. Treat as preprint evidence, not
    settled literature.

## Documentation Standards

- Gebru et al. (2021), **Datasheets for Datasets**:
  <https://www.microsoft.com/en-us/research/publication/datasheets-for-datasets/>
- Bender and Friedman (2018), **Data Statements for Natural Language Processing**:
  <https://aclanthology.org/Q18-1041/>
