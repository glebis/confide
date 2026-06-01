# CONFIDE-Red — re-identification of anonymized transcripts

Attacker `qwen2.5:3b` via ollama. Three GDPR Art-29 attacks (inference / singling-out / linkability) against the CONFIDE-redacted output. Synthetic data; attributes fabricated.

## 1. Inference attack (by prompt strategy — top-3 attribute recovery)

| Client | direct | reason | investigator | of | singled out? |
|---|--:|--:|--:|--:|---|
| a | 2 | 1 | 0 | 5 | no (104.3) |
| b | 1 | 1 | 2 | 5 | no (10428.6) |
| c | 1 | 0 | 1 | 5 | no (104.3) |
| d | 0 | 3 | 0 | 5 | no (104.3) |
| e | 0 | 0 | 0 | 5 | no (104.3) |
| f | 1 | 1 | 1 | 5 | **YES** (0.9) |

## 2. Singling-out

Deterministic k-anonymity over declared RU population priors (method demo): the surviving quasi-identifiers multiply to an expected matching-population count; below 1 ⇒ the redacted transcript still singles the person out.

## 3. Linkability

Same-client pair judged same person: **False**; different-client pair judged same: **False**; → linkable: **False**.

_Prompt-strategy spread shows which framing the anonymizer is least robust to. Rising recovery + singling-out + linkability are the three ways therapy de-id fails after the names are gone._
