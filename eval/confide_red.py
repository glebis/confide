#!/usr/bin/env python3
"""CONFIDE-Red — adversarial re-identification of CONFIDE-anonymized transcripts.

Grades the anonymized (GREEN) output against the three GDPR Art-29 / Anonymeter
attack families, run by an LLM attacker with *varied prompts and goals*:

  1. INFERENCE     — infer a hidden attribute (profession/city/age/employer/medication)
                     from the redacted text. Run with 3 prompt strategies (direct /
                     reason-step-by-step / investigator role-play) to see which the
                     anonymizer is least robust to. Score top-3 vs known truth.
  2. SINGLING-OUT  — do the surviving quasi-identifiers, combined, narrow to one person?
                     Deterministic k-anonymity estimate over declared population priors
                     (no LLM): expected matches < 1 ⇒ singled out.
  3. LINKABILITY   — given two redacted sessions, can the attacker tell whether they are
                     the SAME person? Ask on a same-client pair vs a different-client
                     pair; correct on both ⇒ linkable.

Synthetic data only — every attribute is fabricated. Engine-agnostic LLM
(LLM_API=openai + LLM_BASE_URL → llama.cpp, else Ollama). Outputs CONFIDE-RED-RESULTS.md.
"""
import json
import os
import re
import sys
import urllib.request

import kanon  # shared singling-out estimator (one prior table, one survivor method)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "session-anonymizer", "scripts"))
RU = os.path.join(HERE, "..", "sessions-ru")
MODEL = os.environ.get("LLM_MODEL", "qwen2.5:3b")

# Ground truth for scoring (fabricated personas).
TRUTH = {
    "a": {"profession": ["маркетолог"], "employer": ["яндекс"], "city": ["калуга"], "age": ["34", "тридцать четыре"], "medication": ["сертралин"]},
    "b": {"profession": ["программист"], "employer": ["контур"], "city": ["кострома"], "age": ["41", "сорок один"], "medication": ["флуоксетин"]},
    "c": {"profession": ["дизайнер"], "employer": ["авито"], "city": ["петербург"], "age": ["29", "двадцать девять"], "medication": ["эсциталопрам"]},
    "d": {"profession": ["предприниматель"], "employer": ["сибтранс"], "city": ["новосибирск"], "age": ["45", "сорок пять"], "medication": ["бупропион"]},
    "e": {"profession": ["учитель"], "employer": ["гимназ"], "city": ["екатеринбург"], "age": ["37", "тридцать семь"], "medication": ["миртазапин"]},
    "f": {"profession": ["программист", "студент"], "employer": ["кфу"], "city": ["казан"], "age": ["23", "двадцать три"], "medication": ["атомоксетин"]},
}
# Singling-out priors + estimator now live in the shared `kanon` module so this
# script and privacy_utility_eval.py compute the IDENTICAL expected-match count
# per client (audit bug B1: 104.3 vs 3504). The numbers are ILLUSTRATIVE — a
# methodological demonstration, not a re-identification probability (see kanon).

PROMPTS = {
    "direct": "Из оставшегося контекста назови наиболее вероятные атрибуты клиента.",
    "reason": "Рассуждай шаг за шагом по уликам в тексте, затем выведи атрибуты клиента.",
    "investigator": "Ты частный детектив. По косвенным деталям реконструируй личность клиента.",
}


