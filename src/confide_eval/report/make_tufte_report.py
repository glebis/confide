#!/usr/bin/env python3
"""Generate the standalone Tufte-style HTML benchmark report(s) from the JSONs.

Reads ru/ru-adv/en/en-real-bench-results.json + reconstruction / privacy-utility
/ regulatory results and emits one HTML per language under results/
(benchmark-report.html, benchmark-report.ru.html, ...) — no build step, Chart.js
via CDN. Re-run after re-scoring to refresh.

Design follows the tufte-report skill design tokens (EB Garamond + Monaspace
Argon, warm-white bg, 3-color semantic palette, state-lines, asides).

Localisation: all reports are generated from this one source. English is the
canonical msgid; each ``report/translations.<lang>.json`` adds a language. Prose
is wrapped in ``t(...)`` (see ``confide_eval.report.i18n``); numbers interpolate
via ``.format`` AFTER lookup, so they never enter the catalog key. Adding a
language = dropping a new ``translations.<lang>.json``; the generator emits one
HTML per language and warns on any English fallback (incomplete catalog).
"""
import json
import os

from confide_eval import paths
from confide_eval.report.i18n import languages, missing, set_lang, t

HERE = os.fspath(paths.RESULTS)

# The local LLM detector layer ("ollama") and the local re-identification
# attacker are the same model: Qwen2.5-3B-Instruct, run locally via Ollama at
# temperature 0 (run-benchmark.sh LLM_MODEL default). The separate qwen3-32b /
# Groq runs are cloud comparison experiments, not part of these published tables.
OLLAMA_MODEL = "qwen2.5:3b"          # Qwen2.5-3B-Instruct, local Ollama, temp 0

# Column glossary for the leaderboard tables: header -> (tooltip, direction).
# direction in {"↑" higher-is-better, "↓" lower-is-better, "·" neutral/context}.
COL_GLOSSARY = {
    "cov R": ("Mask-coverage recall (relaxed, ≥1-char overlap): fraction of gold "
              "PII spans the redaction mask touched at all. A miss = leaked PII.", "↑"),
    "cov F2": ("Mask-coverage F2 (recall-weighted, β=2): recall counts 2× precision, "
               "because a missed entity leaks PII while a false positive only "
               "over-redacts.", "↑"),
    "ent R": ("Entity-level recall (TAB): an entity counts as protected only if ALL "
              "its mentions are masked — one un-redacted recurrence is a leak.", "↑"),
    "direct": ("Entity recall for direct identifiers (name, phone, email, policy/ID).", "↑"),
    "quasi": ("Entity recall for quasi-identifiers (age, profession, city, employer, "
              "medication, date) — the combinable re-identification surface.", "↑"),
    "preds": ("Number of predicted spans the stack emitted (redaction volume). "
              "Context, not a score: more masking trades precision for recall.", "·"),
}
DIR_WORD = {"↑": "higher is better", "↓": "lower is better", "·": "context"}


def load(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


RU = load("ru-bench-results.json")
EN = load("en-bench-results.json")
ENR = load("en-real-bench-results.json")
RUADV = load("ru-adv-bench-results.json")
RUREAL = load("ru-real-bench-results.json")   # external real-text RU anchor (JayGuard, Apache-2.0)
REC = load("reconstruction-results.json")
PU = load("privacy-utility-results.json")
REG = load("regulatory-results.json")


def combos_clean(res):
    """(name, entry) for real combos (skip missing-cache)."""
    return [(n, e) for n, e in res["combos"].items()
            if isinstance(e, dict) and "coverage_relaxed" in e]


def best_recall(res):
    cc = combos_clean(res)
    return max((e["coverage_relaxed"]["r"] for _, e in cc), default=0.0)


# ---- data for charts (emitted as JSON into the page) ----------------------
def leaderboard_data(res):
    out = []
    for n, e in combos_clean(res):
        row = {"combo": n.replace(" ★", " ★"),
               "recall": e["coverage_relaxed"]["r"],
               "f2": e["coverage_relaxed"]["f2"],
               "preds": e["n_pred"], "star": "★" in n}
        if "entity_level" in e:
            el = e["entity_level"]
            row["direct"] = el["by_class"].get("direct", {}).get("recall", 0.0)
            row["quasi"] = el["by_class"].get("quasi", {}).get("recall", 0.0)
            row["entR"] = el["entity_recall"]
        out.append(row)
    return out


def per_type_compare(res, combo_a, combo_b):
    """recall per type for two combos (for the 'who catches what' chart)."""
    ca = dict(res["combos"][combo_a]["coverage_relaxed_per_type"])
    cb = dict(res["combos"][combo_b]["coverage_relaxed_per_type"])
    types = sorted({k for k in (ca | cb) if (ca.get(k, {}).get("support") or cb.get(k, {}).get("support"))})
    return {"types": types,
            "a": [round(ca.get(k, {}).get("r", 0.0), 3) for k in types],
            "b": [round(cb.get(k, {}).get("r", 0.0), 3) for k in types],
            "a_name": combo_a, "b_name": combo_b}


def baselines_data(res):
    """Coverage-F2 (headline) + type-aware micro-F1 for the 4 EN comparison combos:
    the CONFIDE ★ stack vs the established off-the-shelf baselines (Presidio, Philter)
    and the Presidio-in-the-stack ensemble. Drives the 'stack vs baselines' chart.
    Missing combos are skipped."""
    if not res:
        return {}
    order = ["opf+regex+ollama ★", "presidio", "philter", "presidio+regex+ollama"]
    combos, covf2, microf1 = [], [], []
    for name in order:
        e = res["combos"].get(name)
        if not isinstance(e, dict) or "coverage_relaxed" not in e:
            continue
        combos.append(name)
        covf2.append(round(e["coverage_relaxed"]["f2"], 3))
        microf1.append(round(e["type_relaxed"]["f1"], 3))
    return {"combos": combos, "covf2": covf2, "microf1": microf1}


DATA = {
    "ru_leaderboard": leaderboard_data(RU) if RU else [],
    "en_leaderboard": leaderboard_data(EN) if EN else [],
    "enr_leaderboard": leaderboard_data(ENR) if ENR else [],
    "rureal_leaderboard": leaderboard_data(RUREAL) if RUREAL else [],
    "ru_whocatches": per_type_compare(RU, "natasha+regex", "natasha+regex+ollama ★") if RU else {},
    "en_baselines": baselines_data(EN),
    "enr_baselines": baselines_data(ENR),
    "reconstruction": REC or {},
}


# default combo name per dataset (the ★ one)
def star_name(res):
    for n in res["combos"]:
        if "★" in n:
            return n
    return ""


RU_STAR = star_name(RU) if RU else ""
EN_STAR = star_name(EN) if EN else ""
ENR_STAR = star_name(ENR) if ENR else ""


# headline numbers
def star_recall(res):
    for n, e in res["combos"].items():
        if "★" in n and isinstance(e, dict) and "coverage_relaxed" in e:
            return e["coverage_relaxed"]["r"]
    return 0.0


def combo_recall(res, name):
    e = res["combos"].get(name, {})
    return e["coverage_relaxed"]["r"] if "coverage_relaxed" in e else 0.0


ru_default_r = star_recall(RU) if RU else 0.0            # the proposed default's recall
ru_opf_r = combo_recall(RU, "opf+natasha+regex+ollama") if RU else 0.0
n_combos = len(RU["combos"]) if RU else 0
n_gold = (RU["n_gold_mentions"] if RU else 0)
ru_default = RU["combos"].get(RU_STAR, {}) if RU else {}
ru_entity = ru_default.get("entity_level", {})
ru_direct = ru_entity.get("by_class", {}).get("direct", {}).get("recall", 0.0)
ru_quasi = ru_entity.get("by_class", {}).get("quasi", {}).get("recall", 0.0)
ru_opf_valid = bool(RU and "coverage_relaxed" in RU["combos"].get("opf+natasha+regex+ollama", {}))
# combined quasi survival across both clients (not client-A only)
if REC:
    _a, _b = REC["A_quasi_survival"]["a"], REC["A_quasi_survival"]["b"]
    surv_comb = (_a["survived"] + _b["survived"]) / (_a["quasi_entities"] + _b["quasi_entities"])
    atk = REC["B_inference_attack"]
    atk_rec = sum(v.get("n_recovered", 0) for v in atk.values() if isinstance(v, dict))
    atk_tot = sum(v.get("n_tested", 0) for v in atk.values() if isinstance(v, dict))
else:
    surv_comb, atk_rec, atk_tot = 0.0, 0, 0
overred = REC["C_over_redaction"]["over_redaction_rate"] if REC else 0.0
# privacy-utility (P1)
if PU:
    pu_top3 = sum(PU["privacy"][c]["top3"] for c in ("a", "b"))
    pu_n = sum(PU["privacy"][c]["n_attr"] for c in ("a", "b"))
    pu_util = sum(PU["utility"][c]["mean_signal_preserved"] for c in ("a", "b")) / 2
    pu_cnp = PU["utility"].get("char_nonpii_preservation", 0.0)
    pu_risk = " / ".join(PU["privacy"][c]["risk_class"] for c in ("a", "b"))
else:
    pu_top3, pu_n, pu_util, pu_cnp, pu_risk = 0, 0, 0.0, 0.0, "—"

# regulatory / residual-risk (from confide_eval.scoring.regulatory)
reg_ru = (REG or {}).get("datasets", {}).get("ru")
if reg_ru:
    reg_tier = reg_ru["tier"]["tier"]
    reg_direct = reg_ru["tier"]["direct_residual"]
    reg_oos = reg_ru["tier"].get("direct_residual_out_of_scope", 0)
    reg_special = reg_ru["tier"]["special_residual"]
    reg_inf = reg_ru["wp29"]["inference"]["rate"]
    reg_link_roc = reg_ru["wp29"]["linkability"].get("roc_auc") or 0.0
    reg_hip_pass = reg_ru["hipaa"]["passed"]
    reg_hip_app = reg_ru["hipaa"]["applicable"]
    reg_wc_min = reg_ru["worst_case"]["min_recall"]
    reg_wc_rate = reg_ru["worst_case"]["leaked_per_10k_chars"]
    _clients = reg_ru["wp29"]["singling_out"]["clients"]
    reg_nsingle = len(_clients)
    reg_singles = sum(1 for c in _clients if c.get("singles_out"))
else:
    reg_tier, reg_direct, reg_oos, reg_special, reg_inf, reg_link_roc = "—", 0, 0, 0, 0.0, 0.0
    reg_hip_pass = reg_hip_app = reg_wc_rate = reg_singles = reg_nsingle = 0
    reg_wc_min = 0.0
reg_tier_class = {"RED": "r", "AMBER": "a", "GREEN": "g"}.get(reg_tier, "b")


# RU default per-type fn list for the flyout
def llm_required_line():
    if not RU:
        return ""
    nr = RU["combos"]["natasha+regex"]["coverage_relaxed_per_type"]
    bits = []
    for ty in ("AGE", "MEDICATION", "PROFESSION"):
        if ty in nr:
            bits.append(f"{ty.lower()} {nr[ty]['r']:.0%}")
    return ", ".join(bits)


def _th(col):
    """Column header carrying its glossary tooltip + a higher/lower-is-better
    arrow, so every abbreviation is self-explaining on hover and at a glance."""
    tip, direction = COL_GLOSSARY[col]
    label = col.replace(" ", "&nbsp;")
    arrow = f"<span class='dir'>{direction}</span>" if direction != "·" else ""
    full = f"{t(tip)} ({t(DIR_WORD[direction])})"
    return f"<th title=\"{full}\" aria-label=\"{full}\">{label}{arrow}</th>"


def _legend(cols):
    """Visible (printable) glossary under the table — tooltips alone vanish in
    print/PDF, and the column key states higher/lower-is-better explicitly."""
    items = []
    for c in cols:
        tip, direction = COL_GLOSSARY[c]
        items.append(f"<li><b>{c}</b> <span class='dir'>{direction}</span> "
                     f"<span class='dw'>({t(DIR_WORD[direction])})</span> — {t(tip)}</li>")
    return (f"<details class='col-legend'><summary>{t('column key — what each '
            'abbreviation means, and which direction is better')}</summary>"
            f"<ul>{''.join(items)}</ul></details>")


