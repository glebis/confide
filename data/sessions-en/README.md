# EN datasets

- **`pii-eval.jsonl`** — curated **synthetic** English slice (CC-BY-4.0, ships in-repo).
- **`pii-eval-ai4privacy.jsonl`** — the **EN-real** slice derived from
  [`ai4privacy/pii-masking-300k`](https://huggingface.co/datasets/ai4privacy/pii-masking-300k).
  **NOT committed** — AI4Privacy's license restricts redistribution of its source text and
  derivatives (academic/non-commercial, no redistribution). Build it **locally**, under
  AI4Privacy's own license, before running the EN-real benchmark:

  ```bash
  PYTHONPATH=src python3 -m confide_eval.data.build_dataset        # writes pii-eval-ai4privacy.jsonl (gitignored)
  # or reconstruct text for an existing gold:
  PYTHONPATH=src python3 -m confide_eval.data.fetch_ai4privacy     # writes pii-eval-ai4privacy.local.jsonl (gitignored)
  ```

  The EN-real detector caches and results are likewise local-only and gitignored. You are
  responsible for your own rights to access/use AI4Privacy.
