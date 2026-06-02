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

from confide_eval import paths

HERE = os.fspath(paths.RESULTS)
DATASETS = [
    ("ru", "RU-synth", "Russian synthetic therapy series (6 clients, 30 sessions)"),
    ("en", "EN-synth", "English curated therapy-style snippets"),
    ("en-real", "EN-real", "External public slice of ai4privacy/pii-masking-300k — "
     "generic, non-therapy, non-clinical PII used only as an external EN anchor "
     "(real generic PII, not synthetic; no clinical data)"),
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
    head = "| Combo | MaskCov F2 (rel) | MaskCov R | Type F2 | Micro-F1 | Macro-F1 | Preds |"
    sep =  "|---|--:|--:|--:|--:|--:|--:|"
    if has_ent:
        head = ("| Combo | MaskCov F2 (rel) | MaskCov R | Type F2 | Macro-F1 | Ent-R (TAB) | "
                "Harm-wtd R | Direct-R | Quasi-R | Preds |")
        sep =  "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|"
    lines += [head, sep]
    for name, e in res["combos"].items():
        if e.get("status") == "missing-cache":
            continue
        cr, tr = e["coverage_relaxed"], e["type_relaxed"]
        if has_ent and "entity_level" in e:
            el = e["entity_level"]
            d = el["by_class"].get("direct", {}).get("recall", 0.0)
            q = el["by_class"].get("quasi", {}).get("recall", 0.0)
            hw = el.get("harm_weighted_recall", 0.0)
            lines.append(f"| {name} | **{cr['f2']:.3f}** | {cr['r']:.3f} | {tr['f2']:.3f} | "
                         f"{tr['macro_f1']:.3f} | {el['entity_recall']:.3f} | {hw:.3f} | "
                         f"{d:.3f} | {q:.3f} | {e['n_pred']} |")
        else:
            lines.append(f"| {name} | **{cr['f2']:.3f}** | {cr['r']:.3f} | {tr['f2']:.3f} | "
                         f"{tr['overall']['f1'] if 'overall' in tr else tr['f1']:.3f} | {tr['macro_f1']:.3f} | {e['n_pred']} |")
    return "\n".join(lines)


def split_table(res):
    """Per-split (dev/test) headline sub-table for the ★ stack (Codex audit R2 #2).
    REPORTING.md §4 promises dev/test separately; the leaderboard aggregates all
    docs, so we surface the split-level headline. Reporting only — nothing tuned on
    test. Returns '' if the ★ combo carries no by_split block."""
    star = next((e for n, e in res["combos"].items()
                 if "★" in n and isinstance(e, dict) and "by_split" in e), None)
    if not star:
        return ""
    bs = star["by_split"]
    # only emit when there is a genuine dev/test partition (skip single-split sets)
    if set(bs) <= {"adversarial"} or len(bs) < 2:
        return ""
    has_ent = any("entity_recall" in v for v in bs.values())
    lines = ["### Dev / test split (★ stack, reporting only — nothing tuned on test)", ""]
    if has_ent:
        lines += ["| Split | Docs | Gold | MaskCov R | MaskCov F2 | Ent-R (TAB) | Harm-wtd R |",
                  "|---|--:|--:|--:|--:|--:|--:|"]
        for sp in ("dev", "test"):
            if sp not in bs:
                continue
            v = bs[sp]
            lines.append(f"| {sp} | {v['n_docs']} | {v['n_gold_mentions']} | "
                         f"{v['mask_coverage_recall']:.3f} | {v['mask_coverage_f2']:.3f} | "
                         f"{v['entity_recall']:.3f} | {v['harm_weighted_recall']:.3f} |")
    else:
        lines += ["| Split | Docs | Gold | MaskCov R | MaskCov F2 |", "|---|--:|--:|--:|--:|"]
        for sp in ("dev", "test"):
            if sp not in bs:
                continue
            v = bs[sp]
            lines.append(f"| {sp} | {v['n_docs']} | {v['n_gold_mentions']} | "
                         f"{v['mask_coverage_recall']:.3f} | {v['mask_coverage_f2']:.3f} |")
    return "\n".join(lines)


def per_category(res):
    """Recall per canonical type for each combo — surfaces LLM-required types."""
    combos = [(n, e) for n, e in res["combos"].items() if isinstance(e, dict) and "coverage_relaxed_per_type" in e]
    # only show types that have gold support somewhere (drops e.g. Philter's
    # untyped OTHER, which has zero gold support and would add an all-"—" column).
    types = sorted({t for _, e in combos for t, m in e["coverage_relaxed_per_type"].items()
                    if m.get("support")})
    lines = ["| Combo | " + " | ".join(types) + " |",
             "|---|" + "|".join("--:" for _ in types) + "|"]
    for name, e in combos:
        cells = []
        for t in types:
            m = e["coverage_relaxed_per_type"].get(t)
            cells.append(f"{m['r']:.2f}" if m and m["support"] else "—")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def default_combo(res):
    for name, e in res["combos"].items():
        if "★" in name and isinstance(e, dict) and "coverage_relaxed" in e:
            return name, e
    return None, None


def fmt_delta(a, b):
    return f"{b - a:+.3f}"


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
    A("- **Composition & provenance.** Four datasets (see per-dataset sections). Every "
      "**therapy transcript** — the Russian series and the EN-synth slice — is **fully "
      "synthetic and fictional** (no real patients), hand-built from synthetic client "
      "inventories. **EN-real is the one exception:** an external public slice of "
      "`ai4privacy/pii-masking-300k` containing **generic, non-therapy, non-clinical** PII; "
      "it is real generic PII (not synthetic the way the therapy corpus is) carried "
      "unmodified under that dataset's license and used **only as an external EN anchor** — "
      "it holds no real clinical/therapy data. The RU-adversarial set probes hard forms "
      "such as transliteration, handles, and structured IDs.")
    A("- **Languages.** Russian (`ru`), English (`en`).")
    A("- **PII taxonomy (canonical).** PERSON, LOCATION, ORG, PHONE, EMAIL, URL, ID, "
      "DATE, MEDICATION, AGE, PROFESSION. Each RU entity is also tagged **direct** vs "
      "**quasi**-identifier (TAB), and `llm_required` where deterministic layers "
      "structurally cannot catch it (medication, age, profession, and some contextual or "
      "spelled-out dates).")
    A("- **DATE coverage (T6).** The deterministic regex layer now covers not just numeric "
      "dates (DD.MM.YYYY / ISO) but also **relative / colloquial / month-name dates** in "
      "both languages — EN \"last Tuesday\", \"12 December\", \"N weeks ago\", \"19th of the "
      "month\"; RU \"в прошлый вторник\", \"третьего февраля\", \"N дней назад\". This closes "
      "the one additive gap the Presidio baseline exposed (its `DATE_TIME` recognizer), "
      "lifting regex-layer DATE recall to 1.00 on EN/EN-real and recovering the last "
      "spelled-out RU date. Bare deictic adverbs (today/this week / сегодня/на этой неделе) "
      "are deliberately excluded as non-identifying and gold-unannotated.")
    A("- **Collection / labeling.** RU gold is located programmatically from curated "
      "surface-form patterns (Cyrillic-morphology-aware) over the raw transcripts, then "
      "hand-verified; every mention carries an `entity_id` for entity-level scoring.")
    A("- **Uses.** De-identification tool comparison; teaching. **Not** a clinical "
      "instrument; synthetic RU content must not be treated as real patient data.")
    A("- **Limitations.** Small N (each miss moves recall several points); synthetic RU "
      "text; spelled-out digit strings are out of scope for the regex layer by design.")
    A("- **Splits.** Person-disjoint: clients a/c/e = `dev`, clients b/d/f = `test` "
      "(each client is a distinct synthetic person → no profile leakage across splits).")
    A("- **Preregistration & power.** The fixed metrics, ★ defaults, dev/test protocol, and "
      "a small honest power analysis (entity-recall CI half-width ≈ ±0.05 at N=30 → minimum "
      "detectable difference ≈ 0.10; the corpus is underpowered for small effects, so "
      "comparisons are reported with CIs, not significance stars) are preregistered in "
      "`PREREGISTRATION.md`.")
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
    A("- **MaskCov F2 / R (mask-coverage, relaxed):** type-agnostic — *did the deployed "
      "redaction mask touch this PII span at all* (overlap ≥1 char)? **F2 weights recall 2× "
      "over precision** because a missed entity is leaked PII while a false positive is mere "
      "over-redaction (Presidio-research; i2b2/n2c2). This is a *mask-coverage* view, **not** "
      "a strict 1:1 span/entity match: a gold span is credited if ANY prediction overlaps it "
      "and a predicted mask counts as a hit if it overlaps ANY gold, so one large span can "
      "score P=R=1.0. The rigorous headline is **entity-level (TAB) recall** below. "
      "(Renamed from \"Coverage F2\" per Codex audit R2 #3 so it is not read as standard "
      "span-F2.)")
    A("- **Type F2 / Micro-F1 / Macro-F1:** prediction must also match the gold span's "
      "canonical type. Micro = corpus-wide; Macro = unweighted mean over types (i2b2/n2c2).")
    A("- **Ent-R (entity-level recall, TAB):** an entity counts as *protected* only if "
      "**all** its mentions are masked — one un-redacted recurrence is a leak.")
    A("- **Direct-R / Quasi-R:** entity recall split by identifier class (TAB).")
    A("- **Harm-wtd R (harm-weighted entity recall):** entity recall with each entity "
      "weighted by the clinical severity of its type (HARM-TAXONOMY.md: medication/person "
      "high, location/profession/age/date medium, email/phone/url/id low). It up-weights "
      "missing a high-harm identifier over a low-harm one; reported alongside plain Ent-R, "
      "not as a replacement.")
    A("")
    A("_Citations: Pilán et al., *The Text Anonymization Benchmark*, Computational "
      "Linguistics 2022; Stubbs et al., *2014 i2b2/UTHealth de-identification*, JBI 2015; "
      "Microsoft Presidio-research evaluation framework; ai4privacy/pii-masking-300k. "
      "Checked source links are listed in `SOURCES.md`._")
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
        st = split_table(res)
        if st:
            A(st)
            A("")
        A("### Per-category recall (relaxed, type-agnostic) — *which layer catches what*")
        A("")
        A(per_category(res))
        A("")

    # Established off-the-shelf baselines (Codex audit R3): Presidio + Philter.
    # Tables above already auto-include the presidio/philter/presidio+regex+ollama
    # rows (they come straight from the bench-results.json combos). Here we add the
    # interpretive narrative + the unique-capability finding so a regeneration of
    # BENCHMARK.md keeps it.
    en_res, enr_res = load("en"), load("en-real")

    def _cell(res, combo, path):
        if not res:
            return None
        e = res["combos"].get(combo)
        if not isinstance(e, dict) or "coverage_relaxed" not in e:
            return None
        d = e
        for k in path:
            d = d[k]
        return d

    if en_res and ("presidio" in en_res["combos"]):
        A("## Established baselines — Microsoft Presidio & Philter (Codex audit R3)")
        A("")
        A("To anchor CONFIDE's metrics against a known, off-the-shelf system, two "
          "established de-identifiers run on the same gold via the same cache/manifest "
          "pipeline as every other detector:")
        A("")
        A("- **Microsoft Presidio** (`presidio-analyzer`, spaCy `en_core_web_sm` — the "
          "*small* model, chosen under a ~1.8 GiB disk constraint; `en_core_web_lg` "
          "would raise PERSON/LOCATION recall somewhat). Run on **en** and **en-real** "
          "only. Presidio's RU support is spaCy-NER-dependent and weak, so it is **not** "
          "reported on the RU datasets to avoid misrepresenting it — a documented scope "
          "limit, not a measured RU score.")
        A("- **Philter** (`philter-lite`, UCSF clinical de-id, `philter_delta.toml` HIPAA "
          "Safe-Harbor rule set; needs NLTK `averaged_perceptron_tagger_eng`). English "
          "clinical-notes tool; run on **en** and **en-real**.")
        A("")
        p_f2 = _cell(en_res, "presidio", ["coverage_relaxed", "f2"])
        s_f2 = _cell(en_res, "opf+regex+ollama ★", ["coverage_relaxed", "f2"])
        p_t = _cell(en_res, "presidio", ["type_relaxed", "f1"])
        s_t = _cell(en_res, "opf+regex+ollama ★", ["type_relaxed", "f1"])
        pr_f2 = _cell(enr_res, "presidio", ["coverage_relaxed", "f2"])
        pr_r = _cell(enr_res, "presidio", ["coverage_relaxed", "r"])
        sr_f2 = _cell(enr_res, "opf+regex+ollama ★", ["coverage_relaxed", "f2"])
        _cmp = ("now also leads coverage F2" if s_f2 >= p_f2
                else "trails Presidio's broad-`DATE_TIME` coverage F2 only slightly")
        A(f"**Headline finding.** Neither off-the-shelf system beats the therapy-tuned "
          f"CONFIDE stack on type-aware F1. On the easy curated EN set the stack {_cmp} "
          f"(stack {s_f2:.3f} vs Presidio {p_f2:.3f}) — since the regex layer gained a "
          f"relative/colloquial-date recognizer (T6) it matches Presidio's `DATE_TIME` "
          f"date recall — and its type-aware F1 stays far ahead ({s_t:.3f} vs {p_t:.3f}). "
          f"On the harder **real** ai4privacy slice Presidio collapses to "
          f"{pr_r:.3f} coverage recall ({pr_f2:.3f} F2 vs the stack's {sr_f2:.3f}) — generic NER + "
          f"structured recognizers don't cover the bespoke ID/markup formats. Philter is "
          f"high-recall but emits nearly everything as untyped `OTHER`, unusable for "
          f"type-aware redaction. **This is the expected, valid baseline result: a generic "
          f"system is not a therapy-tuned one.**")
        A("")
        A("### Unique capabilities (what the baselines catch that the stack does not)")
        A("")
        A("Diffing gold spans missed by `opf+regex+ollama` but caught (relaxed overlap) "
          "by each baseline:")
        A("")
        A("- **Relative/colloquial dates — gap now CLOSED (T6).** Presidio's `DATE_TIME` "
          "was the one signal it caught that the stack missed — *\"last Tuesday\"*, "
          "*\"12 December\"*, *\"last Thursday\"*, *\"19th of the month\"*, *\"5th of "
          "January\"*. The regex layer now ships a tight relative/colloquial-date "
          "recognizer (EN + RU) covering exactly these forms, so the deterministic stack's "
          "DATE recall rose from **0.125→1.00** (EN) and **0.143→1.00** (EN-real), matching "
          "Presidio's date coverage **without** adopting Presidio. On EN-real, Presidio "
          "already caught **0** spans the stack missed.")
        A("- **Philter** caught 1 unique span on EN-synth (*\"12 December\"* — now also "
          "covered by the new recognizer) and 1 on EN-real (a 2-letter country code "
          "*\"GB\"*). Breadth offset by no usable typing.")
        A("- Presidio's **structured recognizers** (US_SSN, IBAN, credit card, bank/"
          "passport/driver-licence, crypto, IP) are a capability the regex layer lacks in "
          "principle, but on this gold they did **not** out-recall the stack: stack ID "
          "recall is 1.00 on EN-real vs Presidio's 0.30. A potential robustness asset on "
          "other corpora, not a measured win here.")
        A("")
        A("**Takeaway:** the one coverage a baseline used to add over the stack — "
          "**relative/colloquial dates** (Presidio `DATE_TIME`) — has been folded into the "
          "deterministic regex layer (T6), so the stack no longer needs Presidio's date "
          "recognizer. No remaining baseline capability out-recalls the therapy-tuned stack "
          "on this gold.")
        A("")
        A("> **Graphic:** the grouped bar chart \"CONFIDE stack vs established baselines\" "
          "(Coverage F2 vs type-aware micro-F1 for {opf+regex+ollama ★, presidio, philter, "
          "presidio+regex+ollama}, one panel each for EN-synth and EN-real) is rendered in "
          "**`benchmark-report.html`** §6 (generated by `make_tufte_report.py` from "
          "`{en,en-real}-bench-results.json`). It shows baselines edging on coverage but "
          "falling far behind on type-aware F1, and Presidio collapsing on the real slice.")
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
          "redacted *spans* were not PII — but those false-positive spans are short, so only "
          "**0.47%** of non-PII *characters* are over-masked (99.5% char-level non-PII "
          "preservation; the two views are complementary, span-rate vs char-rate). Full "
          "detail: `reconstruction-RESULTS.md`.")
    else:
        A("See `reconstruction-RESULTS.md` (run `reconstruct_attack.py`).")
    A("")
    A("## OPF on Russian — optional, not a default")
    A("")
    ru_res = load("ru")
    if ru_res:
        base_name, base = default_combo(ru_res)
        opf = ru_res["combos"].get("opf+natasha+regex+ollama")
        if base and isinstance(opf, dict) and "coverage_relaxed" in opf:
            b_cov, o_cov = base["coverage_relaxed"], opf["coverage_relaxed"]
            b_ent, o_ent = base.get("entity_level"), opf.get("entity_level")
            b_quasi = b_ent["by_class"].get("quasi", {}).get("recall") if b_ent else None
            o_quasi = o_ent["by_class"].get("quasi", {}).get("recall") if o_ent else None
            A(f"On the current RU corpus, adding OPF to `{base_name.replace(' ★','')}` changes "
              f"coverage recall **{b_cov['r']:.3f}→{o_cov['r']:.3f}** "
              f"({fmt_delta(b_cov['r'], o_cov['r'])}) and F2 "
              f"**{b_cov['f2']:.3f}→{o_cov['f2']:.3f}** "
              f"({fmt_delta(b_cov['f2'], o_cov['f2'])}).")
            if b_ent and o_ent:
                A(f"Entity recall changes **{b_ent['entity_recall']:.3f}→{o_ent['entity_recall']:.3f}** "
                  f"({fmt_delta(b_ent['entity_recall'], o_ent['entity_recall'])}); quasi recall "
                  f"changes **{b_quasi:.3f}→{o_quasi:.3f}** "
                  f"({fmt_delta(b_quasi, o_quasi)}).")
            A("That residual lift is useful as a comparison point, but OPF is not the default "
              "RU layer: regex/Natasha/qwen remains the local-first stack, and OPF should be "
              "re-run whenever the RU gold changes before its row is cited.")
        else:
            A("The OPF RU cache is not scored for the current gold because its detector cache "
              "does not validate against the current document set. This is intentional: stale "
              "detector outputs are excluded rather than mixed into headline results. Re-run "
              "`run_detectors.py --dataset ru --detectors opf` before citing an OPF-on-RU row.")
    else:
        A("Run `score_bench.py --dataset ru --out-prefix ru-` to refresh the OPF comparison.")
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
        kappa = I["char_cohen_kappa"]
        kqual = "substantial" if kappa >= 0.6 else "moderate" if kappa >= 0.4 else "fair"
        A("## Gold validation — LLM-assisted consistency check (single second-annotator)")
        A("")
        A("**This is NOT human inter-annotator agreement** (Codex audit R4). It is an "
          "LLM-assisted consistency check with a single automated second annotator; a human "
          "multi-annotator study with adjudication remains required before any publishable "
          "agreement claim.")
        A("")
        A(f"The pattern-derived gold (A1) was checked against an **independent** "
          f"from-scratch annotation by one LLM second-annotator (GPT-5/Codex, A2) on a seed "
          f"set ({', '.join(I['seed'])}). "
          f"**Entity-level F1 {sa['f1']:.3f}** (P {sa['precision']:.3f} = A2 items matching gold, "
          f"R {sa['recall']:.3f} = gold *entities* A2 also marked); "
          f"**character-level Cohen's κ {kappa:.3f}** ({kqual} consistency vs the single LLM "
          f"second-annotator — not a human-agreement κ). "
          f"A2 surfaced **{len(I['gold_blind_spots'])} blind spots** the answer-key gold "
          "structurally omits — relative dates (\"в прошлый четверг\") and spelled-out or "
          "contextual identifiers — and **"
          f"{len(I.get('a1_only', []))} A1-only** item(s) A2 missed. "
          "These are the adjudication queue for a v2 gold. See `IAA-RESULTS.md`. This probes "
          "the circular, pattern-derived gold; full corpus human double-annotation remains "
          "future work.")
        A("")
        A("**Adjudication applied (v2 gold).** The high-confidence blind spots were folded "
          "into the gold (`adjudicated: true`): spelled-out phone/policy read at the card "
          "check, the Latin frontmatter name, quasi-professions (тимлид/бэкенд/младший "
          "специалист), and the employer city. Relative dates (\"в прошлый четверг\") were "
          "explicitly **scoped out** (fuzzy quasi-temporal, often clinical content). This "
          "makes the current v2 gold harder and more complete: spelled-out identifiers and "
          "transliterated names are now counted as leaks when no layer catches them, arguing "
          "for a spelled-digit normalizer + a Latin-NER.")
        A("")
    A("## Stricter headline check (containment)")
    A("")
    ru_res = load("ru")
    _, ru_default = default_combo(ru_res) if ru_res else (None, None)
    if ru_default:
        rel = ru_default["coverage_relaxed"]["r"]
        cont = ru_default["coverage_containment"]["r"]
        strict = ru_default["coverage_strict"]["r"]
        A("Beyond relaxed (≥1-char) overlap, a **containment** metric requires ≥80% of an "
          f"identifier to be masked. For the RU default, containment recall is **{cont:.3f}** "
          f"vs relaxed **{rel:.3f}**; strict exact-span recall is **{strict:.3f}**. The small "
          "relaxed/containment gap means the headline is not driven by 1-character touches, "
          "while the strict gap mostly reflects boundary differences.")
    else:
        A("Beyond relaxed (≥1-char) overlap, a **containment** metric requires ≥80% of an "
          "identifier to be masked. Run the RU scorer to populate this audit check.")
    A("")
    A("## Known limitations")
    A("")
    A("- **Presidio/Philter are generic baselines** (not therapy-tuned, EN-only, Presidio "
      "on the *small* spaCy model); their lower scores are expected and reported as an "
      "anchor, not a failure. Presidio RU is intentionally unscored (weak spaCy-RU NER).")
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
    A("- Bootstrap confidence-interval support is included in `bootstrap_ci.py`; report the "
      "CI files only after they have been regenerated for the current gold and caches.")
    A("")

    path = os.path.join(os.fspath(paths.DOCS), "BENCHMARK.md")
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"[benchmark] wrote {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