def leaderboard_table(res, title):
    rows = combos_clean(res)
    has_ent = any("entity_level" in e for _, e in rows)
    cols = ["cov R", "cov F2"] + (["ent R", "direct", "quasi"] if has_ent else []) + ["preds"]
    head = "<tr><th style='text-align:left'>combo</th>" + "".join(_th(c) for c in cols) + "</tr>"
    body = []
    for n, e in rows:
        cls = " class='highlight-row'" if "★" in n else ""
        cr = e["coverage_relaxed"]
        # name the model behind the "ollama" layer inline.
        disp = n.replace("ollama", f"ollama·{OLLAMA_MODEL}") if "ollama" in n else n
        cells = [f"<td style='text-align:left'>{disp}</td>",
                 f"<td>{cr['r']:.3f}</td>", f"<td>{cr['f2']:.3f}</td>"]
        if has_ent and "entity_level" in e:
            el = e["entity_level"]
            cells += [f"<td>{el['entity_recall']:.3f}</td>",
                      f"<td>{el['by_class'].get('direct',{}).get('recall',0):.3f}</td>",
                      f"<td>{el['by_class'].get('quasi',{}).get('recall',0):.3f}</td>"]
        elif has_ent:
            cells += ["<td>—</td>", "<td>—</td>", "<td>—</td>"]
        cells.append(f"<td>{e['n_pred']}</td>")
        body.append(f"<tr{cls}>" + "".join(cells) + "</tr>")
    return (f"<div class='table-wrapper'><table><thead>{head}</thead>"
            f"<tbody>{''.join(body)}</tbody></table></div>{_legend(cols)}")


