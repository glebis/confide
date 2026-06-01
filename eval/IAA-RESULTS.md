# Inter-annotator agreement (IAA) — seed set

Seed: ru-a-s01, ru-b-s01 (the two densest sessions). **A1** = pattern-derived gold; **A2** = independent from-scratch annotation by GPT-5 (Codex), given only the transcript. This checks the gold against an independent annotator — the research/Codex P0 fix for the circular, pattern-derived gold.

## Agreement

- **Entity-level F1 (A2 vs A1): 0.782**  (precision 0.642 = A2 items matching gold; recall 1.000 = gold *entities* A2 also marked). Entity-level (gold mentions grouped by entity_id) to avoid per-occurrence inflation.
- **Character-level Cohen's κ: 0.666**  (substantial agreement)

| Doc | A1 entities | A2 items | A2 hit | A1 hit | κ |
|---|--:|--:|--:|--:|--:|
| ru-a-s01 | 14 | 28 | 21 | 14 | 0.66 |
| ru-b-s01 | 9 | 25 | 13 | 9 | 0.672 |

## Gold blind spots — A2 found, A1 (gold) missed

Candidate additions for adjudication. Notably the spelled-out identifiers and relative dates the pattern-derived gold cannot express:

- `ru-a-s01` **ID**: 'семь-семь-два-два, четыре-четыре-пять-пять, восемь-восемь-один-один'
- `ru-a-s01` **PHONE**: 'плюс семь, девять-один-шесть, пять-пять-пять, двадцать один, сорок три'
- `ru-a-s01` **DATE**: 'месяца три уже'
- `ru-a-s01` **PROFESSION**: 'младшего специалиста'
- `ru-a-s01` **DATE**: 'На той неделе'
- `ru-a-s01` **DATE**: 'в прошлый четверг'
- `ru-a-s01` **DATE**: 'через неделю'
- `ru-b-s01` **ID**: 'igor'
- `ru-b-s01` **LOCATION**: 'екатеринбургская'
- `ru-b-s01` **PROFESSION**: 'Бэкенд'
- `ru-b-s01` **PROFESSION**: 'Тимлид'
- `ru-b-s01` **DATE**: 'прошлой неделе'
- `ru-b-s01` **DATE**: 'в среду'
- `ru-b-s01` **DATE**: 'в пятницу'
- `ru-b-s01` **DATE**: 'Года три назад'
- `ru-b-s01` **DATE**: 'через неделю'
- `ru-b-s01` **LOCATION**: 'Екатеринбург'
- `ru-b-s01` **PROFESSION**: 'тимлид'
- `ru-b-s01` **DATE**: 'около трёх лет назад'

## A1-only — gold has, A2 missed


## Adjudication note

A2-only items are mostly (a) **spelled-out** phone/policy digits and (b) **relative dates** ("прошлой неделе", "года три назад") — real PII the regex/answer-key gold structurally omits. These should be adjudicated into a v2 gold (or explicitly scoped out). A1-only items are mostly morphological mentions A2 reported once. IAA here measures gold *completeness*, not just boundary agreement.