def llm_json(prompt, temperature=0.3):
    api = os.environ.get("LLM_API", "ollama").lower()
    base = os.environ.get("LLM_BASE_URL", os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
    msgs = [{"role": "user", "content": prompt}]
    headers = {"Content-Type": "application/json"}
    if api == "openai":
        # Reasoning models (gpt-5 / o1 / o3) reject `temperature` and use `max_completion_tokens`.
        reasoning = re.match(r"^(gpt-5|o1|o3)", MODEL or "")
        body = {"model": MODEL, "messages": msgs, "stream": False}
        if reasoning:
            body["max_completion_tokens"] = 4000
        else:
            body["temperature"] = float(os.environ.get("LLM_TEMPERATURE", temperature))
            # Qwen3 spends output budget on a <think> block before the JSON; let a
            # cloud run raise the cap (LLM_MAX_TOKENS) so verdicts don't truncate.
            body["max_tokens"] = int(os.environ.get("LLM_MAX_TOKENS", "400"))
        url = base + "/v1/chat/completions"
        key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
        if key:
            headers["Authorization"] = "Bearer " + key
        # Some providers front their API with Cloudflare, which 403s (error 1010)
        # requests with a default urllib User-Agent. A browser UA passes (matches
        # anonymize.run_ollama's cloud transport per CLOUD-MODEL-RESULTS.md).
        headers["User-Agent"] = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                                 "Chrome/124.0 Safari/537.36")
    else:
        url, body = base + "/api/chat", {"model": MODEL, "messages": msgs, "stream": False, "options": {"temperature": temperature, "num_predict": 400}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    out = d["choices"][0]["message"]["content"] if api == "openai" else d["message"]["content"]
    out = re.sub(r"<think>.*?</think>", "", out, flags=re.DOTALL)
    m = re.search(r"\{.*\}", out, re.DOTALL)
    try:
        return json.loads(m.group()) if m else {}
    except json.JSONDecodeError:
        return {}


def merge(spans):
    ss = sorted(spans, key=lambda s: (s.start, -(s.end - s.start)))
    out = []
    for s in ss:
        if out and s.start < out[-1][1]:
            out[-1][1] = max(out[-1][1], s.end)
        else:
            out.append([s.start, s.end])
    return out


# The redactor (defense) is held FIXED across attacker runs so floor-vs-ceiling
# compares only the attacker. run_ollama() reads LLM_API/LLM_BASE_URL from env,
# so when the ATTACKER uses a cloud model we must pin the redactor back to the
# local Ollama qwen2.5:3b for the duration of the redaction call.
REDACTOR_MODEL = os.environ.get("REDACTOR_MODEL", "qwen2.5:3b")
REDACTOR_API = os.environ.get("REDACTOR_API", "ollama")
REDACTOR_BASE = os.environ.get("REDACTOR_BASE_URL", "http://localhost:11434")


def redact(text, anonymize):
    saved = {k: os.environ.get(k) for k in ("LLM_API", "LLM_BASE_URL", "OLLAMA_HOST")}
    os.environ["LLM_API"] = REDACTOR_API
    os.environ["LLM_BASE_URL"] = REDACTOR_BASE
    os.environ.pop("OLLAMA_HOST", None)
    try:
        ollama_spans = anonymize.run_ollama(text, REDACTOR_MODEL)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    iv = merge(anonymize.run_natasha(text) + anonymize.run_regex(text) + ollama_spans)
    o, last = [], 0
    for s, e in iv:
        o.append(text[last:s]); o.append("<X>"); last = e
    o.append(text[last:])
    return "".join(o), iv


def hit(guess, truths):
    cand = guess if isinstance(guess, list) else [guess]
    return any(any(t in str(c).lower() for t in truths) for c in cand[:3])


def inference_attack(redacted, truth):
    """Run the 3 prompt strategies; return {strategy: recovered/of}."""
    res = {}
    for name, lead in PROMPTS.items():
        p = (lead + " Верни ТОЛЬКО JSON top-3 на атрибут: "
             '{"profession":["",""],"employer":["",""],"city":["",""],"age":["",""],"medication":["",""]}.'
             "\n\nТекст:\n" + redacted[:14000])
        g = llm_json(p)
        res[name] = sum(int(hit(g.get(a, []), truth[a])) for a in truth)
    return res, len(truth)


def singling_out(cl):
    """ILLUSTRATIVE k-anonymity estimate via the SHARED kanon estimator.

    Survivor detection is the deterministic, entity-aware gold+cache method (same
    source privacy_utility_eval.py uses), so both scripts return the identical
    expected-match count. Returns the canonical dict plus the sensitivity verdict.
    """
    s = kanon.singling_out(cl)              # survivors computed from gold+caches inside
    sw = kanon.sensitivity(cl)
    s["dims"] = s["dims_used"]              # back-compat field name
    s["verdict_robust"] = sw["verdict_robust"]
    return s


# ---------------------------------------------------------------------------
# LINKABILITY BENCHMARK (Anonymeter framing) — full pair matrix, not a demo.
#
# Audit bug B8: the old code tested ONE same-client pair + ONE different-client
# pair ("a demo, not a benchmark"). Here we build all unordered pairs of the 30
# redacted docs (6 clients × 5 sessions), label each SAME / DIFFERENT, and ask
# the attacker LLM "same person?" over a balanced sample, then score it as a
# binary classifier (accuracy / P-R-F1 / ROC-AUC) with bootstrap CIs.
# ---------------------------------------------------------------------------

LINK_PROMPT = (
    'Это два анонимизированных транскрипта психотерапии (имена и явные '
    'идентификаторы вырезаны как <X>). Опираясь на косвенные детали (стиль речи, '
    'темы, биографические крошки), определи: это ОДИН И ТОТ ЖЕ клиент в обоих '
    'сессиях? Верни ТОЛЬКО JSON {"same":true|false,"confidence":0..1}, где '
    'confidence — твоя уверенность, что это ОДИН человек (0=точно разные, '
    '1=точно один).\n\nA:\n__A__\n\nB:\n__B__')


def build_pairs(doc_keys, diff_stride=7, max_diff=None):
    """All SAME pairs + a deterministically strided sample of DIFFERENT pairs.

    `doc_keys` is the ordered list of (client, session_idx) keys. Returns
    (pairs, dropped) where each pair is (i, j, label) with label "same"/"diff"
    and i<j index into doc_keys. SAME = both keys share a client. We take ALL
    same-client pairs (6×C(5,2)=60) and every `diff_stride`-th DIFFERENT pair
    (deterministic — no RNG, since the task forbids Math.random-style sampling);
    `dropped` records how many DIFFERENT pairs were skipped, so sampling is
    transparent (no silent truncation)."""
    same, diff = [], []
    n = len(doc_keys)
    for i in range(n):
        for j in range(i + 1, n):
            label = "same" if doc_keys[i][0] == doc_keys[j][0] else "diff"
            (same if label == "same" else diff).append((i, j, label))
    sampled_diff = diff[::diff_stride]
    if max_diff is not None:
        sampled_diff = sampled_diff[:max_diff]
    dropped = len(diff) - len(sampled_diff)
    return same + sampled_diff, {"total_diff": len(diff), "sampled_diff": len(sampled_diff),
                                 "dropped_diff": dropped, "diff_stride": diff_stride}


def link_judge(a_text, b_text):
    """Ask the attacker LLM whether two redacted docs are the same client.
    Returns (called_same: bool, confidence: float in [0,1])."""
    p = LINK_PROMPT.replace("__A__", a_text[:7000]).replace("__B__", b_text[:7000])
    v = llm_json(p, temperature=0.0)
    same = v.get("same")
    try:
        conf = float(v.get("confidence"))
    except (TypeError, ValueError):
        conf = None
    if conf is None:
        conf = 1.0 if same is True else 0.0
    conf = max(0.0, min(1.0, conf))
    # A 'different' verdict should have LOW same-confidence; flip if the model
    # reported confidence-in-its-own-answer rather than confidence-in-same.
    if same is False and conf > 0.5:
        conf = 1.0 - conf
    return (same is True), conf


def score_linkability(verdicts):
    """verdicts: list of dicts {label, called_same, confidence}. Returns the full
    binary-classifier metrics (SAME is the positive class)."""
    tp = sum(1 for v in verdicts if v["label"] == "same" and v["called_same"])
    fn = sum(1 for v in verdicts if v["label"] == "same" and not v["called_same"])
    fp = sum(1 for v in verdicts if v["label"] == "diff" and v["called_same"])
    tn = sum(1 for v in verdicts if v["label"] == "diff" and not v["called_same"])
    n = tp + fn + fp + tn
    acc = (tp + tn) / n if n else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    auc = roc_auc([v["label"] == "same" for v in verdicts],
                  [v["confidence"] for v in verdicts])
    base_rate = (tp + fn) / n if n else 0.0  # P(SAME) — majority-class accuracy is max(base, 1-base)
    return {"n": n, "tp": tp, "fn": fn, "fp": fp, "tn": tn, "accuracy": round(acc, 4),
            "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4),
            "roc_auc": round(auc, 4), "base_rate_same": round(base_rate, 4),
            "majority_accuracy": round(max(base_rate, 1 - base_rate), 4)}


def roc_auc(labels, scores):
    """ROC-AUC via the Mann–Whitney U statistic (probability a random positive
    outscores a random negative), with 0.5 credit for ties. No numpy."""
    pos = [s for l, s in zip(labels, scores) if l]
    neg = [s for l, s in zip(labels, scores) if not l]
    if not pos or not neg:
        return 0.5
    wins = sum((p > nn) + 0.5 * (p == nn) for p in pos for nn in neg)
    return wins / (len(pos) * len(neg))


def bootstrap_link_ci(verdicts, iters=2000, seed=20260601):
    """Resample pairs with replacement; report mean + 2.5–97.5 percentile CI for
    accuracy and ROC-AUC. Matches bootstrap_ci.py's style (deterministic seed)."""
    import random
    rng = random.Random(seed)
    n = len(verdicts)
    accs, aucs = [], []
    for _ in range(iters):
        sample = [verdicts[rng.randrange(n)] for _ in range(n)]
        s = score_linkability(sample)
        accs.append(s["accuracy"])
        aucs.append(s["roc_auc"])

    def ci(xs):
        xs = sorted(xs)
        lo = xs[int(0.025 * len(xs))]
        hi = xs[int(0.975 * len(xs)) - 1]
        return {"mean": round(sum(xs) / len(xs), 4), "lo95": round(lo, 4), "hi95": round(hi, 4)}
    return {"iters": iters, "accuracy": ci(accs), "roc_auc": ci(aucs)}


def run_linkability(clients, red, cache_path):
    """Full-matrix linkability benchmark. Caches per-pair verdicts to JSON so
    re-runs / scoring don't re-call the LLM. Returns the results dict."""
    doc_keys = [(cl, s) for cl in clients for s in range(len(red.get(cl, [])))]
    docs = {(cl, s): red[cl][s] for cl, s in doc_keys}
    stride = int(os.environ.get("CONFIDE_RED_DIFF_STRIDE", "5"))
    # Bound the work: ALL same-client pairs (60 over 6×5) + a fixed-stride sample of
    # DIFFERENT pairs capped at CONFIDE_RED_MAX_DIFF (default 40) ⇒ ~100 pairs total.
    max_diff = int(os.environ.get("CONFIDE_RED_MAX_DIFF", "40"))
    pairs, samp = build_pairs(doc_keys, diff_stride=stride, max_diff=max_diff)
    n_same = sum(1 for *_ , lab in pairs if lab == "same")
    print(f"[link] doc_keys={len(doc_keys)} pairs={len(pairs)} "
          f"(same={n_same}, diff={samp['sampled_diff']} of {samp['total_diff']}, "
          f"dropped_diff={samp['dropped_diff']}, stride={samp['diff_stride']})")

    cache = {}
    if os.path.exists(cache_path):
        cache = json.load(open(cache_path, encoding="utf-8"))
    verdicts = []
    for i, j, label in pairs:
        ka, kb = doc_keys[i], doc_keys[j]
        ck = f"{ka[0]}{ka[1]}|{kb[0]}{kb[1]}"
        if ck not in cache:
            called_same, conf = link_judge(docs[ka], docs[kb])
            cache[ck] = {"label": label, "called_same": called_same, "confidence": conf}
            json.dump(cache, open(cache_path, "w"), ensure_ascii=False, indent=2)
            print(f"[link] {ck} label={label} called_same={called_same} conf={conf:.2f}")
        v = dict(cache[ck]); v["label"] = label  # label is authoritative from pairing
        verdicts.append(v)

    metrics = score_linkability(verdicts)
    ci = bootstrap_link_ci(verdicts)
    print(f"[link] acc={metrics['accuracy']} auc={metrics['roc_auc']} f1={metrics['f1']} "
          f"(majority={metrics['majority_accuracy']})")

    # Diagnostic: the default stack leaves the YAML `client_id` (a first name) in the
    # clear in most sessions. That is a per-client CONSTANT key, so a near-perfect
    # linkability score reflects a surviving DIRECT IDENTIFIER, not subtle stylometry.
    # We surface it so the AUC is read honestly (a redaction failure, not a clever attack).
    leaked = 0
    for cl in clients:
        for s in red.get(cl, []):
            if re.search(r"client_id:\s*\w", s):
                leaked += 1
    leak_note = (f"{leaked}/{len(doc_keys)} redacted sessions still expose a cleartext "
                 "YAML `client_id` (a first name) — a per-client CONSTANT key. The "
                 "near-perfect score therefore reflects a SURVIVING DIRECT IDENTIFIER the "
                 "default stack failed to mask, not stylometric inference. This is itself "
                 "the load-bearing finding: the deployed redaction does not strip "
                 "structured metadata.") if leaked else (
                 "No cleartext client_id detected in the redacted docs; the score reflects "
                 "content-based linkability.")
    print(f"[link] LEAK: {leak_note}")
    return {"model": MODEL, "engine": os.environ.get("LLM_API", "ollama"),
            "n_docs": len(doc_keys), "sampling": samp, "n_pairs": len(pairs),
            "n_same": n_same, "n_diff": samp["sampled_diff"],
            "metrics": metrics, "bootstrap_ci": ci,
            "leaked_client_id_docs": leaked, "leak_note": leak_note}


def _redact_clients(clients):
    import anonymize
    red = {}
    for cl in clients:
        red[cl] = []
        for s in range(1, 6):
            p = os.path.join(RU, f"client-{cl}", f"session-0{s}.md")
            if not os.path.exists(p):
                continue
            text = open(p, encoding="utf-8").read()
            r, _ = redact(text, anonymize)
            red[cl].append(r)
    return red


def _redact_from_cache(clients):
    """Build the SAME redactions as redact() but from the committed local-default-
    stack detector caches (natasha + regex + ollama qwen2.5:3b) instead of re-running
    the slow local LLM. The redactor (system-under-test) stays the committed default;
    we only avoid recomputing identical spans. Doc-id convention: ru-<client>-s0<n>.

    Caches index into score_bench's gold text, so we redact that exact text."""
    import score_bench as sb
    CACHE = os.path.join(HERE, "detector-cache")

    def load(det):
        path = os.path.join(CACHE, f"ru.{det}.jsonl")
        out = {}
        for line in open(path, encoding="utf-8"):
            d = json.loads(line)
            out[d["doc_id"]] = d.get("spans", [])
        return out

    nat, rgx, oll = load("natasha"), load("regex"), load("ollama")
    text_by_id = {g["doc_id"]: g["text"] for g in sb.load_gold("ru")}
    red = {}
    for cl in clients:
        red[cl] = []
        for s in range(1, 6):
            did = f"ru-{cl}-s0{s}"
            if did not in text_by_id:
                continue
            text = text_by_id[did]
            spans = nat.get(did, []) + rgx.get(did, []) + oll.get(did, [])
            ss = sorted(spans, key=lambda x: (x["start"], -(x["end"] - x["start"])))
            iv = []
            for sp in ss:
                if iv and sp["start"] < iv[-1][1]:
                    iv[-1][1] = max(iv[-1][1], sp["end"])
                else:
                    iv.append([sp["start"], sp["end"]])
            o, last = [], 0
            for st, en in iv:
                o.append(text[last:st]); o.append("<X>"); last = en
            o.append(text[last:])
            red[cl].append("".join(o))
    return red


def main():
    # Full benchmark linkability needs ≥2 clients with multiple sessions each;
    # default to all 6 so the pair matrix is meaningful (B8: not a single-pair demo).
    link_only = "--linkability-only" in sys.argv
    default_clients = "a,b,c,d,e,f" if link_only else "a,b,c"
    clients = (os.environ.get("CONFIDE_RED_CLIENTS") or default_clients).split(",")
    # --from-cache: build redactions from the committed local-default-stack detector
    # caches (natasha+regex+ollama 3b) — same system-under-test, no slow live LLM.
    if "--from-cache" in sys.argv:
        red = _redact_from_cache(clients)
        print(f"[link] redactions from detector cache (local default stack) for {clients}")
    else:
        red = _redact_clients(clients)

    link_cache = os.path.join(HERE, "linkability-cache.json")
    link = run_linkability(clients, red, link_cache)
    json.dump(link, open(os.path.join(HERE, "linkability-results.json"), "w"),
              ensure_ascii=False, indent=2)
    print("[link] wrote linkability-results.json")

    # Log to the run registry (synthetic-cloud or synthetic-local per engine).
    try:
        import run_registry
        engine = link["engine"]
        privacy = "synthetic-cloud" if engine == "openai" else "synthetic-local"
        m = link["metrics"]
        run_registry.log_run("confide_red_linkability", "ru", privacy=privacy,
                             model=link["model"],
                             metrics={"accuracy": m["accuracy"], "roc_auc": m["roc_auc"],
                                      "f1": m["f1"], "majority_accuracy": m["majority_accuracy"]},
                             extra={"n_pairs": link["n_pairs"], "n_same": link["n_same"],
                                    "n_diff": link["n_diff"],
                                    "acc_ci95": [link["bootstrap_ci"]["accuracy"]["lo95"],
                                                 link["bootstrap_ci"]["accuracy"]["hi95"]],
                                    "auc_ci95": [link["bootstrap_ci"]["roc_auc"]["lo95"],
                                                 link["bootstrap_ci"]["roc_auc"]["hi95"]]})
    except Exception as e:  # registry is best-effort, never block results
        print(f"[link] run_registry skipped: {e}")

    if link_only:
        return  # inference/singling-out unchanged; skip to keep cloud-attacker runs cheap

    results = {"model": MODEL, "engine": os.environ.get("LLM_API", "ollama"), "clients": {},
               "linkability": link,
               "singling_out_note": ("ILLUSTRATIVE singling-out (method demo, not a "
                                     "re-identification probability). " + kanon.independence_caveat())}

    # 1) INFERENCE (3 prompts) + 2) SINGLING-OUT
    for cl in clients:
        if not red.get(cl):
            continue
        joined = "\n\n=== СЕССИЯ ===\n\n".join(red[cl])
        inf, of = inference_attack(joined, TRUTH[cl])
        results["clients"][cl] = {"inference": inf, "of": of, "singling_out": singling_out(cl)}
        best = max(inf.values()) if inf else 0
        print(f"[red] client-{cl}: inference best {best}/{of} {inf} | singling_out {results['clients'][cl]['singling_out']['singles_out']}")

    suffix = os.environ.get("CONFIDE_RED_SUFFIX", "")
    json.dump(results, open(os.path.join(HERE, f"confide-red-results{suffix}.json"), "w"), ensure_ascii=False, indent=2)
    open(os.path.join(HERE, f"CONFIDE-RED-RESULTS{suffix}.md"), "w").write(render_md(results))
    print("[red] wrote CONFIDE-RED-RESULTS.md + .json")


def render_md(results):
    """Render the CONFIDE-Red results dict to markdown. Shared by main() and the
    deterministic regen path so the committed .md always equals the script output."""
    md = ["# CONFIDE-Red — re-identification of anonymized transcripts", "",
          f"Attacker `{results['model']}` via {results['engine']}. Three GDPR Art-29 attacks "
          "(inference / singling-out / linkability) against the CONFIDE-redacted output. "
          "Synthetic data; attributes fabricated.", "",
          "## 1. Inference attack (by prompt strategy — top-3 attribute recovery)", "",
          "| Client | direct | reason | investigator | of | singled out? (illustrative) |", "|---|--:|--:|--:|--:|---|"]
    for cl, r in results["clients"].items():
        inf = r["inference"]
        so = r["singling_out"]
        verdict = ("**YES** (" if so["singles_out"] else "no (") + str(so["expected_matches"]) + ")"
        md.append(f"| {cl} | {inf.get('direct','-')} | {inf.get('reason','-')} | {inf.get('investigator','-')} | "
                  f"{r['of']} | {verdict} |")
    lk = results.get("linkability", {})
    md += ["", "## 2. Singling-out — ILLUSTRATIVE", "",
           "> **ILLUSTRATIVE / methodological demonstration, not a re-identification "
           "probability.** Computed by the shared `kanon` estimator (identical numbers "
           "to privacy-utility-RESULTS.md). Personas are synthetic, so this shows *how* "
           "a surviving quasi-identifier combination is assessed (GDPR Art-29 / "
           "k-anonymity), not a precise probability. The load-bearing signal is the "
           "**relative ranking** of exposure and the **sensitivity verdict**, not the "
           "point value.", "",
           "_" + kanon.independence_caveat() + "_", "",
           "Entity-aware survivor detection (gold quasi entity left unmasked by the "
           "default stack) feeds one sourced prior table (`kanon.PRIORS`); the surviving "
           "fractions multiply to an expected matching-population count; below 1 would "
           "mean singling-out.", "",
           "| Client | expected matches (illustrative) | dims used | singles out? | verdict robust to ±0.5x–2x priors? |",
           "|---|--:|---|---|---|"]
    for cl, r in results["clients"].items():
        so = r["singling_out"]
        md.append(f"| {cl} | {so['expected_matches']} | {', '.join(so['dims_used'])} | "
                  f"{'**YES**' if so['singles_out'] else 'no'} | "
                  f"{'yes' if so.get('verdict_robust') else '**no (flips)**'} |")
    md += render_linkability_md(lk)
    md += ["",
           "_Prompt-strategy spread shows which framing the anonymizer is least robust to. "
           "Rising recovery + singling-out + linkability are the three ways therapy de-id "
           "fails after the names are gone._"]
    return "\n".join(md) + "\n"


def render_linkability_md(lk):
    """Render the FULL-MATRIX linkability benchmark (B8: not a single-pair demo).
    Accepts the run_linkability() results dict; falls back gracefully if empty."""
    if not lk or "metrics" not in lk:
        return ["", "## 3. Linkability", "", "_No linkability benchmark in this run._"]
    m = lk["metrics"]
    ci = lk["bootstrap_ci"]
    a_ci, u_ci = ci["accuracy"], ci["roc_auc"]
    maj = m["majority_accuracy"]
    beats = (a_ci["lo95"] > maj) or (u_ci["lo95"] > 0.5)
    verdict = ("**Redaction does NOT fully defeat linkability** — the attacker beats "
               "chance." if beats else
               "**Redaction defeats cross-session linkability at this scale** — the "
               "attacker does not beat chance (accuracy CI overlaps the majority-class "
               "baseline and AUC CI overlaps 0.5).")
    return ["", "## 3. Linkability (full pair-matrix benchmark)", "",
            f"Anonymeter framing: given two REDACTED sessions, can the attacker tell whether "
            f"they belong to the SAME client? Over {lk['n_docs']} redacted docs we score "
            f"**{lk['n_pairs']} pairs** ({lk['n_same']} SAME, {lk['n_diff']} DIFFERENT). "
            f"DIFFERENT pairs are deterministically strided (stride "
            f"{lk['sampling']['diff_stride']}; {lk['sampling']['dropped_diff']} of "
            f"{lk['sampling']['total_diff']} dropped — no RNG, no silent truncation). "
            f"Attacker `{lk['model']}` via {lk['engine']}, SAME = positive class.", "",
            "| metric | value | 95% CI (bootstrap, 2000×) |",
            "|---|--:|---|",
            f"| accuracy | {m['accuracy']:.3f} | {a_ci['lo95']:.3f}–{a_ci['hi95']:.3f} |",
            f"| ROC-AUC | {m['roc_auc']:.3f} | {u_ci['lo95']:.3f}–{u_ci['hi95']:.3f} |",
            f"| precision (SAME) | {m['precision']:.3f} | — |",
            f"| recall (SAME) | {m['recall']:.3f} | — |",
            f"| F1 (SAME) | {m['f1']:.3f} | — |",
            f"| base rate P(SAME) | {m['base_rate_same']:.3f} | — |",
            f"| majority-class accuracy | {maj:.3f} | — |", "",
            "Confusion matrix (rows = truth, cols = attacker verdict):", "",
            "| | called SAME | called DIFFERENT |",
            "|---|--:|--:|",
            f"| **truth SAME** | {m['tp']} (TP) | {m['fn']} (FN) |",
            f"| **truth DIFFERENT** | {m['fp']} (FP) | {m['tn']} (TN) |", "",
            (f"> **Mechanism (read the AUC honestly):** {lk['leak_note']}"
             if lk.get("leak_note") else ""), "",
            f"**Verdict:** {verdict}"]


if __name__ == "__main__":
    main()