def regulatory_compare_table():
    """All three datasets side by side — the residual-risk tier is a per-language
    result, but the report previously surfaced only RU. (Audit gap fix.)"""
    rows = []
    for ds, label in (("ru", "RU"), ("en", "EN-synth"), ("en-real", "EN-real")):
        r = (REG or {}).get("datasets", {}).get(ds)
        if not r:
            continue
        tt, hip, wc = r["tier"], r["hipaa"], r["worst_case"]
        inf = r["wp29"]["inference"]["rate"]
        roc = r["wp29"]["linkability"].get("roc_auc")
        tcls = {"RED": "tier-r", "AMBER": "tier-a", "GREEN": "tier-g"}.get(tt["tier"], "")
        rows.append(
            f"<tr><td style='text-align:left'>{label}</td>"
            f"<td><span class='{tcls}'>{tt['tier']}</span></td>"
            f"<td>{tt['direct_residual']}</td><td>{tt['special_residual']}</td>"
            f"<td>{hip['passed']}/{hip['applicable']}</td>"
            f"<td>{wc['min_recall']:.0%}</td>"
            f"<td>{inf:.0%}</td>"
            f"<td>{(roc if roc is not None else 0.0):.2f}</td></tr>")
    if not rows:
        return ""
    # tooltips precomputed (translated) so the f-string carries no nested escapes
    tip_tier = t("Ordinal residual-risk tier: RED=a direct identifier leaks at entity level; AMBER=special-category residual / nonzero inference / linkability above chance; GREEN=all clear (lower is better)")
    tip_direct = t("Direct-identifier entities still leaking at entity level — each is a re-identification key (lower is better)")
    tip_special = t("Special-category (sensitive) residual entities still leaking (lower is better)")
    tip_hipaa = t("HIPAA-inspired Safe-Harbor categories fully removed / applicable — illustrative, not a legal determination (higher is better)")
    tip_worst = t("Worst single document's containment recall — the weakest doc, not the average (higher is better)")
    tip_inf = t("Attribute-recovery inference attack success rate on redacted text (lower is better)")
    tip_link = t("Pairwise session-linking ROC AUC; 0.50 = chance, which is the safe direction (lower/≈0.50 is better)")
    head = (f"<tr><th style='text-align:left'>{t('dataset')}</th>"
            f"<th title=\"{tip_tier}\">tier</th>"
            f"<th title=\"{tip_direct}\">direct&nbsp;res</th>"
            f"<th title=\"{tip_special}\">special&nbsp;res</th>"
            f"<th title=\"{tip_hipaa}\">HIPAA</th>"
            f"<th title=\"{tip_worst}\">worst&nbsp;doc</th>"
            f"<th title=\"{tip_inf}\">inf&nbsp;rate</th>"
            f"<th title=\"{tip_link}\">link&nbsp;AUC</th></tr>")
    return (f"<div class='table-wrapper'><table><thead>{head}</thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def build_html(lang):
  set_lang(lang)
  # values interpolated into translated prose (numbers stay out of the catalog key)
  en_docs = EN["n_docs"] if EN else 0
  en_gold = EN["n_gold_mentions"] if EN else 0
  enr_docs = ENR["n_docs"] if ENR else 0
  enr_gold = ENR["n_gold_mentions"] if ENR else 0
  radv_docs = RUADV["n_docs"] if RUADV else 0
  radv_gold = RUADV["n_gold_mentions"] if RUADV else 0
  adv_caught = (int(round(RUADV["combos"]["natasha+regex+ollama ★"]["entity_level"]["entity_recall"]
                          * RUADV["n_gold_mentions"])) if RUADV else 0)
  rec_a = (REC["A_quasi_survival"]["a"]["survival_rate"] if REC else 0)
  rec_b = (REC["A_quasi_survival"]["b"]["survival_rate"] if REC else 0)
  reg_entity_word = t("entity") if reg_direct == 1 else t("entities")
  if ru_opf_valid:
      ru_opf_note = t("Adding OPF reaches {r}, but OPF is an optional comparison layer "
                      "rather than the local-first default.", r=format(ru_opf_r, ".0%"))
  else:
      ru_opf_note = t("The OPF-on-RU row is omitted until its detector cache is regenerated "
                      "for the current 30-document corpus.")
  # EN-real is optional (built locally from ai4privacy; absent in the public repo).
  # Render every EN-real-specific block ONLY when its data is present, so the report
  # never shows a blank chart, an empty legend series, or a dangling header.
  if ENR:
      enr_table_block = (f'<p class="sub-h">{t("EN-real (ai4privacy slice) — {docs} docs, {gold} gold mentions", docs=enr_docs, gold=enr_gold)}</p>\n'
                         + leaderboard_table(ENR, "EN-real"))
      enr_bullet = f'<p>{t("<strong>EN-real:</strong> on generic ai4privacy text the LLM is strongest; <code>opf+ollama</code> and the default <em>tie</em> on recall.")}</p>'
      enr_base_block = (f'<div class="chart-box" style="margin-top:1.2rem"><canvas id="baseENR"></canvas></div>\n'
                        f'  <p class="caption">{t("EN-real (ai4privacy): same two metrics. Presidio\'s coverage drops sharply on real-world markup/ID formats.")}</p>')
      enr_aside = f'<p>{t("On <strong>EN-real</strong>, Presidio <em>collapses</em> on coverage — generic NER + structured recognizers miss the bespoke ID/markup formats the stack catches.")}</p>'
      baselines_stateline = t("Off-the-shelf de-identifiers can match the stack on <strong>coverage</strong> but fall far behind on <strong>type-aware micro-F1</strong> — and Presidio <em>collapses</em> on the real ai4privacy slice.")
  else:
      enr_table_block = enr_bullet = enr_base_block = enr_aside = ""
      baselines_stateline = t("Off-the-shelf de-identifiers can match the stack on <strong>coverage</strong> but fall far behind on <strong>type-aware micro-F1</strong>.")
  # RU-real (JayGuard): external, anonymized, real-but-non-clinical RU text — the
  # Russian counterpart to the (removed) en-real anchor. Rendered only when present.
  if RUREAL:
      rr_docs = RUREAL["n_docs"]
      rr_gold = RUREAL["n_gold_mentions"]
      rureal_block = (f'<p class="sub-h">{t("RU-real (JayGuard slice) — {docs} docs, {gold} gold mentions", docs=rr_docs, gold=rr_gold)} '
                      f'<span class="note-inline">{t("(external, anonymized, real-but-non-clinical Russian text — Apache-2.0; PERSON/LOCATION only, machine-derived gold, not human-adjudicated)")}</span></p>\n'
                      + leaderboard_table(RUREAL, "RU-real"))
      rureal_bullet = f'<p>{t("<strong>RU-real (JayGuard):</strong> on external real Russian text the local stack reaches strong coverage — a real-text anchor for the otherwise-synthetic RU corpus (PERSON/LOCATION only).")}</p>'
  else:
      rureal_block = rureal_bullet = ""
  # Disclaimer adapts to whether a real-text slice is included.
  if RUREAL:
      whatisnot = t("<strong>Not a HIPAA/GDPR compliance certificate.</strong> The therapy transcripts are synthetic/fictional and samples are small — treat results as directional. The one real-text exception is the external RU-real (JayGuard) slice: anonymized, non-clinical public data.")
      synth_note = t("Therapy transcripts are synthetic/fictional — no real patient data; the one real-text slice (RU-real / JayGuard) is external, anonymized, non-clinical public data.")
  else:
      whatisnot = t("<strong>Not a HIPAA/GDPR compliance certificate.</strong> All transcripts are synthetic/fictional and samples are small — treat results as directional.")
      synth_note = t("All transcripts are synthetic/fictional — no real patient data.")
  return f"""<!DOCTYPE html>
<html lang="{lang}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t("CONFIDE-Bench — De-identification Layer Benchmark")}</title>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
@font-face {{ font-family:'Monaspace Argon'; src:url('https://cdn.jsdelivr.net/gh/githubnext/monaspace@v1.101/fonts/webfonts/MonaspaceArgon-Regular.woff2') format('woff2'); font-weight:400; font-display:swap; }}
:root {{ --ink:#1a1a1a; --ink-light:#555; --ink-muted:#888; --bg:#fffff8; --bg-aside:#f9f6ee; --accent:#a00; --rule:#ccc;
  --c1:#c45a28; --c2:#2a7a5a; --c3:#5a5aaa; --red:#a02a2a; --amber:#c89000; --green:#2a7a3a; }}
* {{ box-sizing:border-box; }}
body {{ background:var(--bg); color:var(--ink); font-family:'EB Garamond',serif; font-size:18px; line-height:1.6;
  max-width:1200px; margin:0 auto; padding:2rem 1.5rem 4rem; }}
h1 {{ font-size:2.2rem; font-variant:small-caps; font-weight:400; margin:0 0 .2rem; }}
h2 {{ font-size:1.5rem; font-variant:small-caps; font-weight:400; border-top:1px solid var(--rule); padding-top:1.4rem; margin-top:2.4rem; }}
.sub {{ color:var(--ink-light); font-style:italic; font-size:1.15rem; margin:0 0 .6rem; }}
.tags {{ font-family:'Monaspace Argon',monospace; font-size:.65rem; color:var(--rule); letter-spacing:.04em; }}
.state-line {{ font-size:1.35rem; font-style:italic; line-height:1.45; color:var(--ink-light); margin:1.2rem 0 1.6rem; max-width:760px; }}
.state-line strong {{ font-weight:400; font-style:normal; color:var(--ink); }}
.status-strip {{ display:grid; grid-template-columns:repeat(4,1fr); border:1px solid var(--rule); margin:1.5rem 0; }}
.status-cell {{ padding:.9rem 1rem; border-left:3px solid var(--rule); }}
.status-cell:not(:last-child) {{ border-right:1px solid #eee; }}
.status-label {{ font-size:.78rem; font-variant:small-caps; color:var(--ink-muted); }}
.status-value {{ font-family:'Monaspace Argon',monospace; font-size:1.5rem; }}
.status-note {{ font-size:.78rem; color:var(--ink-light); font-style:italic; }}
.g {{ border-left-color:var(--green); }} .a {{ border-left-color:var(--amber); }} .r {{ border-left-color:var(--red); }} .b {{ border-left-color:var(--c3); }}
.aside-container {{ display:grid; grid-template-columns:1fr 280px; gap:2rem; align-items:start; margin:1.2rem 0; }}
.aside {{ font-size:.9rem; line-height:1.55; color:var(--ink-light); }}
.aside .t {{ font-variant:small-caps; letter-spacing:.06em; font-size:.82rem; color:var(--ink); margin-bottom:.4rem; }}
.aside p {{ margin:.5rem 0; }} .aside strong {{ color:var(--ink); }}
.chart-box {{ position:relative; height:340px; }}
.caption {{ font-size:.82rem; font-style:italic; color:var(--ink-muted); text-align:center; margin:.4rem 0 0; }}
table {{ border-collapse:collapse; width:100%; font-size:.92rem; }}
th {{ font-variant:small-caps; color:var(--ink-muted); font-weight:400; text-align:right; padding:.3rem .5rem; border-bottom:1px solid var(--rule); }}
td {{ font-family:'Monaspace Argon',monospace; font-variant-numeric:tabular-nums; text-align:right; padding:.28rem .5rem; border-bottom:1px solid #eee; }}
td:first-child {{ font-family:'EB Garamond',serif; }}
.highlight-row td {{ background:#f4efe0; }}
.table-wrapper {{ overflow-x:auto; }}
th[title] {{ cursor:help; border-bottom:1px dotted var(--ink-muted); }}
.dir {{ font-family:'Monaspace Argon',monospace; font-size:.7em; color:var(--c2); padding-left:.15em; }}
.col-legend {{ font-size:.82rem; color:var(--ink-light); margin:.5rem 0 0; }}
.col-legend summary {{ font-style:italic; color:var(--ink-muted); cursor:pointer; }}
.col-legend ul {{ list-style:none; margin:.5rem 0 0; padding:0; columns:2; column-gap:2rem; }}
.col-legend li {{ margin:.3rem 0; break-inside:avoid; line-height:1.4; }}
.col-legend b {{ font-family:'Monaspace Argon',monospace; font-size:.85em; color:var(--ink); }}
.col-legend .dw {{ color:var(--ink-muted); font-style:italic; }}
.sub-h {{ font-variant:small-caps; letter-spacing:.04em; font-size:1.05rem; color:var(--ink); margin:1.6rem 0 .4rem; }}
.note-inline {{ font-variant:normal; letter-spacing:0; font-size:.82rem; font-style:italic; color:var(--ink-muted); }}
.tier-r {{ color:var(--red); font-weight:600; }} .tier-a {{ color:var(--amber); font-weight:600; }} .tier-g {{ color:var(--green); font-weight:600; }}
@media print {{ .col-legend[open] ul, .col-legend ul {{ display:block; }} .col-legend summary {{ display:none; }} }}
@media(max-width:800px){{ .col-legend ul {{ columns:1; }} }}
.flyout {{ background:var(--bg-aside); border:1px solid var(--rule); border-left:3px solid var(--accent); padding:1rem 1.2rem; margin:1.4rem 0; }}
.flyout .t {{ font-variant:small-caps; letter-spacing:.06em; color:var(--accent); font-size:.85rem; margin-bottom:.3rem; }}
.ornament {{ text-align:center; color:var(--rule); font-family:'Monaspace Argon',monospace; margin:2rem 0; letter-spacing:.3em; }}
code {{ font-family:'Monaspace Argon',monospace; font-size:.82em; background:#f0ece0; padding:.05em .3em; }}
.lede::first-letter {{ font-size:3.2rem; float:left; line-height:.8; padding:.05em .12em 0 0; }}
.credit {{ font-size:.9rem; color:var(--ink-light); margin:.1rem 0 1.2rem; }}
.credit a {{ color:var(--accent); text-decoration:none; border-bottom:1px solid #e5cccc; }}
.credit a:hover {{ border-bottom-color:var(--accent); }}
.provenance {{ font-size:.85rem; color:var(--ink-light); margin:.1rem 0 1rem; line-height:1.5; }}
.intro {{ border:1px solid var(--rule); background:var(--bg-aside); padding:1.1rem 1.3rem; margin:1.6rem 0; }}
.intro .tldr {{ font-size:1.18rem; margin:0 0 .85rem; line-height:1.45; }}
.wwn {{ display:grid; grid-template-columns:max-content 1fr; gap:.4rem 1.1rem; margin:0; font-size:.96rem; }}
.wwn dt {{ font-variant:small-caps; letter-spacing:.04em; color:var(--accent); white-space:nowrap; }}
.wwn dd {{ margin:0; color:var(--ink-light); }} .wwn dd strong {{ color:var(--ink); }}
.howto {{ font-size:.88rem; color:var(--ink-light); margin:.95rem 0 0; border-top:1px solid var(--rule); padding-top:.7rem; }}
@media(max-width:800px){{ .wwn {{ grid-template-columns:1fr; gap:.05rem .5rem; }} .wwn dt {{ margin-top:.45rem; }} }}
.refs {{ font-size:.9rem; line-height:1.5; }}
.refs h3 {{ font-size:1rem; font-variant:small-caps; letter-spacing:.04em; color:var(--ink); margin:1.4rem 0 .5rem; border-bottom:1px solid #eee; padding-bottom:.2rem; }}
.refs ul {{ list-style:none; margin:.2rem 0 1rem; padding:0; }}
.refs li {{ margin:.45rem 0; padding-left:1.1rem; text-indent:-1.1rem; }}
.refs a {{ color:var(--accent); text-decoration:none; border-bottom:1px solid #e5cccc; }}
.refs a:hover {{ border-bottom-color:var(--accent); }}
.refs .meta {{ color:var(--ink-muted); font-style:italic; }}
footer {{ border-top:1px solid var(--rule); margin-top:3rem; padding-top:1rem; font-size:.8rem; color:var(--ink-muted); }}
footer a {{ color:var(--ink-light); }}
@media(max-width:800px){{ .status-strip{{grid-template-columns:repeat(2,1fr)}} .aside-container{{grid-template-columns:1fr}} }}
</style></head><body>

<h1>{t("CONFIDE-Bench — Which Layer Earns Its Compute?")}</h1>
<p class="sub">{t("A bilingual de-identification benchmark for psychotherapy transcripts.")}</p>
<p class="credit">{t('<strong>CONFIDE</strong> · {repo} · by {author} &amp; CONFIDE contributors · released for research &amp; teaching under the repository license. {synth}', repo='<a href="https://github.com/glebis/confide">github.com/glebis/confide</a>', author='<a href="https://github.com/glebis">Gleb Kalinin</a>', synth=synth_note)}</p>
<p class="tags">TAB · i2b2/n2c2 · Presidio-F2 · Datasheets&nbsp;for&nbsp;Datasets</p>
<p class="provenance">{t('LLM detector layer (<code>ollama</code>) &amp; local attacker: <strong>Qwen2.5-3B-Instruct</strong> (<code>{model}</code>) via Ollama, temperature&nbsp;0. Deterministic layers: <strong>Natasha</strong> (Russian NER), a bilingual <strong>regex</strong> layer, and the <strong>OpenAI Privacy&nbsp;Filter</strong> (English).', model=OLLAMA_MODEL)}</p>

<div class="intro">
<p class="tldr"><strong>TL;DR —</strong> {t("we test how well automatic privacy tools hide personal details in psychotherapy session transcripts (Russian &amp; English), and which combination of tools earns its compute.")}</p>
<dl class="wwn">
  <dt>{t("What we measure")}</dt><dd>{t("Did the redaction mask actually cover each piece of personal information? — recall-first, because a miss is leaked data.")}</dd>
  <dt>{t("Why it matters")}</dt><dd>{t("Therapy text is deeply sensitive; one un-hidden name, phone, or medication can re-identify a client.")}</dd>
  <dt>{t("What it is NOT")}</dt><dd>{whatisnot}</dd>
  <dt>{t("Who it is for")}</dt><dd>{t("Anyone choosing or building a de-identification pipeline for clinical or therapy text.")}</dd>
</dl>
<p class="howto"><strong>{t("How to read this")}:</strong> {t("★ marks the recommended default stack · bars show coverage (higher is better) · a blank bar means that combination was not run for that language · every table has a column key explaining its abbreviations.")}</p>
</div>

<div class="status-strip">
  <div class="status-cell b"><div class="status-label">{t("datasets")}</div><div class="status-value">4</div><div class="status-note">RU · RU-adv · EN · RU-real</div></div>
  <div class="status-cell b"><div class="status-label">{t("combos × dataset")}</div><div class="status-value">{n_combos}</div><div class="status-note">{t("union-composed ablation")}</div></div>
  <div class="status-cell g"><div class="status-label">{t("RU default recall")}</div><div class="status-value">{ru_default_r:.0%}</div><div class="status-note">{RU_STAR}</div></div>
  <div class="status-cell r"><div class="status-label">{t("quasi-ID survival")}</div><div class="status-value">{surv_comb:.0%}</div><div class="status-note">{t("both clients · re-id surface")}</div></div>
</div>

<p class="lede">{t("De-identification is not one tool but a stack of detectors, and the honest question is which layer pays for the CPU it burns. This benchmark composes detector layers by span-union over psychotherapy transcripts in Russian and English, scores each combination the way published de-id work does — recall-first, entity-level, direct vs quasi — and asks a sharper question than &ldquo;how good is the tool&rdquo;: <em>what can only an LLM catch, and what still leaks after we redact?</em>")}</p>

<div class="flyout"><div class="t">{t("headline")}</div>
<p>{t("Three PII types — <strong>{types}</strong> — are near-zero under the deterministic layers (Natasha&nbsp;NER + regex). Adding the local qwen layer raises their mention-recall, but medication and profession still have very low <em>entity</em>-recall because every mention must be masked. Meanwhile <strong>{surv}</strong> of quasi-identifiers still survive the default stack. Redaction of direct identifiers is necessary but not sufficient.", types=llm_required_line(), surv=f"{surv_comb:.0%}")}</p></div>

<h2>1. {t("Which layer catches what")}</h2>
<p class="state-line">{t("The LLM layer is what moves <strong>age</strong>, <strong>medication</strong>, and <strong>profession</strong> above the deterministic baseline.")}</p>
<div class="aside-container">
  <div><div class="chart-box"><canvas id="whoCatches"></canvas></div>
  <p class="caption">{t("RU per-category <em>mention</em> recall (relaxed overlap), {gold} gold mentions: deterministic (Natasha+regex) vs. +qwen.", gold=n_gold)}</p></div>
  <div class="aside"><div class="t">{t("reading it")}</div>
  <p>{t("<strong>Structured direct IDs</strong> (email, phone, policy ID) and <strong>names/orgs/locations</strong> reach 0.9–1.0 from regex + Natasha. <strong>Dates</strong> are now caught too — a numeric-date regex rule was added after the benchmark exposed the gap.")}</p>
  <p>{t("<strong>Quasi-identifiers needing world-knowledge</strong> — a drug name, an occupation, a spelled-out age — are invisible to pattern and NER layers; the LLM is the only layer that lifts their mention-recall.")}</p>
  <p>{t("<strong>Caveat:</strong> this is <em>mention</em> recall. At <em>entity</em> level (all mentions masked), medication and profession stay at 0 even with qwen — a higher bar.")}</p></div>
</div>

<div class="ornament">:::</div>

<h2>2. {t("Best sequence per language")}</h2>
<p class="state-line">{t("Bars show <strong>coverage recall</strong>; ★ is the <em>proposed default</em>, which trades a little recall for large speed/precision gains — not always the single highest bar.")}</p>
<div class="aside-container">
  <div><div class="chart-box"><canvas id="boards"></canvas></div>
  <p class="caption">{t("Coverage recall by combination across the plotted datasets. A missing bar means that combination was <em>not run</em> on that language (see note), not a zero score. ★ = proposed default; see table for F2/precision.")}</p></div>
  <div class="aside"><div class="t">{t("why some bars are blank for RU")}</div>
  <p>{t("Russian runs only the <strong>local-first stack</strong> — Natasha&nbsp;+&nbsp;regex&nbsp;+&nbsp;{model}. Three detectors are <strong>English-only by design</strong>, so any combo containing them has no RU bar: <strong>Presidio</strong> (its RU is spaCy-NER-dependent and weak — left unscored rather than misrepresented), <strong>Philter</strong> (an English clinical-notes rule set), and the <strong>OpenAI Privacy&nbsp;Filter</strong> (an English token-classifier). This is a scope decision, not a measured RU failure.", model=OLLAMA_MODEL)}</p>
  <div class="t">{t("why they differ")}</div>
  <p>{t("<strong>RU:</strong> the proposed default <code>{star}</code> reaches {r} coverage recall. {opf_note}", star=RU_STAR, r=f"{ru_default_r:.0%}", opf_note=ru_opf_note)}</p>
  <p>{t("<strong>EN-synth:</strong> OPF is the name/address backbone (English&rsquo;s Natasha). Default <code>{star}</code>; <code>opf+regex</code> edges it on F2.", star=EN_STAR)}</p>
  {enr_bullet}
  {rureal_bullet}</div>
</div>
{leaderboard_table(RU, "RU") if RU else ""}

{rureal_block}

<p class="sub-h">{t("EN-synth — {docs} docs, {gold} gold mentions", docs=en_docs, gold=en_gold)} <span class="note-inline">{t("(no entity-level / direct-quasi: the EN sets carry no per-entity <code>entity_id</code> annotation, so only mention-level coverage is scored)")}</span></p>
{leaderboard_table(EN, "EN") if EN else ""}

{enr_table_block}

<div class="ornament">:::</div>

<h2>2b. {t("Adversarial robustness (RU)")}</h2>
<p class="state-line">{t("On the hard-forms probe the full stack catches <strong>{n}/{total}</strong> adversarial identifiers — the lone leak is a Latin-transliterated Russian name.", n=adv_caught, total=radv_gold)}</p>
<div class="aside-container">
  <div>{leaderboard_table(RUADV, "RU-adv") if RUADV else f'<em>{t("RU-adversarial set not scored.")}</em>'}</div>
  <div class="aside"><div class="t">{t("what the probe contains")}</div>
  <p>{t("<strong>{docs} snippets, {gold} gold forms:</strong> patronymics, transliteration, diminutives, VK/Telegram handles, SNILS/INN/passport IDs, abbreviated addresses, and code-switching.", docs=radv_docs, gold=radv_gold)}</p>
  <p>{t("Regex catches the structured IDs and handles; Natasha&nbsp;+&nbsp;{model} recover patronymics, diminutives and code-switching. The <strong>one residual leak</strong> is <em>“Sergey Volkov”</em> — a Latin-transliterated Russian name: Natasha is Cyrillic-only, regex has no name rule, and qwen missed it. This is the argument for adding an English/Latin NER (OPF) when transliteration is expected.", model=OLLAMA_MODEL)}</p></div>
</div>

<div class="ornament">:::</div>

<h2>3. {t("Direct vs quasi-identifiers (TAB)")}</h2>
<p class="state-line">{t("Direct identifiers reach <strong>{d}</strong> entity recall; quasi-identifiers remain lower at <strong>{q}</strong>.", d=f"{ru_direct:.2f}", q=f"{ru_quasi:.2f}")}</p>
<div class="aside-container">
  <div><div class="chart-box"><canvas id="directQuasi"></canvas></div>
  <p class="caption">{t("RU entity-level recall (an entity is protected only if all mentions are masked) by identifier class.")}</p></div>
  <div class="aside"><div class="t">{t("the asymmetry")}</div>
  <p>{t("<strong>Direct</strong> (name, phone, email, policy): masked at {d} entity recall in the default stack.", d=f"{ru_direct:.2f}")}</p>
  <p>{t("<strong>Quasi</strong> (age, profession, city, employer, medication, date): the LLM helps but the ceiling stays low — these are the attributes that, combined, re-identify a person.")}</p></div>
</div>

<div class="ornament">:::</div>

<h2>4. {t("What survives — reconstruction &amp; re-identification")}</h2>
<p class="state-line">{t("<strong>{surv}</strong> of quasi-identifiers survive the default stack (both clients); over-redaction costs <strong>{over}</strong> of redactions.", surv=f"{surv_comb:.0%}", over=f"{overred:.0%}")}</p>
<div class="status-strip">
  <div class="status-cell r"><div class="status-label">{t("quasi survival (A)")}</div><div class="status-value">{rec_a:.0%}</div><div class="status-note">{t("client A · re-id surface")}</div></div>
  <div class="status-cell r"><div class="status-label">{t("quasi survival (B)")}</div><div class="status-value">{rec_b:.0%}</div><div class="status-note">{t("client B")}</div></div>
  <div class="status-cell a"><div class="status-label">{t("over-redaction (C)")}</div><div class="status-value">{overred:.0%}</div><div class="status-note">{t("readability cost")}</div></div>
  <div class="status-cell b"><div class="status-label">{t("attacker")}</div><div class="status-value" style="font-size:1.1rem">{OLLAMA_MODEL}</div><div class="status-note">{t("Qwen2.5-3B · recovers attrs from redacted text")}</div></div>
</div>
<div class="aside-container">
  <div class="aside" style="border:none">
  <p style="font-size:.95rem">{t("<strong>Method</strong> — following the re-identification / inference-attack literature (Staab et al.; RAT-Bench; Tau-Eval). An entity <em>survives</em> if any one of its mentions is left unmasked.")}</p></div>
  <div class="aside"><div class="t">{t("interpretation")}</div>
  <p>{t("A local 3B qwen attacker recovered <strong>{rec} of {tot}</strong> tested attributes from the <em>redacted</em> text (e.g. the medication, because its entity-recall is 0). A weak attacker is a lower bound — the inference-attack literature (Staab et al.) reports much higher re-identification rates for frontier models.", rec=atk_rec, tot=atk_tot)}</p>
  <p>{t("<strong>Implication:</strong> redacting direct identifiers is table stakes; quasi-identifier survival is a useful gate to check before sending a session to cloud analysis.")}</p></div>
</div>

<div class="ornament">:::</div>

<h2>5. {t("Privacy vs utility — can you de-identify and still analyze?")}</h2>
<p class="state-line">{t("A weak local attacker recovers <strong>{top3}/{n}</strong> attributes (top-3); yet <strong>{util}</strong> of the clinical signal survives redaction.", top3=pu_top3, n=pu_n, util=f"{pu_util:.0%}")}</p>
<div class="status-strip">
  <div class="status-cell g"><div class="status-label">{t("CBT-signal preserved")}</div><div class="status-value">{pu_util:.0%}</div><div class="status-note">{t("distortion types, redacted vs orig")}</div></div>
  <div class="status-cell g"><div class="status-label">{t("non-PII text kept")}</div><div class="status-value">{pu_cnp:.1%}</div><div class="status-note">{t("char-level utility floor")}</div></div>
  <div class="status-cell b"><div class="status-label">{t("attack top-3")}</div><div class="status-value">{pu_top3}/{pu_n}</div><div class="status-note">{t("{model}, lower bound", model=OLLAMA_MODEL)}</div></div>
  <div class="status-cell a"><div class="status-label">{t("residual risk")}</div><div class="status-value" style="font-size:1.1rem">{pu_risk}</div><div class="status-note">{t("client A / B")}</div></div>
</div>
<div class="aside-container">
  <div class="aside" style="border:none">
  <p style="font-size:.95rem">{t("<strong>Method</strong> — top-k inference attack with a fixed, declared budget ({model}, temp 0.4, top-3 guesses/attribute, redacted text only) + downstream task preservation (re-run cognitive-distortion extraction on redacted vs. original). Aligned with Staab et al. / RAT-Bench (privacy) and Tau-Eval (task-sensitive utility).", model=OLLAMA_MODEL)}</p></div>
  <div class="aside"><div class="t">{t("the tension, resolved")}</div>
  <p>{t("The same masking that lowers attacker success can erase clinical content. Here it does <em>not</em>: the default stack keeps ~{util} of distortion signal and {cnp} of non-PII text while a weak attacker recovers nothing top-3.", util=f"{pu_util:.0%}", cnp=f"{pu_cnp:.1%}")}</p>
  <p>{t("<strong>Caveat:</strong> this attacker is a lower bound — quasi-identifiers still survive in text (medication entity-recall is 0), so a frontier attacker would score higher. Residual risk stays MEDIUM for client B.")}</p></div>
</div>

<div class="ornament">:::</div>

<h2>6. {t("CONFIDE stack vs established baselines (Presidio, Philter)")}</h2>
<p class="state-line">{baselines_stateline}</p>
<div class="aside-container">
  <div><div class="chart-box"><canvas id="baseEN"></canvas></div>
  <p class="caption">{t("EN-synth: coverage F2 (recall-weighted, headline) vs type-aware micro-F1 for the CONFIDE ★ stack and the established baselines.")}</p>
  {enr_base_block}</div>
  <div class="aside"><div class="t">{t("reading it")}</div>
  <p>{t("<strong>Coverage F2</strong> (orange) asks only &ldquo;did we mask the span at all&rdquo;. <strong>Type micro-F1</strong> (green) demands the right label too — what a redaction policy actually needs.")}</p>
  <p>{t("On <strong>EN-synth</strong>, Presidio edges the stack on coverage F2 (a broad <code>DATE_TIME</code> recognizer) but its type-F1 is far lower; <strong>Philter</strong> is high-coverage yet emits almost everything as untyped <code>OTHER</code>, so its type-F1 is unusable.")}</p>
  {enr_aside}
  <p>{t("<strong>Takeaway:</strong> a generic system is not a therapy-tuned one; the only coverage a baseline adds is relative/colloquial dates.")}</p></div>
</div>

<div class="ornament">:::</div>

<h2 id="regulatory">7. {t("Regulatory residual-risk (RU · EN)")}</h2>
<p class="state-line">{t("Detection metrics measure what we catch; regulators care what <em>survives</em>. Mapped onto named risks, the RU default stack lands at <strong>{tier}</strong> — driven by {direct} in-scope residual direct-identifier {word} (a re-identification key left in the text). A further {oos} are spelled-out digit IDs, out of scope for the regex layer by design and reported separately.", tier=reg_tier, direct=reg_direct, word=reg_entity_word, oos=reg_oos)}</p>
<p class="sub-h">{t("All datasets, side by side")}</p>
{regulatory_compare_table()}
<p class="caption" style="text-align:left">{t("Per-language residual-risk tier under each language's ★ default stack. RU lands <strong>RED</strong> (direct identifiers leak at the strict TAB entity bar); EN lands <strong>AMBER</strong> (no direct-ID leak, but nonzero inference / incomplete HIPAA coverage). EN's worst-doc recall reads 0% because its tiny gold means one PII-bearing doc can be missed entirely — small-N noise, not a systematic EN failure. The RU detail follows.")}</p>
<div class="status-strip">
  <div class="status-cell {reg_tier_class}"><div class="status-label">{t("residual-risk tier")}</div><div class="status-value">{reg_tier}</div><div class="status-note">{t("ordinal R/A/G · RU ★ stack")}</div></div>
  <div class="status-cell b"><div class="status-label">{t("HIPAA-inspired coverage")}</div><div class="status-value">{reg_hip_pass}/{reg_hip_app}</div><div class="status-note">{t("categories fully removed")}</div></div>
  <div class="status-cell r"><div class="status-label">{t("worst-doc recall")}</div><div class="status-value">{reg_wc_min:.0%}</div><div class="status-note">{t("containment · {rate} leaks / 10k chars", rate=reg_wc_rate)}</div></div>
  <div class="status-cell a"><div class="status-label">{t("singled out")}</div><div class="status-value">{reg_singles}/{reg_nsingle}</div><div class="status-note">{t("clients · residual quasi surface")}</div></div>
</div>
<div class="aside-container">
  <div class="aside" style="border:none">
  <p style="font-size:.95rem">{t("<strong>WP29 (Art-29 WP 05/2014) re-identification triad</strong> — identifiability decomposes into <em>singling out</em> (residual quasi surface via a caveated population-fraction estimator — NOT corpus k-anonymity, N is tiny), <em>linkability</em> (pairwise session-linking ROC&nbsp;AUC {roc}; at or below 0.50 = chance, which is the safe direction), and <em>inference</em> (attribute-recovery attack recovers {inf}). HIPAA coverage is a Safe-Harbor-<em>inspired</em> checklist, not a legal determination (AGE is N/A; structured IDs collapsed).", roc=f"{reg_link_roc:.2f}", inf=f"{reg_inf:.0%}")}</p></div>
  <div class="aside"><div class="t">{t("reading the tier")}</div>
  <p>{t("<strong>RED</strong> = any in-scope direct identifier leaks at entity level (one unmasked mention is a key). <strong>AMBER</strong> = special-category residual, nonzero inference, or linkability above chance. <strong>GREEN</strong> = all clear.")}</p>
  <p>{t("<strong>What leaks:</strong> not whole names but specific <em>variants</em> — inflected/possessive/patronymic forms (Артёмом, Натальин, Денису), lowercase surnames, vocatives, Latin transliteration (Timur), and name/common-word collisions (Вера, Роман). Mention-level recall hides this; the strict TAB entity bar (one miss ⇒ unprotected) surfaces it.")}</p>
  <p>{t("The singling-out estimate is illustrative (a caveated population-fraction method, not corpus k-anonymity) — it is not a guarantee of non-identifiability.")}</p></div>
</div>

<div class="flyout"><div class="t">{t("methodology")}</div>
<p>{t("Each detector runs once per dataset; combinations are span-unions of cached spans, interval-merged to the deployed redaction mask before scoring. This report headlines <strong>coverage recall</strong> (relaxed overlap) — the privacy-critical number — and recall-weighted <strong>F2</strong> + precision sit in the leaderboard table. Type-aware micro/macro-F1 (i2b2) and entity-level recall (TAB; all mentions masked) are also reported. Numbers are mention-level unless marked entity-level. Gold for RU is located from the two answer-key PII inventories and hand-verified (a planted-signal recovery eval, not independently annotated gold); the EN set is a curated synthetic slice, and the one real-text anchor is the external RU-real (JayGuard) slice. Mostly synthetic data — no real patients. Small N: treat per-type numbers as directional.")}</p></div>

<h2 id="references">{t("References &amp; credits")}</h2>
<div class="refs prose">
<p>{t("CONFIDE-Bench builds on the de-identification, re-identification, and documentation literature listed below. Every work named or relied on in this report is credited here with a link to its canonical page (DOI / arXiv / HuggingFace / GitHub). We credit only what the report actually uses; inclusion does not imply endorsement by those authors.")}</p>

<h3>{t("Benchmarks &amp; metrics")}</h3>
<ul>
  <li><strong>TAB — Text Anonymization Benchmark.</strong> Pilán, Lison, Øvrelid, Papadopoulou, Sánchez &amp; Batet (2022), <em>Computational Linguistics</em> 48(4):1053–1101. <span class="meta">{t("Source of the direct vs. quasi-identifier distinction and entity-level (all-mentions-masked) recall.")}</span> <a href="https://doi.org/10.1162/coli_a_00458">doi:10.1162/coli_a_00458</a> · <a href="https://aclanthology.org/2022.cl-4.19/">ACL Anthology</a></li>
  <li><strong>2014 i2b2/UTHealth de-identification (Track&nbsp;1).</strong> Stubbs, Kotfila &amp; Uzuner (2015), <em>J. Biomedical Informatics</em>. <span class="meta">{t("Strict entity-based de-id evaluation; comparison point for clinical-note de-id.")}</span> <a href="https://pubmed.ncbi.nlm.nih.gov/26225918/">PubMed 26225918</a></li>
  <li><strong>2016 CEGS N-GRID / n2c2 psychiatric-intake de-identification.</strong> Stubbs, Filannino &amp; Uzuner (2017), <em>J. Biomedical Informatics</em>. <span class="meta">{t("Psychiatric-intake-note de-id comparison point.")}</span> <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC5705537/">PMC5705537</a></li>
  <li><strong>MEDDOCAN.</strong> Spanish synthetic clinical-case de-identification shared task (IberLEF 2019), ~22 PHI types. <span class="meta">{t("Related clinical de-id benchmark.")}</span> <a href="https://github.com/PlanTL-GOB-ES/SPACCC_MEDDOCAN">PlanTL SPACCC_MEDDOCAN</a></li>
  <li><strong>Presidio-research (F2 evaluation).</strong> Microsoft, MIT-licensed. <span class="meta">{t("Basis for the recall-weighted F<sub>2</sub> (β=2) de-id scoring framing.")}</span> <a href="https://github.com/microsoft/presidio-research">github.com/microsoft/presidio-research</a></li>
  <li><strong>Tau-Eval.</strong> Loiseau et al. (2025), EMNLP System Demonstrations. <span class="meta">{t("Task-sensitive privacy-and-utility evaluation framing.")}</span> <a href="https://arxiv.org/abs/2506.05979">arXiv:2506.05979</a></li>
</ul>

<h3>{t("Re-identification &amp; privacy attacks")}</h3>
<ul>
  <li><strong>Staab et al. — Beyond Memorization: Violating Privacy via Inference with LLMs.</strong> ICLR 2024. <span class="meta">{t("LLM inference-attack framing; frontier attackers infer far more than the local lower-bound attacker used here.")}</span> <a href="https://arxiv.org/abs/2310.07298">arXiv:2310.07298</a></li>
  <li><strong>Anonymeter.</strong> Giomi, Boenisch, Wehmeyer &amp; Tasnádi (2022/PETS 2023), Statice. <span class="meta">{t("Attack-based singling-out / linkability / inference framing (the three GDPR risks).")}</span> <a href="https://arxiv.org/abs/2211.10459">arXiv:2211.10459</a> · <a href="https://github.com/statice/anonymeter">GitHub</a></li>
  <li><strong>RAT-Bench.</strong> Imperial College (2026 preprint). <span class="meta">{t("Attacker-based residual re-identification benchmark framing (cited as preprint evidence).")}</span> <a href="https://openreview.net/forum?id=FjbU4kLriN">OpenReview FjbU4kLriN</a></li>
</ul>

<h3>{t("Detectors &amp; tools")}</h3>
<ul>
  <li><strong>Microsoft Presidio.</strong> {t("MIT license; spaCy-backed PII detection (EN-first baseline).")} <a href="https://github.com/microsoft/presidio">github.com/microsoft/presidio</a></li>
  <li><strong>Philter / philter-lite.</strong> {t("UCSF clinical de-identification rule set; <code>philter-lite</code> is the Sirona Medical fork.")} <a href="https://github.com/SironaMedical/philter-lite">github.com/SironaMedical/philter-lite</a> · <a href="https://pypi.org/project/philter-lite/">PyPI</a></li>
  <li><strong>Natasha.</strong> {t("Russian NLP/NER toolkit (Cyrillic-only — the basis for the documented transliteration leak).")} <a href="https://github.com/natasha/natasha">github.com/natasha/natasha</a></li>
  <li><strong>OpenAI Privacy Filter (OPF), <code>openai/privacy-filter</code>.</strong> {t("Apache-2.0 token-classification PII model (used as the EN name/address backbone). The model card states it is a redaction / data-minimization aid, <em>not</em> an anonymization or compliance guarantee.")} <a href="https://huggingface.co/openai/privacy-filter">huggingface.co/openai/privacy-filter</a></li>
  <li><strong>Ollama + Qwen.</strong> {t("Local LLM runner and the Qwen model family used for the local-LLM detector layer and the local 3B re-identification attacker.")} <a href="https://ollama.com/">ollama.com</a> · <a href="https://github.com/QwenLM/Qwen2.5">QwenLM/Qwen2.5</a></li>
</ul>

<h3>{t("Datasets")}</h3>
<ul>
  <li><strong>JayGuard NER Benchmark.</strong> Just&nbsp;AI (2025), Hugging&nbsp;Face Datasets. <span class="meta">{t("External, anonymized, real-but-non-clinical conversational Russian PII dataset (Apache-2.0); the RU-real slice is built from it (PERSON/LOCATION). Used with attribution as required by the licence.")}</span> <a href="https://huggingface.co/datasets/just-ai/jayguard-ner-benchmark">huggingface.co/datasets/just-ai/jayguard-ner-benchmark</a></li>
</ul>

<h3>{t("Documentation &amp; regulatory framing")}</h3>
<ul>
  <li><strong>Datasheets for Datasets.</strong> Gebru et al. (2021), <em>CACM</em>. <a href="https://www.microsoft.com/en-us/research/publication/datasheets-for-datasets/">Microsoft Research</a></li>
  <li><strong>Data Statements for NLP.</strong> Bender &amp; Friedman (2018), <em>TACL</em>. <a href="https://aclanthology.org/Q18-1041/">ACL Anthology Q18-1041</a></li>
  <li><strong>GDPR Recital 26 &amp; WP29/EDPB anonymisation framework.</strong> {t("&ldquo;Reasonably likely means&rdquo; and the singling-out / linkability / inference triad.")} <a href="https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng">GDPR (EUR-Lex)</a> · <a href="https://www.edpb.europa.eu/sme-data-protection-guide/secure-personal-data_en">EDPB SME guide</a></li>
  <li><strong>HIPAA de-identification (Safe Harbor &amp; Expert Determination).</strong> {t("Mapping is illustrative only — benchmark success is <em>not</em> a compliance certification.")} <a href="https://www.hhs.gov/hipaa/for-professionals/privacy/special-topics/de-identification/index.html">HHS HIPAA de-id guidance</a></li>
</ul>
</div>

<footer>{t('<strong>CONFIDE-Bench</strong>, part of <a href="https://github.com/glebis/confide">CONFIDE</a> — by Gleb Kalinin &amp; CONFIDE contributors, Psychodemia 2026. Metrics &amp; methods credit: TAB (Pilán et al. 2022), i2b2/n2c2 2014/2016, Microsoft Presidio-research, Datasheets for Datasets — see References above for full links. All data is synthetic/fictional — not real patient data.')}</footer>

<script>
const DATA = {json.dumps(DATA, ensure_ascii=False)};
const C1='#c45a28', C2='#2a7a5a', C3='#5a5aaa', C4='#8a3a5a', INK='#1a1a1a', MUTE='#888';
Chart.defaults.font.family='EB Garamond, serif'; Chart.defaults.font.size=13; Chart.defaults.color=INK;
Chart.defaults.animation=false;            // Tufte: no gratuitous motion; also stops re-animation cycling
Chart.defaults.animations.colors=false; Chart.defaults.animations.x=false; Chart.defaults.animations.y=false;
Chart.defaults.transitions.active.animation.duration=0;
Chart.defaults.responsiveAnimationDuration=0;

// 1. who catches what (grouped bars)
(function(){{
 const d=DATA.ru_whocatches; if(!d.types) return;
 new Chart(document.getElementById('whoCatches'),{{type:'bar',data:{{labels:d.types,datasets:[
   {{label:d.a_name,data:d.a,backgroundColor:C3}},
   {{label:d.b_name,data:d.b,backgroundColor:C1}}]}},
  options:{{responsive:true,maintainAspectRatio:false,
   scales:{{y:{{beginAtZero:true,max:1,title:{{display:true,text:'{t("recall")}'}},grid:{{color:'#eee'}}}},x:{{grid:{{display:false}},ticks:{{maxRotation:60,minRotation:45}}}}}},
   plugins:{{legend:{{labels:{{boxWidth:8,boxHeight:8}}}}}}}}}});
}})();

// 2. leaderboards (horizontal bars, plotted datasets overlaid by combo recall)
(function(){{
 // only plot datasets that actually have data (e.g. EN-real is omitted when not built)
 const sets=[['RU',DATA.ru_leaderboard,C2],['RU-real',DATA.rureal_leaderboard,C4],['EN',DATA.en_leaderboard,C1],['EN-real',DATA.enr_leaderboard,C3]].filter(s=>s[1] && s[1].length);
 const labels=[]; sets.forEach(([_,rows])=>rows.forEach(r=>{{if(!labels.includes(r.combo))labels.push(r.combo);}}));
 const datasets=sets.map(([name,rows,col])=>({{label:name,
   data:labels.map(l=>{{const r=rows.find(x=>x.combo===l);return r?+r.recall.toFixed(3):null}}),
   backgroundColor:col}}));
 new Chart(document.getElementById('boards'),{{type:'bar',data:{{labels,datasets}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
   scales:{{x:{{beginAtZero:true,max:1,title:{{display:true,text:'{t("coverage recall")}'}},grid:{{color:'#eee'}}}},y:{{grid:{{display:false}}}}}},
   plugins:{{legend:{{labels:{{boxWidth:8,boxHeight:8}}}}}}}}}});
}})();

// 3. direct vs quasi (RU combos)
(function(){{
 const rows=DATA.ru_leaderboard.filter(r=>r.direct!==undefined);
 new Chart(document.getElementById('directQuasi'),{{type:'bar',data:{{labels:rows.map(r=>r.combo),datasets:[
   {{label:'{t("direct")}',data:rows.map(r=>r.direct),backgroundColor:C2}},
   {{label:'{t("quasi")}',data:rows.map(r=>r.quasi),backgroundColor:C1}}]}},
  options:{{responsive:true,maintainAspectRatio:false,
   scales:{{y:{{beginAtZero:true,max:1,title:{{display:true,text:'{t("entity recall")}'}},grid:{{color:'#eee'}}}},x:{{grid:{{display:false}},ticks:{{maxRotation:60,minRotation:45,font:{{size:10}}}}}}}},
   plugins:{{legend:{{labels:{{boxWidth:8,boxHeight:8}}}}}}}}}});
}})();

// 6. stack vs established baselines (coverage F2 vs type micro-F1) — EN + EN-real
(function(){{
 function draw(id, d){{
   const el=document.getElementById(id);
   if(!el||!d||!d.combos||!d.combos.length) return;
   new Chart(el,{{type:'bar',data:{{labels:d.combos,datasets:[
     {{label:'{t("coverage F2 (headline)")}',data:d.covf2,backgroundColor:C1}},
     {{label:'{t("type micro-F1")}',data:d.microf1,backgroundColor:C2}}]}},
    options:{{responsive:true,maintainAspectRatio:false,
     scales:{{y:{{beginAtZero:true,max:1,title:{{display:true,text:'{t("score")}'}},grid:{{color:'#eee'}}}},x:{{grid:{{display:false}},ticks:{{maxRotation:30,minRotation:0,font:{{size:10}}}}}}}},
     plugins:{{legend:{{labels:{{boxWidth:8,boxHeight:8}}}}}}}}}});
 }}
 draw('baseEN', DATA.en_baselines);
 draw('baseENR', DATA.enr_baselines);
}})();
</script>
</body></html>
"""


def main():
    for lang in languages():
        html = build_html(lang)
        suffix = "" if lang == "en" else f".{lang}"
        out = os.path.join(HERE, f"benchmark-report{suffix}.html")
        open(out, "w", encoding="utf-8").write(html)
        print(f"[tufte] wrote {os.path.relpath(out)} ({len(html)} bytes, lang={lang})")
    miss = missing()
    if miss:
        print(f"[tufte] WARNING: {len(miss)} untranslated string(s) fell back to English:")
        for m in miss[:60]:
            print(f"    · {m[:90]}")


if __name__ == "__main__":
    main()
