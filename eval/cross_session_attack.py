#!/usr/bin/env python3
"""Cross-session (longitudinal) re-identification attack.

The single-session reconstruction attack misses the real therapy threat: an agent
that sees the BULK of one client's anonymized sessions can correlate quasi-identifiers
that accumulate ACROSS sessions (recurring employer hints, a city, an age, a
medication, a rare event) and single the person out — even when each session alone
looks safe. (Cross-document linkage; cf. PANORAMA, RAT-Bench population modelling,
Staab et al. inference.)

Method: for each synthetic client, anonymize all 5 sessions with the default local
stack (merged redaction mask), then run an LLM attacker twice —
  (A) SINGLE: given ONE redacted session, infer attributes;
  (B) BULK: given ALL redacted sessions together, infer attributes.
Score top-3 hits vs known truth; the BULK−SINGLE delta is the cross-session leak.

Engine-agnostic LLM (set LLM_API=openai + LLM_BASE_URL=<llama.cpp> to avoid Ollama
contention). Synthetic data only. Outputs cross-session-RESULTS.md + .json.
"""
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "session-anonymizer", "scripts"))
RU = os.path.join(HERE, "..", "sessions-ru")
MODEL = os.environ.get("LLM_MODEL", "qwen2.5:3b")

# Known ground-truth attributes per synthetic client (for scoring only).
TRUTH = {
    "a": {"profession": ["маркетолог"], "employer": ["яндекс"], "city": ["калуга"],
          "age": ["34", "тридцать четыре"], "medication": ["сертралин"], "partner": ["андрей"]},
    "b": {"profession": ["программист"], "employer": ["контур"], "city": ["кострома", "москв"],
          "age": ["41", "сорок один"], "medication": ["флуоксетин"], "family": ["алексей", "светлан"]},
}
ATTRS = ["profession", "employer", "city", "age", "medication", "other_clues"]


def llm_json(prompt, temperature=0.3, num_predict=512):
    api = os.environ.get("LLM_API", "ollama").lower()
    base = os.environ.get("LLM_BASE_URL", os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
    msgs = [{"role": "user", "content": prompt}]
    if api == "openai":
        url = base + "/v1/chat/completions"
        body = {"model": MODEL, "messages": msgs, "temperature": temperature, "max_tokens": num_predict, "stream": False}
    else:
        url = base + "/api/chat"
        body = {"model": MODEL, "messages": msgs, "stream": False, "options": {"temperature": temperature, "num_predict": num_predict}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read())
    out = d["choices"][0]["message"]["content"] if api == "openai" else d["message"]["content"]
    out = re.sub(r"<think>.*?</think>", "", out, flags=re.DOTALL)
    m = re.search(r"\{.*\}", out, re.DOTALL)
    try:
        return json.loads(m.group()) if m else {}
    except json.JSONDecodeError:
        return {}


def merge(spans):
    spans = sorted(spans, key=lambda s: (s.start, -(s.end - s.start)))
    out = [[spans[0].start, spans[0].end]] if spans else []
    for s in spans[1:]:
        if s.start < out[-1][1]:
            out[-1][1] = max(out[-1][1], s.end)
        else:
            out.append([s.start, s.end])
    return out


def redact_session(text, anonymize):
    spans = anonymize.run_natasha(text) + anonymize.run_regex(text) + anonymize.run_ollama(text, MODEL)
    iv = merge(spans)
    out, last = [], 0
    for s, e in iv:
        out.append(text[last:s]); out.append("<X>"); last = e
    out.append(text[last:])
    return "".join(out)


def attack(redacted_text):
    prompt = ("Ниже — анонимизированные транскрипты психотерапии ОДНОГО клиента (личные "
              "данные заменены на <X>). По СОВОКУПНОСТИ сохранившихся деталей предположи "
              "атрибуты клиента. Верни ТОЛЬКО JSON с топ-3 догадками на атрибут: "
              '{"profession":["",""],"employer":["",""],"city":["",""],"age":["",""],'
              '"medication":["",""],"other_clues":""}. Текст:\n\n' + redacted_text[:16000])
    return llm_json(prompt)


def hit(guess, truths):
    cand = guess if isinstance(guess, list) else [guess]
    return any(any(t in str(c).lower() for t in truths) for c in cand[:3])


def score(guess, truth):
    return sum(int(hit(guess.get(a, []), truth[a])) for a in truth) , len(truth)


def main():
    import anonymize
    results = {"model": MODEL, "engine": os.environ.get("LLM_API", "ollama"), "clients": {}}
    for cl in ("a", "b"):
        reds = []
        for s in range(1, 6):
            p = os.path.join(RU, f"client-{cl}", f"session-0{s}.md")
            reds.append(redact_session(open(p, encoding="utf-8").read(), anonymize))
        # (A) single-session: best over the 5 individually
        single_best = (0, 0)
        for r in reds:
            g = attack(r)
            single_best = max(single_best, score(g, TRUTH[cl]), key=lambda x: x[0])
        # (B) bulk: all sessions together
        bulk_guess = attack("\n\n=== СЕССИЯ ===\n\n".join(reds))
        bulk = score(bulk_guess, TRUTH[cl])
        results["clients"][cl] = {
            "single_best_recovered": single_best[0], "of": single_best[1],
            "bulk_recovered": bulk[0], "bulk_of": bulk[1],
            "cross_session_gain": bulk[0] - single_best[0],
            "bulk_guess": bulk_guess,
        }
        print(f"[xsession] client-{cl}: single {single_best[0]}/{single_best[1]} -> "
              f"BULK {bulk[0]}/{bulk[1]}  (cross-session gain +{bulk[0]-single_best[0]})")

    json.dump(results, open(os.path.join(HERE, "cross-session-results.json"), "w"), ensure_ascii=False, indent=2)
    md = ["# Cross-session (longitudinal) re-identification", "",
          f"Attacker: `{results['model']}` via {results['engine']}. The same LLM infers client "
          "attributes from (A) ONE redacted session vs (B) ALL of the client's redacted sessions "
          "together. The **bulk − single** gain is the cross-session linkage risk that "
          "single-session de-id evaluation misses.", "",
          "| Client | single-session best | **all-sessions (bulk)** | cross-session gain |",
          "|---|--:|--:|--:|"]
    for cl, r in results["clients"].items():
        md.append(f"| {cl} | {r['single_best_recovered']}/{r['of']} | "
                  f"**{r['bulk_recovered']}/{r['bulk_of']}** | +{r['cross_session_gain']} |")
    md += ["", "_A positive gain means accumulating quasi-identifiers across sessions let the "
           "attacker recover attributes no single session exposed — the longitudinal therapy "
           "de-identification risk. Synthetic data; attributes are fabricated._"]
    open(os.path.join(HERE, "cross-session-RESULTS.md"), "w").write("\n".join(md) + "\n")
    print("[xsession] wrote cross-session-RESULTS.md + .json")


if __name__ == "__main__":
    main()
