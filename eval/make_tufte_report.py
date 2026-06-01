#!/usr/bin/env python3
"""Generate a standalone Tufte-style HTML report from the benchmark JSONs.

Reads ru/en/en-real-bench-results.json + reconstruction-results.json and emits
eval/benchmark-report.html — one file, no build step, Chart.js via CDN.
Re-run after re-scoring (e.g. once OPF-RU lands) to refresh.

Design follows the tufte-report skill design tokens (EB Garamond + Monaspace
Argon, warm-white bg, 3-color semantic palette, state-lines, asides).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


RU = load("ru-bench-results.json")
EN = load("en-bench-results.json")
ENR = load("en-real-bench-results.json")
RUADV = load("ru-adv-bench-results.json")
REC = load("reconstruction-results.json")
PU = load("privacy-utility-results.json")


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
footer {{ border-top:1px solid var(--rule); margin-top:3rem; padding-top:1rem; font-size:.8rem; color:var(--ink-muted); }}
@media(max-width:800px){{ .status-strip{{grid-template-columns:repeat(2,1fr)}} .aside-container{{grid-template-columns:1fr}} }}
</style></head><body>

<h1>CONFIDE-Bench — Which Layer Earns Its Compute?</h1>
<p class="sub">A bilingual de-identification benchmark for psychotherapy transcripts.</p>
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

<div class="flyout"><div class="t">methodology</div>
<p>Each detector runs once per dataset; combinations are span-unions of cached spans, interval-merged to the deployed redaction mask before scoring. This report headlines <strong>coverage recall</strong> (relaxed overlap) — the privacy-critical number — and recall-weighted <strong>F2</strong> + precision sit in the leaderboard table. Type-aware micro/macro-F1 (i2b2) and entity-level recall (TAB; all mentions masked) are also reported. Numbers are mention-level unless marked entity-level. Gold for RU is located from the two answer-key PII inventories and hand-verified (a planted-signal recovery eval, not independently annotated gold); English reuses curated + real ai4privacy slices. Synthetic data — no real patients. Small N: treat per-type numbers as directional.</p></div>

<footer>Generated from eval/*-bench-results.json. CONFIDE-Bench benchmark, Psychodemia 2026. Metrics: TAB (Pilán 2022), i2b2/n2c2 2014, Presidio-research, Datasheets for Datasets. Synthetic/fictional data.</footer>

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
