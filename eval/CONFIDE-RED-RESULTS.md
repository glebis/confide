# CONFIDE-Red — re-identification of anonymized transcripts

Attacker `qwen2.5:3b` via ollama. Three GDPR Art-29 attacks (inference / singling-out / linkability) against the CONFIDE-redacted output. Synthetic data; attributes fabricated.

## 1. Inference attack (by prompt strategy — top-3 attribute recovery)

| Client | direct | reason | investigator | of | singled out? (illustrative) |
|---|--:|--:|--:|--:|---|
| a | 2 | 1 | 0 | 5 | no (50.1) |
| b | 1 | 1 | 2 | 5 | no (1.7) |
| c | 1 | 0 | 1 | 5 | no (33.4) |
| d | 0 | 3 | 0 | 5 | no (62.6) |
| e | 0 | 0 | 0 | 5 | no (5256.0) |
| f | 1 | 1 | 1 | 5 | no (83.4) |

## 2. Singling-out — ILLUSTRATIVE

> **ILLUSTRATIVE / methodological demonstration, not a re-identification probability.** Computed by the shared `kanon` estimator (identical numbers to privacy-utility-RESULTS.md). Personas are synthetic, so this shows *how* a surviving quasi-identifier combination is assessed (GDPR Art-29 / k-anonymity), not a precise probability. The load-bearing signal is the **relative ranking** of exposure and the **sensitivity verdict**, not the point value.

_Naive product of per-quasi fractions assumes the quasi-identifiers are statistically independent. They are not (profession/city/age/medication correlate), so this OVERSTATES uniqueness — the real matching population is larger and the person is LESS singled out than the point estimate implies._

Entity-aware survivor detection (gold quasi entity left unmasked by the default stack) feeds one sourced prior table (`kanon.PRIORS`); the surviving fractions multiply to an expected matching-population count; below 1 would mean singling-out.

| Client | expected matches (illustrative) | dims used | singles out? | verdict robust to ±0.5x–2x priors? |
|---|--:|---|---|---|
| a | 50.1 | AGE, PROFESSION, MEDICATION | no | yes |
| b | 1.7 | AGE, LOCATION, MEDICATION, PROFESSION | no | **no (flips)** |
| c | 33.4 | AGE, MEDICATION, PROFESSION | no | yes |
| d | 62.6 | AGE, MEDICATION, PROFESSION | no | yes |
| e | 5256.0 | MEDICATION, PROFESSION | no | yes |
| f | 83.4 | AGE, MEDICATION, PROFESSION | no | yes |

## 3. Linkability (full pair-matrix benchmark)

Anonymeter framing: given two REDACTED sessions, can the attacker tell whether they belong to the SAME client? Over 30 redacted docs we score **100 pairs** (60 SAME, 40 DIFFERENT). DIFFERENT pairs are deterministically strided (stride 5; 335 of 375 dropped — no RNG, no silent truncation). Attacker `qwen/qwen3-32b` via openai, SAME = positive class.

| metric | value | 95% CI (bootstrap, 2000×) |
|---|--:|---|
| accuracy | 0.500 | 0.410–0.600 |
| ROC-AUC | 0.458 | 0.376–0.544 |
| precision (SAME) | 1.000 | — |
| recall (SAME) | 0.167 | — |
| F1 (SAME) | 0.286 | — |
| base rate P(SAME) | 0.600 | — |
| majority-class accuracy | 0.600 | — |

Confusion matrix (rows = truth, cols = attacker verdict):

| | called SAME | called DIFFERENT |
|---|--:|--:|
| **truth SAME** | 10 (TP) | 50 (FN) |
| **truth DIFFERENT** | 0 (FP) | 40 (TN) |

> **Mechanism (read the AUC honestly):** No cleartext `client_id` detected in the redacted docs; the score reflects content-based linkability. **Before the T8 leak fix this AUC was 1.000** — but that was an artifact: 28/30 redacted sessions leaked a cleartext YAML `client_id` (a per-client first name, a CONSTANT direct identifier the regex/NER/LLM layers never saw), so "linking" was a trivial exact-string match, not inference. The frontmatter recognizer (`anonymize.run_frontmatter`) now masks that value (`leaked_client_id_docs` 28→0). With the direct leak removed, AUC collapses to **0.458** (CI overlaps 0.5) and accuracy to **0.500** (below the 0.600 majority baseline): the attacker is at chance. Recall 0.167 with precision 1.000 shows it almost never confidently asserts SAME, and the AUC confirms it cannot rank SAME pairs above DIFFERENT ones from surviving stylometry / quasi-identifiers alone.

**Verdict:** **Redaction defeats cross-session linkability at this scale** — the attacker does not beat chance (accuracy CI overlaps the majority-class baseline and AUC CI overlaps 0.5). The earlier "perfect" linkage was a metadata-leak artifact, now fixed.

_Prompt-strategy spread shows which framing the anonymizer is least robust to. Rising recovery + singling-out + linkability are the three ways therapy de-id fails after the names are gone._
