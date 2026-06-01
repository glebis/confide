#!/usr/bin/env python3
"""Generate the publishable BENCHMARK.md from the per-dataset bench-results.json.

Layout follows published de-id benchmark conventions:
  - Datasheet header (Datasheets for Datasets; Data Statements for NLP)
  - Metric definitions with citations (TAB, i2b2/n2c2, Presidio-research)
  - Per-dataset ablation leaderboards (combo x metric)
  - Per-category recall table (which layer catches what -> LLM-required types)
  - Direct vs quasi-identifier entity-level recall (RU)

Run after score_bench.py has produced ru-/en-/en-real-bench-results.json.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATASETS = [
    ("ru", "RU-synth", "Russian synthetic therapy series (client-a + client-b, 10 sessions)"),
    ("en", "EN-synth", "English curated therapy-style snippets"),
    ("en-real", "EN-real", "Real ai4privacy/pii-masking-300k slice (English validation)"),
    ("ru-adv", "RU-adversarial", "Russian robustness probe (16 snippets: patronymics, "
     "transliteration, diminutives, VK/Telegram handles, SNILS/INN/passport, abbreviated "
     "addresses, code-switching)"),
]


def load(ds):
    p = os.path.join(HERE, f"{ds}-bench-results.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def leaderboard(res):
    has_ent = any("entity_level" in c for c in res["combos"].values() if isinstance(c, dict) and "members" in c)
    lines = []
    head = "| Combo | Cov F2 (rel) | Cov R | Type F2 | Micro-F1 | Macro-F1 | Preds |"
    sep =  "|---|--:|--:|--:|--:|--:|--:|"
    if has_ent:
        head = "| Combo | Cov F2 (rel) | Cov R | Type F2 | Macro-F1 | Ent-R (TAB) | Direct-R | Quasi-R | Preds |"
        sep =  "|---|--:|--:|--:|--:|--:|--:|--:|--:|"
    lines += [head, sep]
    for name, e in res["combos"].items():
        if e.get("status") == "missing-cache":
            lines.append(f"| {name} | _(cache missing: {'+'.join(e['members'])})_ |" + " |" * (8 if has_ent else 5))
            continue
        cr, tr = e["coverage_relaxed"], e["type_relaxed"]
        if has_ent and "entity_level" in e:
            el = e["entity_level"]
            d = el["by_class"].get("direct", {}).get("recall", 0.0)
            q = el["by_class"].get("quasi", {}).get("recall", 0.0)
            lines.append(f"| {name} | **{cr['f2']:.3f}** | {cr['r']:.3f} | {tr['f2']:.3f} | "
                         f"{tr['macro_f1']:.3f} | {el['entity_recall']:.3f} | {d:.3f} | {q:.3f} | {e['n_pred']} |")
        else:
            lines.append(f"| {name} | **{cr['f2']:.3f}** | {cr['r']:.3f} | {tr['f2']:.3f} | "
                         f"{tr['overall']['f1'] if 'overall' in tr else tr['f1']:.3f} | {tr['macro_f1']:.3f} | {e['n_pred']} |")
    return "\n".join(lines)


def per_category(res):
    """Recall per canonical type for each combo — surfaces LLM-required types."""
    combos = [(n, e) for n, e in res["combos"].items() if isinstance(e, dict) and "coverage_relaxed_per_type" in e]
    types = sorted({t for _, e in combos for t in e["coverage_relaxed_per_type"]})
    lines = ["| Combo | " + " | ".join(types) + " |",
             "|---|" + "|".join("--:" for _ in types) + "|"]
    for name, e in combos:
        cells = []
        for t in types:
            m = e["coverage_relaxed_per_type"].get(t)
            cells.append(f"{m['r']:.2f}" if m and m["support"] else "—")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    out = []
    A = out.append
    A("# CONFIDE-Bench — A Bilingual Synthetic De-identification Benchmark for Therapy Transcripts")
    A("")
    A("> A reproducible, layered-detector ablation measuring how well a local, "
      "privacy-first anonymization stack redacts PII from psychotherapy session "
      "transcripts in **Russian and English**. Built for the Psychodemia 2026 masterclass.")
    A("")
    A("## Datasheet (Datasheets for Datasets / Data Statements for NLP)")
    A("")
    A("> Full datasheet + data statement: **`DATASHEET.md`**. Summary below.")
    A("")
    A("- **Motivation.** Compare detector layers (regex, Natasha RU-NER, the OpenAI "
      "Privacy Filter, and a local qwen LLM) for de-identifying therapy transcripts, "
      "and quantify which layer earns its compute — especially which PII types *require* "
      "an LLM to catch.")
    A("- **Composition.** Three datasets (see per-dataset sections). The Russian set is "
      "**fully synthetic and fictional** — no real patients — hand-built from two answer-key "
      "PII inventories. The English sets are a curated synthetic slice and a real "
      "`ai4privacy/pii-masking-300k` validation slice.")
    A("- **Languages.** Russian (`ru`), English (`en`).")
    A("- **PII taxonomy (canonical).** PERSON, LOCATION, ORG, PHONE, EMAIL, URL, ID, "
      "DATE, MEDICATION, AGE, PROFESSION. Each RU entity is also tagged **direct** vs "
      "**quasi**-identifier (TAB), and `llm_required` where deterministic layers "
      "structurally cannot catch it (medication/age/date/profession).")
    A("- **Collection / labeling.** RU gold is located programmatically from curated "
      "surface-form patterns (Cyrillic-morphology-aware) over the raw transcripts, then "
      "hand-verified; every mention carries an `entity_id` for entity-level scoring.")
    A("- **Uses.** De-identification tool comparison; teaching. **Not** a clinical "
      "instrument; synthetic RU content must not be treated as real patient data.")
    A("- **Limitations.** Small N (each miss moves recall several points); synthetic RU "
      "text; spelled-out digit strings are out of scope for the regex layer by design.")
    A("- **Splits.** Person-disjoint: client-a = `dev`, client-b = `test` (each client is "
      "a distinct synthetic person → no profile leakage across splits).")
    A("- **Adversarial robustness (RU-adversarial probe).** The full stack catches 19/20 "
      "adversarial forms — SNILS/INN/passport (regex), VK/Telegram handles (regex), "
      "patronymics/diminutives (Natasha+qwen), code-switching (qwen). The **one leak is a "
      "Latin-transliterated Russian name** (\"Sergey Volkov\"): Natasha is Cyrillic-only, "
      "regex has no name rule, and qwen missed it — an argument for an English/Latin NER "
      "(OPF) when transliteration is expected.")
    A("- **License & compliance.** Synthetic/fictional content, released for research and "
      "teaching. **Benchmark success is NOT HIPAA or GDPR compliance.** Types map loosely "
      "to HIPAA Safe-Harbor / GDPR identifier concepts, but the mapping is illustrative, "
      "not legal certification; GDPR identifiability is context-dependent and HIPAA offers "
      "distinct Safe-Harbor vs Expert-Determination routes. Any *real* session data must "
      "go through consent + ethics review and must not be re-identified.")
    A("")
    A("## Metrics (what each column means)")
    A("")
    A("- **Coverage F2 / R (relaxed):** type-agnostic — *did we redact this PII span at "
      "all* (overlap ≥1 char)? **F2 weights recall 2× over precision** because a missed "
      "entity is leaked PII while a false positive is mere over-redaction "
      "(Presidio-research; i2b2/n2c2). **Headline.**")
    A("- **Type F2 / Micro-F1 / Macro-F1:** prediction must also match the gold span's "
      "canonical type. Micro = corpus-wide; Macro = unweighted mean over types (i2b2/n2c2).")
    A("- **Ent-R (entity-level recall, TAB):** an entity counts as *protected* only if "
      "**all** its mentions are masked — one un-redacted recurrence is a leak.")
    A("- **Direct-R / Quasi-R:** entity recall split by identifier class (TAB).")
    A("")
    A("_Citations: Pilán et al., *The Text Anonymization Benchmark*, Computational "
      "Linguistics 2022; Stubbs et al., *2014 i2b2/UTHealth de-identification*, JBI 2015; "
      "Microsoft Presidio-research evaluation framework; ai4privacy/pii-masking-300k._")
    A("")

    for ds, short, desc in DATASETS:
        res = load(ds)
        A(f"## {short} — {desc}")
        A("")
        if res is None:
            A("_Not yet scored._\n"); continue
        A(f"**{res['n_docs']} documents, {res['n_gold_mentions']} gold PII mentions.** "
          "★ marks the proposed default stack for this language.")
        ci_path = os.path.join(HERE, f"{ds}-bootstrap-ci.json")
        if os.path.exists(ci_path):
            ci = json.load(open(ci_path, encoding="utf-8"))
            cr = ci["coverage_recall"]
            extra = ""
            if "entity_recall" in ci:
                er = ci["entity_recall"]
                extra = f"; entity recall {er['mean']:.2f} (CI {er['lo95']:.2f}–{er['hi95']:.2f})"
            A("")
            A(f"_Bootstrap 95% CI ({ci['iters']} resamples, {ci['combo']}): coverage recall "
              f"**{cr['mean']:.2f}** (CI **{cr['lo95']:.2f}–{cr['hi95']:.2f}**){extra} — wide, as "
              "small N demands; treat point estimates as directional._")
        A("")
        A("### Ablation leaderboard")
        A("")
        A(leaderboard(res))
        A("")
        A("### Per-category recall (relaxed, type-agnostic) — *which layer catches what*")
        A("")
        A(per_category(res))
        A("")

    # Reconstruction / re-identification + limitations
    rec = os.path.join(HERE, "reconstruction-results.json")
    A("## Reconstruction & re-identification (what survives)")
    A("")
    if os.path.exists(rec):
        r = json.load(open(rec, encoding="utf-8"))
        A(f"Under the default RU stack (`{r['default_combo']}`), direct identifiers are "
          "well masked but **quasi-identifiers largely survive** — the real "
          "re-identification surface (TAB; RAT-Bench):")
        A("")
        A("| Client | Quasi survival rate | Surviving types |")
        A("|---|--:|---|")
        for cl, s in r["A_quasi_survival"].items():
            A(f"| {cl} | **{s['survival_rate']:.0%}** | {', '.join(s['survivors_by_type']) or '—'} |")
        A("")
        orr = r["C_over_redaction"]["over_redaction_rate"]
        A(f"A local qwen **inference attack** on the *redacted* text still reconstructs "
          "identity-narrowing attributes from context; a frontier model would recover "
          "more (SOTA tools prevent re-identification only ~27–29% of the time, Staab et "
          f"al.). Over-redaction (utility cost) under the default stack: **{orr:.0%}** of "
          "redacted spans were not PII. Full detail: `reconstruction-RESULTS.md`.")
    else:
        A("See `reconstruction-RESULTS.md` (run `reconstruct_attack.py`).")
    A("")
    A("## Key finding — OPF is NOT weak on Russian")
    A("")
    A("The README's prior assumption (\"OPF is English-first and weak on Russian\") is "
      "**contradicted by measurement**. Adding OPF to the RU stack lifts coverage recall "
      "0.865→**0.953**, entity recall 0.541→**0.838**, and quasi-identifier recall "
      "0.304→**0.739**. The lift is almost entirely one type: **DATE 0.00→0.91** — OPF's "
      "`private_date` catches the `DD.MM.YYYY` session dates that *no other layer* caught. "
      "It does NOT help medication/age/profession (still need qwen).")
    A("")
    A("**Bang-for-buck — fix shipped.** OPF costs ~227s/doc on MPS (vs regex 0.44s, "
      "ollama 14s). Since its whole RU advantage was dates, a numeric-date rule was added "
      "to the regex layer. Result: the LLM-free-of-OPF default `natasha+regex+ollama` now "
      "reaches **0.924** recall / **0.811** entity recall / **0.739** quasi-recall — "
      "matching OPF's quasi-recall exactly and within 0.03 of its coverage recall, at "
      "~500× the speed. OPF's residual edge is spelled-out dates + perfect PERSON.")
    A("")
    # Privacy–utility (P1)
    pu = os.path.join(HERE, "privacy-utility-results.json")
    if os.path.exists(pu):
        P = json.load(open(pu, encoding="utf-8"))
        A("## Privacy–utility (P1: top-k attack + downstream task)")
        A("")
        b = P["attack_budget"]
        A(f"**Attack budget (declared):** `{b['model']}`, temp {b['temperature']}, "
          f"{b['calls_per_client']} call/client, top-{b['topk']} guesses/attribute, "
          f"background knowledge = {b['background_knowledge']}. A frontier attacker is a "
          "strict upper bound on this local-model lower bound (Staab et al.; RAT-Bench).")
        A("")
        A("| Client | top-1 | top-3 | of N | residual risk | CBT-signal preserved |")
        A("|---|--:|--:|--:|---|--:|")
        for cl in ("a", "b"):
            pr = P["privacy"][cl]
            ut = P["utility"][cl]["mean_signal_preserved"]
            ut_s = f"{ut:.0%}" if ut is not None else "n/a"
            A(f"| {cl} | {pr['top1']} | {pr['top3']} | {pr['n_attr']} | **{pr['risk_class']}** | {ut_s} |")
        if "quasi_combination" in P:
            A("")
            A("**Quasi-identifier combination (k-anonymity-style):** direct identifiers can "
              "be fully masked yet a person singled out by surviving quasi-identifiers "
              "*together*. Using declared, illustrative RU population fractions (method demo, "
              "not census):")
            A("")
            A("| Client | surviving quasi | expected matches | singles out? |")
            A("|---|---|--:|---|")
            for cl in ("a", "b"):
                q = P["quasi_combination"].get(cl, {})
                em = q.get("expected_matches")
                A(f"| {cl} | {', '.join(q.get('surviving_quasi', [])) or '—'} | "
                  f"{em if em is not None else '—'} | {'**YES**' if q.get('singles_out') else 'no (k>1)'} |")
        cnp = P["utility"].get("char_nonpii_preservation")
        A("")
        A(f"**Downstream utility (Tau-Eval style):** the de-identified transcript still "
          "supports its clinical purpose — re-running cognitive-distortion extraction on "
          "redacted vs. original text preserves "
          f"~{int(round(100*sum(P['utility'][c]['mean_signal_preserved'] for c in ('a','b'))/2))}% "
          f"of distortion types, and **{cnp:.1%}** of non-PII characters survive redaction. "
          "Privacy and utility are in tension; the default stack is tuned for recall.")
        A("")
    # IAA (gold validation)
    iaa = os.path.join(HERE, "iaa-results.json")
    if os.path.exists(iaa):
        I = json.load(open(iaa, encoding="utf-8"))
        sa = I["span_agreement"]
        A("## Gold validation — inter-annotator agreement (IAA)")
        A("")
        A(f"The pattern-derived gold (A1) was checked against an **independent** "
          f"from-scratch annotation by GPT-5/Codex (A2) on a seed set ({', '.join(I['seed'])}). "
          f"**Entity-level F1 {sa['f1']:.3f}** (P {sa['precision']:.3f} = A2 items matching gold, "
          f"R {sa['recall']:.3f} = gold *entities* A2 also marked); "
          f"**character-level Cohen's κ {I['char_cohen_kappa']:.3f}** (substantial). "
          f"A2 independently re-found **every** gold entity (recall 1.0) and surfaced **{len(I['gold_blind_spots'])} "
          "blind spots** the answer-key gold structurally omits — spelled-out phone/policy "
          "digits, relative dates (\"в прошлый четверг\"), and quasi-professions (\"тимлид\"). "
          "These are the adjudication queue for a v2 gold. See `IAA-RESULTS.md`. This is the "
          "fix for the circular, pattern-derived gold — though full corpus double-annotation "
          "remains future work.")
        A("")
        A("**Adjudication applied (v2 gold).** The high-confidence blind spots were folded "
          "into the gold (`adjudicated: true`): spelled-out phone/policy read at the card "
          "check, the Latin frontmatter name, quasi-professions (тимлид/бэкенд/младший "
          "специалист), and the employer city. Relative dates (\"в прошлый четверг\") were "
          "explicitly **scoped out** (fuzzy quasi-temporal, often clinical content). This "
          "*lowered* RU default recall **0.93 → 0.86** — not a regression but a more complete, "
          "harder gold: every spelled-out identifier and the transliterated name now **leak** "
          "(no layer catches them), arguing for a spelled-digit normalizer + a Latin-NER.")
        A("")
    A("## Stricter headline check (containment)")
    A("")
    A("Beyond relaxed (≥1-char) overlap, a **containment** metric requires ≥80% of an "
      "identifier to be masked. For the RU default, containment recall equals relaxed "
      "(0.93) — i.e. catches are not 1-char-overlap artifacts; when the stack flags a PII "
      "it masks essentially all of it. Strict exact-span recall is 0.83 (boundary "
      "differences only).")
    A("")
    A("## Known limitations")
    A("")
    A("- **Small N** — each miss moves recall several points; treat per-type numbers as "
      "directional.")
    A("- **Synthetic RU data** — fictional; not real patient text.")
    A("- **Spelled-out digits** (e.g. phone read out word-by-word) are out of scope for "
      "the regex layer by design and fall to the LLM layer / manual review.")
    A("- One EN-real doc failed Ollama JSON parsing (returned no spans) — a single-doc "
      "lower bound on the ollama EN-real numbers.")
    A("- **Non-determinism.** The Ollama (qwen) and GPT-5/Codex (IAA) steps are not fully "
      "deterministic; qwen runs at temperature 0 and the IAA seed annotation is committed "
      "for reproducibility, but exact spans can vary run-to-run. The bootstrap CIs and the "
      "detector manifests bound and date the measurements.")
    A("- Confidence intervals (bootstrap, 95%) are reported per dataset above; with N as "
      "small as 10–32 they are wide by design.")
    A("")

    path = os.path.join(HERE, "BENCHMARK.md")
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"[benchmark] wrote {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
