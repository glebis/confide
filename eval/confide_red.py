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
            body["temperature"] = temperature
            body["max_tokens"] = 400
        url = base + "/v1/chat/completions"
        key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
        if key:
            headers["Authorization"] = "Bearer " + key
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


def main():
    import anonymize
    clients = (os.environ.get("CONFIDE_RED_CLIENTS") or "a,b,c").split(",")
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

    results = {"model": MODEL, "engine": os.environ.get("LLM_API", "ollama"), "clients": {}, "linkability": {},
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

    # 3) LINKABILITY — same-client pair should be 'same', cross-client pair 'different'
    if len(clients) >= 2 and red.get(clients[0]) and red.get(clients[1]):
        a, b = clients[0], clients[1]
        def linkq(x, y):
            p = ('Это два анонимизированных транскрипта психотерапии. Один и тот же это человек? '
                 'Верни ТОЛЬКО JSON {"same":true|false,"confidence":0..1}.\n\nA:\n' + x[:7000] + "\n\nB:\n" + y[:7000])
            return llm_json(p)
        same = linkq(red[a][0], red[a][1]).get("same")
        diff = linkq(red[a][0], red[b][0]).get("same")
        results["linkability"] = {"same_pair_called_same": same is True, "diff_pair_called_same": diff is True,
                                  "linkable": (same is True and diff is False)}
        print(f"[red] linkability: same-pair→same={same}, diff-pair→same={diff}, linkable={results['linkability']['linkable']}")

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
    md += ["", "## 3. Linkability", "",
           f"Same-client pair judged same person: **{lk.get('same_pair_called_same')}**; "
           f"different-client pair judged same: **{lk.get('diff_pair_called_same')}**; "
           f"→ linkable: **{lk.get('linkable')}**.", "",
           "_Prompt-strategy spread shows which framing the anonymizer is least robust to. "
           "Rising recovery + singling-out + linkability are the three ways therapy de-id "
           "fails after the names are gone._"]
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
