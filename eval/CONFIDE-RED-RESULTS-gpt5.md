# CONFIDE-Red — re-identification of anonymized transcripts

Attacker `gpt-5` via openai. Three GDPR Art-29 attacks (inference / singling-out / linkability) against the CONFIDE-redacted output. Synthetic data; attributes fabricated.

## 1. Inference attack (by prompt strategy — top-3 attribute recovery)

| Client | direct | reason | investigator | of | singled out? (illustrative) |
|---|--:|--:|--:|--:|---|
| a | 2 | 2 | 0 | 5 | no (50.1) |
| b | 3 | 3 | 4 | 5 | no (1.7) |
| c | 4 | 4 | 5 | 5 | no (33.4) |
| d | 4 | 4 | 4 | 5 | no (62.6) |
| e | 4 | 2 | 4 | 5 | no (5256.0) |
| f | 4 | 4 | 4 | 5 | no (83.4) |

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

## 3. Linkability

Same-client pair judged same person: **True**; different-client pair judged same: **False**; → linkable: **True**.

_Prompt-strategy spread shows which framing the anonymizer is least robust to. Rising recovery + singling-out + linkability are the three ways therapy de-id fails after the names are gone._
