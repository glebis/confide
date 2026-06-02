# CONFIDE — Harm taxonomy for therapy de-identification

Not all leaks are equal. A benchmark that treats a leaked **email** the same as a leaked
**"my therapist for my HIV diagnosis is Dr. X in [small town]"** is measuring the wrong
thing for *therapy*. This is a **qualitative** severity model (clinical judgment, not a
formula) to mark what actually damages people, so de-identification and CONFIDE-Red can
prioritise it.

> Qualitative by design. These are starting points for **clinician review**, not fixed
> weights. Severity is contextual — the same fact is low-harm for one client and
> catastrophic for another.

## Two axes (why a single number misleads)

Every piece of information has **two independent properties**:

- **Re-identification power (linkability):** how directly it points to a specific real
  person. An email/phone is *maximal* here.
- **Disclosure sensitivity (damage):** how much harm exposure does *to the person* —
  stigma, discrimination, danger, re-traumatization. The *content* of a session.

The dangerous cases are **high on both**. Classic de-id tools optimise only the first
axis; therapy's worst leaks live on the second.

| | low sensitivity | high sensitivity |
|---|---|---|
| **high linkability** | email, phone (strong linker, low content-harm — and **rare in therapy speech**) | name + diagnosis/medication; abuser's name; address of someone fleeing abuse → **CRITICAL** |
| **low linkability** | generic small talk | trauma detail, orientation, substance use *without* a name (damaging if later linked via quasi-IDs) |

## Coarse severity levels (therapy context)

- **CRITICAL** — exposure can endanger or re-traumatize. Names of abusers/perpetrators;
  a survivor's location; identity + stigmatised/illegal/criminal disclosure; orientation
  or gender identity in a hostile context; identity + active suicidality; identity + HIV
  or other high-stigma diagnosis. *Often a quasi-identifier combined with a disclosure,
  not a classic identifier at all.*
- **HIGH** — stigma/discrimination if linked to the person. The **fact of being in
  mental-health treatment + a name**; a specific **diagnosis**; **medication** (implies a
  diagnosis); substance use; affair/relationship details; employer paired with a
  sensitive disclosure (job risk).
- **MEDIUM** — quasi-identifiers that re-identify *in combination*: rare **profession**,
  small **city/neighbourhood**, **age**, family structure, unusual life events, employer.
  Individually weak; the **singling-out** surface.
- **LOW** — strong but content-thin identifiers: **email, URL, phone, account/policy
  numbers**. Maximal linkers, but **uncommon in spoken therapy** and not damaging on their
  own. Still must be removed (they're direct links) — just not the *clinically* worst miss.

## How this maps to CONFIDE types

| CONFIDE type | Typical severity | Note for therapy |
|---|---|---|
| MEDICATION | **HIGH** | implies a diagnosis; high stigma |
| PERSON (third parties: abuser, affair, family) | **CRITICAL/HIGH** | a named third party + the disclosure about them |
| PERSON (the client) | HIGH | "is in therapy" is itself sensitive |
| LOCATION (small town / neighbourhood) | MEDIUM→HIGH | strong singling-out; CRITICAL if safety-relevant |
| PROFESSION / ORG (rare role, employer) | MEDIUM | combination risk + job consequences |
| AGE / DATE | MEDIUM | quasi-identifier; combines |
| EMAIL / PHONE / ID / URL | LOW (linkability HIGH) | rare in therapy speech; remove, but not the worst clinical miss |
| (no CONFIDE type yet) **sensitive disclosure** | CRITICAL/HIGH | trauma, orientation, substance use, legal issues — *content*, not an identifier; a candidate new layer |

## What this changes in CONFIDE

1. **Harm-weighted recall (optional reporting).** Alongside plain recall, report recall
   weighted by severity — a missed CRITICAL/HIGH item counts more than a missed email.
   Plain recall over-rewards catching cheap, frequent identifiers.
2. **Schema field.** Gold spans can carry a qualitative `harm` level (low/medium/high/
   critical) for clinician review (pairs with the existing `confidential_status`).
3. **CONFIDE-Red targets the worst first.** The attack suite should prioritise HIGH/
   CRITICAL attributes (medication→diagnosis, abuser names, locations) over LOW ones.
4. **A gap worth naming.** The most damaging therapy leaks are often **sensitive
   disclosures** (trauma, orientation) that no PII type captures — a future "sensitive
   content" layer, flagged for human review rather than auto-redacted.

## Empirical check (RU corpus, 30 docs / 713 mentions)

`score_bench.py` now reports `harm_weighted_recall` (entities weighted by the levels
above) alongside plain `entity_recall`. The gap is the point:

| layer | entity recall | harm-weighted | Δ | reading |
|---|--:|--:|--:|---|
| regex | 0.355 | 0.262 | **−0.093** | catches cheap, low-harm tokens (email/ID/phone); misses damaging content |
| Natasha (NER) | 0.308 | 0.362 | **+0.054** | catches PERSON/LOCATION — the high-harm entities; weighting *rewards* it |
| full stack ★ | 0.701 | 0.659 | −0.042 | still leaks somewhat more *high*-harm than the headline recall implies |

Harm-weighting **reranks the layers by clinical priority**: optimise for token count and
you favour regex; optimise for harm and you favour NER + LLM. Plain recall alone would
have hidden this.

**One sentence:** in therapy, optimise de-identification for *harm × linkability*, not for
catching the most identifiers — and the worst miss is usually a stigmatised disclosure
tied to a quasi-identifier, not an email.
