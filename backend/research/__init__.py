"""Earned vs Fabricated Advantage -- the research pipeline.

Measures how much of the screening-score gain from LLM resume rewriting comes
from claims the original resume does not support. `app/` holds the shared
rule layers (ATS screen, resume rules, job fetch) and the web API.

Modules:
  llm          OpenAI-compatible chat client (Ollama, Groq, ...) + disk cache + FakeLLM
  claims       claim extraction, typing and support checking (the verifier)
  rewriters    the five resume versions: original, LLM, stripped, rule-based, guarded
  screeners    rule-based ATS score and LLM screener score
  data         Kaggle resumes, job snapshot, resume-job pairing
  fetch_jobs   builds the dated job-description snapshot
  run_experiment  runs every pair and writes results JSONL
  analyze      fabricated share, confidence intervals, statistical tests, report
  labelling    export claims for hand labelling; score the verifier against labels
"""
