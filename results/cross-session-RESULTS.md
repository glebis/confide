# Cross-session (longitudinal) re-identification

Attacker: `qwen2.5-3b-instruct` via openai. The same LLM infers client attributes from (A) ONE redacted session vs (B) ALL of the client's redacted sessions together. The **bulk − single** gain is the cross-session linkage risk that single-session de-id evaluation misses.

| Client | single-session best | **all-sessions (bulk)** | cross-session gain |
|---|--:|--:|--:|
| a | 2/6 | **1/6** | +-1 |
| b | 1/6 | **1/6** | +0 |

_A positive gain means accumulating quasi-identifiers across sessions let the attacker recover attributes no single session exposed — the longitudinal therapy de-identification risk. Synthetic data; attributes are fabricated._
