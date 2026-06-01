# CONFIDE-Red — re-identification of anonymized transcripts

Attacker `gpt-5` via openai. Three GDPR Art-29 attacks (inference / singling-out / linkability) against the CONFIDE-redacted output. Synthetic data; attributes fabricated.

## 1. Inference attack (by prompt strategy — top-3 attribute recovery)

| Client | direct | reason | investigator | of | singled out? |
|---|--:|--:|--:|--:|---|
| a | 2 | 2 | 0 | 5 | no (104.3) |
| b | 3 | 3 | 4 | 5 | no (10428.6) |
| c | 4 | 4 | 5 | 5 | no (104.3) |
| d | 4 | 4 | 4 | 5 | no (104.3) |
| e | 4 | 2 | 4 | 5 | no (104.3) |
| f | 4 | 4 | 4 | 5 | **YES** (0.9) |

## 2. Singling-out

Deterministic k-anonymity over declared RU population priors (method demo): the surviving quasi-identifiers multiply to an expected matching-population count; below 1 ⇒ the redacted transcript still singles the person out.

## 3. Linkability

Same-client pair judged same person: **True**; different-client pair judged same: **False**; → linkable: **True**.

_Prompt-strategy spread shows which framing the anonymizer is least robust to. Rising recovery + singling-out + linkability are the three ways therapy de-id fails after the names are gone._
