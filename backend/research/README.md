# Earned vs Fabricated Advantage: research pipeline

Measures how much of the screening-score gain from LLM resume rewriting comes from
claims the original resume does not support. The problem statement, research questions,
objectives and methodology are in the project doc; this folder is the code for them.

```
resume-job pair ─┬─ original ─────────────────────────┐
                 ├─ LLM rewrite ──┬─ stripped ────────┤
                 │                ├─ control ─────────┤──> ATS screener + LLM screener ──> analyze.py
                 │                └─ guarded ─────────┤
                 └─ rule-based builder ───────────────┘
fabricated share = (S_llm − S_stripped) ÷ (S_llm − S_orig)
```

| File | What it does |
| --- | --- |
| `claims.py` | The claim verifier: splits a rewrite into lines, extracts typed claims (skill, metric, role_scope, credential, content), checks each against the original, and strips unsupported ones |
| `rewriters.py` | The versions: LLM rewrite, rule-based rewrite (`app/resume_builder.py`), guarded rewrite |
| `screeners.py` | ATS score (`app/ats.py`) and LLM screener score |
| `llm.py` | OpenAI-compatible client (Ollama, Groq, ...), disk cache, and `FakeLLM` for tests |
| `data.py` | Loads the Kaggle resumes, the job snapshot, and makes matched / career-changer pairs |
| `fetch_jobs.py` | Saves a dated job snapshot from the public job APIs |
| `run_experiment.py` | Runs every pair, writes one JSON line per pair and sample, resumable |
| `analyze.py` | RQ1–RQ3 numbers, bootstrap CIs, statistical tests, Markdown report |
| `labelling.py` | Exports claims for hand labelling; scores the verifier (kappa, precision, recall, F1) |

All commands run from `backend/` with the project venv.

## 0. Check it works (no model, no download)

```bash
python -m pytest tests/test_research.py -q
python -m research.run_experiment --sample --rewriter fake --screener fake --samples 2 --out research/results/smoke.jsonl
python -m research.analyze research/results/smoke.jsonl
```

`FakeLLM` only fabricates and never genuinely improves a resume, so the smoke report
shows a fabricated share of 100%. That is the expected answer, not a bug.

## 1. Get the data

1. Resumes: download the [Kaggle Resume Dataset](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset)
   (free Kaggle login) and put `Resume.csv` at `research/data/Resume.csv`. Do not commit it.
2. Jobs: `python -m research.fetch_jobs --per-category 2`. It prints the categories the
   public APIs could not fill; add public postings for those by hand to
   `research/data/jobs_snapshot.json` (fields: `id`, `title`, `company`, `description`,
   `tags`, `category`, `url`). Freeze this file: the experiment must use one snapshot.

## 2. Get the models

Install [Ollama](https://ollama.com), then pull a rewriter and a screener from **different
model families** (so the screener's preference for its own writing does not inflate the result).
The reference setup fits a 6 GB laptop GPU:

```bash
ollama pull qwen3.5:4b
ollama pull gemma3:4b
ollama create qwen3.5-4b-8k -f research/ollama/qwen3.5-4b-8k.Modelfile
ollama create gemma3-4b-8k -f research/ollama/gemma3-4b-8k.Modelfile
```

The `-8k` variants only raise the context window to 8,192 tokens. Ollama's default (4,096)
silently truncates a long resume + job + rewrite. Long resumes (over 1,500 words, 98 of 2,482)
are skipped with `--max-words`. Thinking models (Qwen3/3.5) have thinking turned off for
Ollama calls (`reasoning_effort: none`), which makes them about 40x faster here.

Any OpenAI-compatible API also works: pass `model@base_url` and set `LLM_API_KEY`, e.g.
`--rewriter llama-3.1-8b-instant@https://api.groq.com/openai/v1`.

## 3. Calibrate the verifier first (objective 3)

Run a small pilot, export 100 claims, have two people label them, and check the verifier
before the main run:

```bash
python -m research.run_experiment --resumes research/data/Resume.csv --jobs research/data/jobs_snapshot.json --n 30 --rewriter qwen3.5-4b-8k --screener none --out research/results/pilot.jsonl
python -m research.labelling export research/results/pilot.jsonl --n 100 --out research/labels
python -m research.labelling evaluate research/labels/sheet.csv
```

If recall on unsupported claims is low, adjust the thresholds at the top of `claims.py`
(`CONTENT_LOW`, `CONTENT_HIGH`, `REVERT_MIN_SIM`) or the word lists, then re-evaluate.
Report the final numbers in the thesis.

## 4. Main run

Two models do not fit a 6 GB GPU together, so run in two phases. Phase A makes every
rewrite (cached); phase B re-runs with the screener, gets every rewrite from the cache,
and so never swaps models:

```bash
python -m research.run_experiment --resumes research/data/Resume.csv --jobs research/data/jobs_snapshot.json --n 200 --rewriter qwen3.5-4b-8k --screener none --out research/results/rewrites.jsonl
python -m research.run_experiment --resumes research/data/Resume.csv --jobs research/data/jobs_snapshot.json --n 200 --rewriter qwen3.5-4b-8k --screener gemma3-4b-8k --out research/results/main.jsonl
python -m research.analyze research/results/main.jsonl
```

The stratified sample is a prefix: `--n 30` (the pilot) is the first 30 resumes of `--n 200`,
so pilot rewrites are reused. On an RTX 4050 phase A takes about 1-2 min per pair.

Interrupted? Run the same command again: finished pairs are skipped, and every LLM reply is
cached in `research/cache/`, so reruns reproduce the same numbers.

**Compute budget.** Each pair and sample makes 1 rewrite call, up to 2 revision calls, and
about 11 screener calls (6 versions + up to 5 per-type ablations). For 1,000 pairs × 3
samples that is roughly 40,000 calls. A local 8B model on a laptop CPU takes about 5–20 s a
call, which is days, not hours. Options: use a GPU, use a hosted API with `--workers 4`, run
`--samples 1`, or pass `--no-llm-ablation` so per-type ablations are scored by the ATS only.

## Outputs

* `main.jsonl`: one record per pair and sample, with all texts, scores and claim counts
* `main.report.md`: tables for RQ1–RQ3, ready to adapt for the results chapter
* `main.summary.json`: the same numbers, machine-readable

## The app (objective 7)

`/audit` in the frontend runs the same verifier, stripper and ATS scorer on one resume
(`research/audit.py`, endpoint `POST /api/audit`). Paste a resume and a job; it either makes
an LLM rewrite or audits one you paste from ChatGPT etc., highlights each unsupported claim,
splits the gain into earned and fabricated, and offers the guarded rewrite. The model is
`AUDIT_LLM` (default `qwen3.5-4b-8k`).
