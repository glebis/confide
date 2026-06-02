#!/usr/bin/env python3
"""Speed compare the local-LLM layer across engines (Ollama vs llama.cpp).

Runs the SAME anonymize.run_ollama() over a few SYNTHETIC snippets against each
engine via env switching, reports wall-clock per call. Synthetic data only.
"""
import os, sys, time, statistics as st
from confide_eval import paths
sys.path.insert(0, os.fspath(paths.ANONYMIZER_SCRIPTS))
import anonymize

SAMPLES = [
    "Меня зовут Марина Волкова, мне 34, маркетолог в Яндексе. Пью сертралин 100 мг.",
    "Брат Игорь живёт в Костроме, телефон +7-916-555-21-43, почта i@example.ru.",
    "**Т:** Здравствуйте. **К:** Я тревожусь на работе, начальник Дмитрий Олегович давит.",
]

def bench(label, env, model):
    for k,v in env.items(): os.environ[k]=v
    ts=[]
    for s in SAMPLES:
        t=time.time(); spans=anonymize.run_ollama(s, model); dt=time.time()-t
        ts.append(dt)
    print(f"{label:12} model={model:28} per-call: "
          f"min {min(ts):.2f}s / median {st.median(ts):.2f}s / max {max(ts):.2f}s  (n={len(ts)})")
    return st.median(ts)

if __name__ == "__main__":
    eng = sys.argv[1] if len(sys.argv)>1 else "both"
    if eng in ("ollama","both"):
        bench("ollama", {"LLM_API":"ollama","OLLAMA_HOST":"http://localhost:11434"}, "qwen2.5:3b")
    if eng in ("llamacpp","both"):
        bench("llama.cpp", {"LLM_API":"openai","LLM_BASE_URL":"http://localhost:8080"},
              os.environ.get("LCPP_MODEL","qwen2.5-3b-instruct"))
