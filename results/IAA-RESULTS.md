# LLM-assisted consistency check (single second-annotator) — seed set

**This is NOT human inter-annotator agreement.** It is an *LLM-assisted consistency check* with a single, automated second annotator (per Codex audit R4). A human multi-annotator study with adjudication is still required before any publishable agreement claim; the numbers below only flag where the pattern-derived gold and an independent LLM pass disagree.

Seed: ru-a-s01, ru-b-s01 (the two densest sessions). **A1** = pattern-derived gold; **A2** = independent from-scratch annotation by GPT-5 (Codex), given only the transcript. This checks the gold against one independent automated annotator — the research/Codex P0 probe for the circular, pattern-derived gold.

## Consistency (A2 vs A1)

- **Entity-level F1 (A2 vs A1): 0.880**  (precision 0.808 = A2 items matching gold; recall 0.967 = gold *entities* A2 also marked). Entity-level (gold mentions grouped by entity_id) to avoid per-occurrence inflation.
- **Character-level Cohen's κ: 0.794**  (substantial consistency vs the single LLM second-annotator — not a human-agreement κ)

| Doc | A1 entities | A2 items | A2 hit | A1 hit | κ |
|---|--:|--:|--:|--:|--:|
| ru-a-s01 | 17 | 28 | 24 | 17 | 0.828 |
| ru-b-s01 | 13 | 24 | 18 | 12 | 0.761 |

## Gold blind spots — A2 found, A1 (gold) missed

Candidate additions for adjudication. Notably the spelled-out identifiers and relative dates the pattern-derived gold cannot express:

- `ru-a-s01` **DATE**: 'месяца три уже'
- `ru-a-s01` **DATE**: 'На той неделе'
- `ru-a-s01` **DATE**: 'в прошлый четверг'
- `ru-a-s01` **DATE**: 'через неделю'
- `ru-b-s01` **DATE**: 'прошлой неделе'
- `ru-b-s01` **DATE**: 'в среду'
- `ru-b-s01` **DATE**: 'в пятницу'
- `ru-b-s01` **DATE**: 'Года три назад'
- `ru-b-s01` **DATE**: 'через неделю'
- `ru-b-s01` **DATE**: 'около трёх лет назад'

## A1-only — gold has, A2 missed

- `ru-b-s01` **LOCATION**: 'Заволжский'

## Adjudication note

A2-only items are mostly (a) **spelled-out** phone/policy digits and (b) **relative dates** ("прошлой неделе", "года три назад") — real PII the regex/answer-key gold structurally omits. These should be adjudicated into a v2 gold (or explicitly scoped out). A1-only items are mostly morphological mentions A2 reported once. IAA here measures gold *completeness*, not just boundary agreement.

