#!/usr/bin/env python3
"""Generate a standalone Tufte-style HTML report from the benchmark JSONs.

Reads ru/en/en-real-bench-results.json + reconstruction-results.json and emits
results/benchmark-report.html — one file, no build step, Chart.js via CDN.
Re-run after re-scoring (e.g. once OPF-RU lands) to refresh.

Design follows the tufte-report skill design tokens (EB Garamond + Monaspace
Argon, warm-white bg, 3-color semantic palette, state-lines, asides).
"""
import json
import os

from confide_eval import paths

HERE = os.fspath(paths.RESULTS)


def load(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


RU = load("ru-bench-results.json")
EN = load("en-bench-results.json")
ENR = load("en-real-bench-results.json")
RUADV = load("ru-adv-bench-results.json")
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
    types = sorted({t for t in (ca | cb) if (ca.get(t, {}).get("support") or cb.get(t, {}).get("support"))})
    return {"types": types,
            "a": [round(ca.get(t, {}).get("r", 0.0), 3) for t in types],
            "b": [round(cb.get(t, {}).get("r", 0.0), 3) for t in types],
            "a_name": combo_a, "b_name": combo_b}


def baselines_data(res):
    """Coverage-F2 (headline) + type-aware micro-F1 for the 4 EN comparison combos:
    the CONFIDE ★ stack vs the established off-the-shelf baselines (Presidio, Philter)
    and the Presidio-in-the-stack ensemble. Drives the 'stack vs baselines' chart
    (BENCHMARK.md GRAPHICS-TODO). Missing combos are skipped."""
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
    for t in ("AGE", "MEDICATION", "PROFESSION"):
        if t in nr:
            bits.append(f"{t.lower()} {nr[t]['r']:.0%}")
    return ", ".join(bits)


def leaderboard_table(res, title):
    rows = combos_clean(res)
    has_ent = any("entity_level" in e for _, e in rows)
    head = "<tr><th style='text-align:left'>combo</th><th>cov&nbsp;R</th><th>cov&nbsp;F2</th>"
    if has_ent:
        head += "<th>ent&nbsp;R</th><th>direct</th><th>quasi</th>"
    head += "<th>preds</th></tr>"
    body = []
    for n, e in rows:
        cls = " class='highlight-row'" if "★" in n else ""
        cr = e["coverage_relaxed"]
        cells = [f"<td style='text-align:left'>{n}</td>",
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
            f"<tbody>{''.join(body)}</tbody></table></div>")


HTML = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CONFIDE-Bench — De-identification Layer Benchmark</title>
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
.flyout {{ background:var(--bg-aside); border:1px solid var(--rule); border-left:3px solid var(--accent); padding:1rem 1.2rem; margin:1.4rem 0; }}
.flyout .t {{ font-variant:small-caps; letter-spacing:.06em; color:var(--accent); font-size:.85rem; margin-bottom:.3rem; }}
.ornament {{ text-align:center; color:var(--rule); font-family:'Monaspace Argon',monospace; margin:2rem 0; letter-spacing:.3em; }}
code {{ font-family:'Monaspace Argon',monospace; font-size:.82em; background:#f0ece0; padding:.05em .3em; }}
.lede::first-letter {{ font-size:3.2rem; float:left; line-height:.8; padding:.05em .12em 0 0; }}
.credit {{ font-size:.9rem; color:var(--ink-light); margin:.1rem 0 1.2rem; }}
.credit a {{ color:var(--accent); text-decoration:none; border-bottom:1px solid #e5cccc; }}
.credit a:hover {{ border-bottom-color:var(--accent); }}
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

<h1>CONFIDE-Bench — Which Layer Earns Its Compute?</h1>
<p class="sub">A bilingual de-identification benchmark for psychotherapy transcripts.</p>
<p class="credit"><strong>CONFIDE</strong> · <a href="https://github.com/glebis/confide">github.com/glebis/confide</a> · by <a href="https://github.com/glebis">Gleb Kalinin</a> &amp; CONFIDE contributors · released for research &amp; teaching under the repository license. All transcripts are synthetic/fictional — no real patient data.</p>
<p class="tags">sources: ru/ru-adv/en/en-real-bench-results.json · reconstruction-results.json &nbsp;|&nbsp; metrics: TAB · i2b2 · Presidio-F2 · datasheets-for-datasets</p>

<div class="status-strip">
  <div class="status-cell b"><div class="status-label">datasets</div><div class="status-value">4</div><div class="status-note">RU · RU-adv · EN · EN-real</div></div>
  <div class="status-cell b"><div class="status-label">combos × dataset</div><div class="status-value">{n_combos}</div><div class="status-note">union-composed ablation</div></div>
  <div class="status-cell g"><div class="status-label">RU default recall</div><div class="status-value">{ru_default_r:.0%}</div><div class="status-note">{RU_STAR}</div></div>
  <div class="status-cell r"><div class="status-label">quasi-ID survival</div><div class="status-value">{surv_comb:.0%}</div><div class="status-note">both clients · re-id surface</div></div>
</div>

<p class="lede">De-identification is not one tool but a stack of detectors, and the honest question is which layer pays for the CPU it burns. This benchmark composes detector layers by span-union over psychotherapy transcripts in Russian and English, scores each combination the way published de-id work does — recall-first, entity-level, direct vs quasi — and asks a sharper question than &ldquo;how good is the tool&rdquo;: <em>what can only an LLM catch, and what still leaks after we redact?</em></p>

<div class="flyout"><div class="t">headline</div>
<p>Three PII types — <strong>{llm_required_line()}</strong> — are near-zero under the deterministic layers (Natasha&nbsp;NER + regex). Adding the local qwen layer raises their mention-recall, but medication and profession still have very low <em>entity</em>-recall because every mention must be masked. Meanwhile <strong>{surv_comb:.0%}</strong> of quasi-identifiers still survive the default stack. Redaction of direct identifiers is necessary but not sufficient.</p></div>

<h2>1. Which layer catches what</h2>
<p class="state-line">The LLM layer is what moves <strong>age</strong>, <strong>medication</strong>, and <strong>profession</strong> above the deterministic baseline.</p>
<div class="aside-container">
  <div><div class="chart-box"><canvas id="whoCatches"></canvas></div>
  <p class="caption">RU per-category <em>mention</em> recall (relaxed overlap), {n_gold} gold mentions: deterministic (Natasha+regex) vs. +qwen.</p></div>
  <div class="aside"><div class="t">reading it</div>
  <p><strong>Structured direct IDs</strong> (email, phone, policy ID) and <strong>names/orgs/locations</strong> reach 0.9–1.0 from regex + Natasha. <strong>Dates</strong> are now caught too — a numeric-date regex rule was added after the benchmark exposed the gap.</p>
  <p><strong>Quasi-identifiers needing world-knowledge</strong> — a drug name, an occupation, a spelled-out age — are invisible to pattern and NER layers; the LLM is the only layer that lifts their mention-recall.</p>
  <p><strong>Caveat:</strong> this is <em>mention</em> recall. At <em>entity</em> level (all mentions masked), medication and profession stay at 0 even with qwen — a higher bar.</p></div>
</div>

<div class="ornament">:::</div>

<h2>2. Best sequence per language</h2>
<p class="state-line">Bars show <strong>coverage recall</strong>; ★ is the <em>proposed default</em>, which trades a little recall for large speed/precision gains — not always the single highest bar.</p>
<div class="aside-container">
  <div><div class="chart-box"><canvas id="boards"></canvas></div>
  <p class="caption">Coverage recall by combination across the plotted datasets (blank = combo not run for that dataset). ★ = proposed default; see table for F2/precision.</p></div>
  <div class="aside"><div class="t">why they differ</div>
  <p><strong>RU:</strong> the proposed default <code>{RU_STAR}</code> reaches {ru_default_r:.0%} coverage recall. {'Adding OPF reaches ' + format(ru_opf_r, '.0%') + ', but OPF is an optional comparison layer rather than the local-first default.' if ru_opf_valid else 'The OPF-on-RU row is omitted until its detector cache is regenerated for the current 30-document corpus.'}</p>
  <p><strong>EN-synth:</strong> OPF is the name/address backbone (English&rsquo;s Natasha). Default <code>{EN_STAR}</code>; <code>opf+regex</code> edges it on F2.</p>
  <p><strong>EN-real:</strong> on generic ai4privacy text the LLM is strongest; <code>opf+ollama</code> and the default <em>tie</em> on recall.</p></div>
</div>
{leaderboard_table(RU, "RU") if RU else ""}

<div class="ornament">:::</div>

<h2>3. Direct vs quasi-identifiers (TAB)</h2>
<p class="state-line">Direct identifiers reach <strong>{ru_direct:.2f}</strong> entity recall; quasi-identifiers remain lower at <strong>{ru_quasi:.2f}</strong>.</p>
<div class="aside-container">
  <div><div class="chart-box"><canvas id="directQuasi"></canvas></div>
  <p class="caption">RU entity-level recall (an entity is protected only if all mentions are masked) by identifier class.</p></div>
  <div class="aside"><div class="t">the asymmetry</div>
  <p><strong>Direct</strong> (name, phone, email, policy): masked at {ru_direct:.2f} entity recall in the default stack.</p>
  <p><strong>Quasi</strong> (age, profession, city, employer, medication, date): the LLM helps but the ceiling stays low — these are the attributes that, combined, re-identify a person.</p></div>
</div>

<div class="ornament">:::</div>

<h2>4. What survives — reconstruction &amp; re-identification</h2>
<p class="state-line"><strong>{surv_comb:.0%}</strong> of quasi-identifiers survive the default stack (both clients); over-redaction costs <strong>{overred:.0%}</strong> of redactions.</p>
<div class="status-strip">
  <div class="status-cell r"><div class="status-label">quasi survival (A)</div><div class="status-value">{(REC['A_quasi_survival']['a']['survival_rate'] if REC else 0):.0%}</div><div class="status-note">client A · re-id surface</div></div>
  <div class="status-cell r"><div class="status-label">quasi survival (B)</div><div class="status-value">{(REC['A_quasi_survival']['b']['survival_rate'] if REC else 0):.0%}</div><div class="status-note">client B</div></div>
  <div class="status-cell a"><div class="status-label">over-redaction (C)</div><div class="status-value">{overred:.0%}</div><div class="status-note">readability cost</div></div>
  <div class="status-cell b"><div class="status-label">attacker</div><div class="status-value">qwen-3B</div><div class="status-note">recovers attrs from redacted text</div></div>
</div>
<div class="aside-container">
  <div class="aside" style="border:none">
  <p style="font-size:.95rem"><strong>Method</strong> — following the re-identification / inference-attack literature (Staab et al.; RAT-Bench; Tau-Eval). An entity <em>survives</em> if any one of its mentions is left unmasked.</p></div>
  <div class="aside"><div class="t">interpretation</div>
  <p>A local 3B qwen attacker recovered <strong>{atk_rec} of {atk_tot}</strong> tested attributes from the <em>redacted</em> text (e.g. the medication, because its entity-recall is 0). A weak attacker is a lower bound — the inference-attack literature (Staab et al.) reports much higher re-identification rates for frontier models.</p>
  <p><strong>Implication:</strong> redacting direct identifiers is table stakes; quasi-identifier survival is a useful gate to check before sending a session to cloud analysis.</p></div>
</div>

<div class="ornament">:::</div>

<h2>5. Privacy vs utility — can you de-identify and still analyze?</h2>
<p class="state-line">A weak local attacker recovers <strong>{pu_top3}/{pu_n}</strong> attributes (top-3); yet <strong>{pu_util:.0%}</strong> of the clinical signal survives redaction.</p>
<div class="status-strip">
  <div class="status-cell g"><div class="status-label">CBT-signal preserved</div><div class="status-value">{pu_util:.0%}</div><div class="status-note">distortion types, redacted vs orig</div></div>
  <div class="status-cell g"><div class="status-label">non-PII text kept</div><div class="status-value">{pu_cnp:.1%}</div><div class="status-note">char-level utility floor</div></div>
  <div class="status-cell b"><div class="status-label">attack top-3</div><div class="status-value">{pu_top3}/{pu_n}</div><div class="status-note">qwen-3B, lower bound</div></div>
  <div class="status-cell a"><div class="status-label">residual risk</div><div class="status-value" style="font-size:1.1rem">{pu_risk}</div><div class="status-note">client A / B</div></div>
</div>
<div class="aside-container">
  <div class="aside" style="border:none">
  <p style="font-size:.95rem"><strong>Method</strong> — top-k inference attack with a fixed, declared budget (qwen-3B, temp 0.4, top-3 guesses/attribute, redacted text only) + downstream task preservation (re-run cognitive-distortion extraction on redacted vs. original). Aligned with Staab et al. / RAT-Bench (privacy) and Tau-Eval (task-sensitive utility).</p></div>
  <div class="aside"><div class="t">the tension, resolved</div>
  <p>The same masking that lowers attacker success can erase clinical content. Here it does <em>not</em>: the default stack keeps ~{pu_util:.0%} of distortion signal and {pu_cnp:.1%} of non-PII text while a weak attacker recovers nothing top-3.</p>
  <p><strong>Caveat:</strong> this attacker is a lower bound — quasi-identifiers still survive in text (medication entity-recall is 0), so a frontier attacker would score higher. Residual risk stays MEDIUM for client B.</p></div>
</div>

<div class="ornament">:::</div>

<h2>6. CONFIDE stack vs established baselines (Presidio, Philter)</h2>
<p class="state-line">Off-the-shelf de-identifiers can match the stack on <strong>coverage</strong> but fall far behind on <strong>type-aware micro-F1</strong> — and Presidio <em>collapses</em> on the real ai4privacy slice.</p>
<div class="aside-container">
  <div><div class="chart-box"><canvas id="baseEN"></canvas></div>
  <p class="caption">EN-synth: coverage F2 (recall-weighted, headline) vs type-aware micro-F1 for the CONFIDE ★ stack and the established baselines.</p>
  <div class="chart-box" style="margin-top:1.2rem"><canvas id="baseENR"></canvas></div>
  <p class="caption">EN-real (ai4privacy): same two metrics. Presidio's coverage drops sharply on real-world markup/ID formats.</p></div>
  <div class="aside"><div class="t">reading it</div>
  <p><strong>Coverage F2</strong> (orange) asks only &ldquo;did we mask the span at all&rdquo;. <strong>Type micro-F1</strong> (green) demands the right label too — what a redaction policy actually needs.</p>
  <p>On <strong>EN-synth</strong>, Presidio edges the stack on coverage F2 (a broad <code>DATE_TIME</code> recognizer) but its type-F1 is far lower; <strong>Philter</strong> is high-coverage yet emits almost everything as untyped <code>OTHER</code>, so its type-F1 is unusable.</p>
  <p>On <strong>EN-real</strong>, Presidio <em>collapses</em> on coverage — generic NER + structured recognizers miss the bespoke ID/markup formats the stack catches.</p>
  <p><strong>Takeaway:</strong> a generic system is not a therapy-tuned one; the only coverage a baseline adds is relative/colloquial dates.</p></div>
</div>

<div class="ornament">:::</div>

<h2 id="regulatory">7. Regulatory residual-risk (RU)</h2>
<p class="state-line">Detection metrics measure what we catch; regulators care what <em>survives</em>. Mapped onto named risks, the RU default stack lands at <strong>{reg_tier}</strong> — driven by {reg_direct} in-scope residual direct-identifier {"entity" if reg_direct == 1 else "entities"} (a re-identification key left in the text). A further {reg_oos} are spelled-out digit IDs, out of scope for the regex layer by design and reported separately.</p>
<div class="status-strip">
  <div class="status-cell {reg_tier_class}"><div class="status-label">residual-risk tier</div><div class="status-value">{reg_tier}</div><div class="status-note">ordinal R/A/G · RU ★ stack</div></div>
  <div class="status-cell b"><div class="status-label">HIPAA-inspired coverage</div><div class="status-value">{reg_hip_pass}/{reg_hip_app}</div><div class="status-note">categories fully removed</div></div>
  <div class="status-cell r"><div class="status-label">worst-doc recall</div><div class="status-value">{reg_wc_min:.0%}</div><div class="status-note">containment · {reg_wc_rate} leaks / 10k chars</div></div>
  <div class="status-cell a"><div class="status-label">singled out</div><div class="status-value">{reg_singles}/{reg_nsingle}</div><div class="status-note">clients · residual quasi surface</div></div>
</div>
<div class="aside-container">
  <div class="aside" style="border:none">
  <p style="font-size:.95rem"><strong>WP29 (Art-29 WP 05/2014) re-identification triad</strong> — identifiability decomposes into <em>singling out</em> (residual quasi surface via a caveated population-fraction estimator — NOT corpus k-anonymity, N is tiny), <em>linkability</em> (pairwise session-linking ROC&nbsp;AUC {reg_link_roc:.2f}; at or below 0.50 = chance, which is the safe direction), and <em>inference</em> (attribute-recovery attack recovers {reg_inf:.0%}). HIPAA coverage is a Safe-Harbor-<em>inspired</em> checklist, not a legal determination (AGE is N/A; structured IDs collapsed).</p></div>
  <div class="aside"><div class="t">reading the tier</div>
  <p><strong>RED</strong> = any in-scope direct identifier leaks at entity level (one unmasked mention is a key). <strong>AMBER</strong> = special-category residual, nonzero inference, or linkability above chance. <strong>GREEN</strong> = all clear.</p>
  <p><strong>What leaks:</strong> not whole names but specific <em>variants</em> — inflected/possessive/patronymic forms (Артёмом, Натальин, Денису), lowercase surnames, vocatives, Latin transliteration (Timur), and name/common-word collisions (Вера, Роман). Mention-level recall hides this; the strict TAB entity bar (one miss ⇒ unprotected) surfaces it.</p>
  <p>Source: <code>results/regulatory-results.json</code> (<code>confide_eval.scoring.regulatory</code>, unit-tested). Singling-out is illustrative — see its independence caveat in the JSON.</p></div>
</div>

<div class="flyout"><div class="t">methodology</div>
<p>Each detector runs once per dataset; combinations are span-unions of cached spans, interval-merged to the deployed redaction mask before scoring. This report headlines <strong>coverage recall</strong> (relaxed overlap) — the privacy-critical number — and recall-weighted <strong>F2</strong> + precision sit in the leaderboard table. Type-aware micro/macro-F1 (i2b2) and entity-level recall (TAB; all mentions masked) are also reported. Numbers are mention-level unless marked entity-level. Gold for RU is located from the two answer-key PII inventories and hand-verified (a planted-signal recovery eval, not independently annotated gold); English reuses curated + real ai4privacy slices. Synthetic data — no real patients. Small N: treat per-type numbers as directional.</p></div>

<h2 id="references">References &amp; credits</h2>
<div class="refs prose">
<p>CONFIDE-Bench builds on the de-identification, re-identification, and documentation literature listed below. Every work named or relied on in this report is credited here with a link to its canonical page (DOI / arXiv / HuggingFace / GitHub). We credit only what the report actually uses; inclusion does not imply endorsement by those authors. URLs verified against <code>docs/CITATION-AUDIT.md</code>.</p>

<h3>Benchmarks &amp; metrics</h3>
<ul>
  <li><strong>TAB — Text Anonymization Benchmark.</strong> Pilán, Lison, Øvrelid, Papadopoulou, Sánchez &amp; Batet (2022), <em>Computational Linguistics</em> 48(4):1053–1101. <span class="meta">Source of the direct vs. quasi-identifier distinction and entity-level (all-mentions-masked) recall.</span> <a href="https://doi.org/10.1162/coli_a_00458">doi:10.1162/coli_a_00458</a> · <a href="https://aclanthology.org/2022.cl-4.19/">ACL Anthology</a></li>
  <li><strong>2014 i2b2/UTHealth de-identification (Track&nbsp;1).</strong> Stubbs, Kotfila &amp; Uzuner (2015), <em>J. Biomedical Informatics</em>. <span class="meta">Strict entity-based de-id evaluation; comparison point for clinical-note de-id.</span> <a href="https://pubmed.ncbi.nlm.nih.gov/26225918/">PubMed 26225918</a></li>
  <li><strong>2016 CEGS N-GRID / n2c2 psychiatric-intake de-identification.</strong> Stubbs, Filannino &amp; Uzuner (2017), <em>J. Biomedical Informatics</em>. <span class="meta">Psychiatric-intake-note de-id comparison point.</span> <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC5705537/">PMC5705537</a></li>
  <li><strong>MEDDOCAN.</strong> Spanish synthetic clinical-case de-identification shared task (IberLEF 2019), ~22 PHI types. <span class="meta">Related clinical de-id benchmark.</span> <a href="https://github.com/PlanTL-GOB-ES/SPACCC_MEDDOCAN">PlanTL SPACCC_MEDDOCAN</a></li>
  <li><strong>Presidio-research (F2 evaluation).</strong> Microsoft, MIT-licensed. <span class="meta">Basis for the recall-weighted F<sub>2</sub> (β=2) de-id scoring framing.</span> <a href="https://github.com/microsoft/presidio-research">github.com/microsoft/presidio-research</a></li>
  <li><strong>Tau-Eval.</strong> Loiseau et al. (2025), EMNLP System Demonstrations. <span class="meta">Task-sensitive privacy-and-utility evaluation framing.</span> <a href="https://arxiv.org/abs/2506.05979">arXiv:2506.05979</a></li>
</ul>

<h3>Re-identification &amp; privacy attacks</h3>
<ul>
  <li><strong>Staab et al. — Beyond Memorization: Violating Privacy via Inference with LLMs.</strong> ICLR 2024. <span class="meta">LLM inference-attack framing; frontier attackers infer far more than the local lower-bound attacker used here.</span> <a href="https://arxiv.org/abs/2310.07298">arXiv:2310.07298</a></li>
  <li><strong>Anonymeter.</strong> Giomi, Boenisch, Wehmeyer &amp; Tasnádi (2022/PETS 2023), Statice. <span class="meta">Attack-based singling-out / linkability / inference framing (the three GDPR risks).</span> <a href="https://arxiv.org/abs/2211.10459">arXiv:2211.10459</a> · <a href="https://github.com/statice/anonymeter">GitHub</a></li>
  <li><strong>RAT-Bench.</strong> Imperial College (2026 preprint). <span class="meta">Attacker-based residual re-identification benchmark framing (cited as preprint evidence).</span> <a href="https://openreview.net/forum?id=FjbU4kLriN">OpenReview FjbU4kLriN</a></li>
</ul>

<h3>Detectors &amp; tools</h3>
<ul>
  <li><strong>Microsoft Presidio.</strong> MIT license; spaCy-backed PII detection (EN-first baseline). <a href="https://github.com/microsoft/presidio">github.com/microsoft/presidio</a></li>
  <li><strong>Philter / philter-lite.</strong> UCSF clinical de-identification rule set; <code>philter-lite</code> is the Sirona Medical fork. <a href="https://github.com/SironaMedical/philter-lite">github.com/SironaMedical/philter-lite</a> · <a href="https://pypi.org/project/philter-lite/">PyPI</a></li>
  <li><strong>Natasha.</strong> Russian NLP/NER toolkit (Cyrillic-only — the basis for the documented transliteration leak). <a href="https://github.com/natasha/natasha">github.com/natasha/natasha</a></li>
  <li><strong>OpenAI Privacy Filter (OPF), <code>openai/privacy-filter</code>.</strong> Apache-2.0 token-classification PII model (used as the EN name/address backbone). The model card states it is a redaction / data-minimization aid, <em>not</em> an anonymization or compliance guarantee. <a href="https://huggingface.co/openai/privacy-filter">huggingface.co/openai/privacy-filter</a></li>
  <li><strong>Ollama + Qwen.</strong> Local LLM runner and the Qwen model family used for the local-LLM detector layer and the local 3B re-identification attacker. <a href="https://ollama.com/">ollama.com</a> · <a href="https://github.com/QwenLM/Qwen2.5">QwenLM/Qwen2.5</a></li>
</ul>

<h3>Datasets</h3>
<ul>
  <li><strong>ai4privacy / pii-masking-300k.</strong> Multilingual synthetic PII dataset; the EN-real validation slice is drawn from it. <span class="meta">License is custom/<code>other</code> (see the dataset's <code>license.md</code>) — verify before redistributing.</span> <a href="https://huggingface.co/datasets/ai4privacy/pii-masking-300k">huggingface.co/datasets/ai4privacy/pii-masking-300k</a></li>
</ul>

<h3>Documentation &amp; regulatory framing</h3>
<ul>
  <li><strong>Datasheets for Datasets.</strong> Gebru et al. (2021), <em>CACM</em>. <a href="https://www.microsoft.com/en-us/research/publication/datasheets-for-datasets/">Microsoft Research</a></li>
  <li><strong>Data Statements for NLP.</strong> Bender &amp; Friedman (2018), <em>TACL</em>. <a href="https://aclanthology.org/Q18-1041/">ACL Anthology Q18-1041</a></li>
  <li><strong>GDPR Recital 26 &amp; WP29/EDPB anonymisation framework.</strong> &ldquo;Reasonably likely means&rdquo; and the singling-out / linkability / inference triad. <a href="https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng">GDPR (EUR-Lex)</a> · <a href="https://www.edpb.europa.eu/sme-data-protection-guide/secure-personal-data_en">EDPB SME guide</a></li>
  <li><strong>HIPAA de-identification (Safe Harbor &amp; Expert Determination).</strong> Mapping is illustrative only — benchmark success is <em>not</em> a compliance certification. <a href="https://www.hhs.gov/hipaa/for-professionals/privacy/special-topics/de-identification/index.html">HHS HIPAA de-id guidance</a></li>
</ul>
</div>

<footer>Generated by <code>make_tufte_report.py</code> from <code>results/*-bench-results.json</code>. <strong>CONFIDE-Bench</strong>, part of <a href="https://github.com/glebis/confide">CONFIDE</a> — by Gleb Kalinin &amp; CONFIDE contributors, Psychodemia 2026. Metrics &amp; methods credit: TAB (Pilán et al. 2022), i2b2/n2c2 2014/2016, Microsoft Presidio-research, Datasheets for Datasets — see References above for full links. All data is synthetic/fictional — not real patient data.</footer>

<script>
const DATA = {json.dumps(DATA, ensure_ascii=False)};
const C1='#c45a28', C2='#2a7a5a', C3='#5a5aaa', INK='#1a1a1a', MUTE='#888';
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
   scales:{{y:{{beginAtZero:true,max:1,title:{{display:true,text:'recall'}},grid:{{color:'#eee'}}}},x:{{grid:{{display:false}},ticks:{{maxRotation:60,minRotation:45}}}}}},
   plugins:{{legend:{{labels:{{boxWidth:8,boxHeight:8}}}}}}}}}});
}})();

// 2. leaderboards (horizontal bars, plotted datasets overlaid by combo recall) -> small multiples as one grouped chart
(function(){{
 const sets=[['RU',DATA.ru_leaderboard,C2],['EN',DATA.en_leaderboard,C1],['EN-real',DATA.enr_leaderboard,C3]];
 // union of combo names preserving RU order then extras
 const labels=[]; sets.forEach(([_,rows])=>rows.forEach(r=>{{if(!labels.includes(r.combo))labels.push(r.combo);}}));
 const datasets=sets.map(([name,rows,col])=>({{label:name,
   data:labels.map(l=>{{const r=rows.find(x=>x.combo===l);return r?+r.recall.toFixed(3):null}}),
   backgroundColor:col}}));
 new Chart(document.getElementById('boards'),{{type:'bar',data:{{labels,datasets}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
   scales:{{x:{{beginAtZero:true,max:1,title:{{display:true,text:'coverage recall'}},grid:{{color:'#eee'}}}},y:{{grid:{{display:false}}}}}},
   plugins:{{legend:{{labels:{{boxWidth:8,boxHeight:8}}}}}}}}}});
}})();

// 3. direct vs quasi (RU combos)
(function(){{
 const rows=DATA.ru_leaderboard.filter(r=>r.direct!==undefined);
 new Chart(document.getElementById('directQuasi'),{{type:'bar',data:{{labels:rows.map(r=>r.combo),datasets:[
   {{label:'direct',data:rows.map(r=>r.direct),backgroundColor:C2}},
   {{label:'quasi',data:rows.map(r=>r.quasi),backgroundColor:C1}}]}},
  options:{{responsive:true,maintainAspectRatio:false,
   scales:{{y:{{beginAtZero:true,max:1,title:{{display:true,text:'entity recall'}},grid:{{color:'#eee'}}}},x:{{grid:{{display:false}},ticks:{{maxRotation:60,minRotation:45,font:{{size:10}}}}}}}},
   plugins:{{legend:{{labels:{{boxWidth:8,boxHeight:8}}}}}}}}}});
}})();

// 6. stack vs established baselines (coverage F2 vs type micro-F1) — EN + EN-real
(function(){{
 function draw(id, d){{
   if(!d||!d.combos||!d.combos.length) return;
   new Chart(document.getElementById(id),{{type:'bar',data:{{labels:d.combos,datasets:[
     {{label:'coverage F2 (headline)',data:d.covf2,backgroundColor:C1}},
     {{label:'type micro-F1',data:d.microf1,backgroundColor:C2}}]}},
    options:{{responsive:true,maintainAspectRatio:false,
     scales:{{y:{{beginAtZero:true,max:1,title:{{display:true,text:'score'}},grid:{{color:'#eee'}}}},x:{{grid:{{display:false}},ticks:{{maxRotation:30,minRotation:0,font:{{size:10}}}}}}}},
     plugins:{{legend:{{labels:{{boxWidth:8,boxHeight:8}}}}}}}}}});
 }}
 draw('baseEN', DATA.en_baselines);
 draw('baseENR', DATA.enr_baselines);
}})();
</script>
</body></html>
"""

out = os.path.join(HERE, "benchmark-report.html")
open(out, "w", encoding="utf-8").write(HTML)
print(f"[tufte] wrote {os.path.relpath(out)} ({len(HTML)} bytes)")
