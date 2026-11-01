"""The two screeners every resume version is scored by.

* ats   -- the project's rule-based screen (app/ats.py), returned as an unrounded 0-100 float so small differences
           between versions are not lost to rounding.
* llm   -- an LLM asked for a 0-100 match score, averaged over `runs`. Use a
           different model family from the rewriter to avoid self-preference
           (Xu et al.), or the same one to measure it.
"""
from __future__ import annotations

import json
import re

from app import ats
from research.llm import LLM
from research.rewriters import job_text

SCORE_SYSTEM = "You are an experienced recruiter screening job applications."
SCORE_PROMPT = """### SCORE
Rate how well this resume matches the job, from 0 (no match) to 100 (ideal candidate). Judge only the qualifications the resume states.

Reply with JSON only: {{"score": <integer 0-100>}}

<job>
{job}
</job>

<resume>
{resume}
</resume>"""


def ats_score(text: str, job: dict, job_kw: list[str]) -> float:
    checks = ats.screen(text, job, job_kw)["checks"]
    total_w = sum(c["weight"] for c in checks)
    return round(100 * sum(c["weight"] * c["score"] for c in checks) / total_w, 3)


def parse_score(reply: str) -> float | None:
    try:
        val = json.loads(re.search(r"\{.*?\}", reply, re.S).group(0))["score"]
        return float(val) if 0 <= float(val) <= 100 else None
    except (AttributeError, ValueError, KeyError, TypeError):
        m = re.search(r"\b(100|\d{1,2})\b", reply)
        return float(m.group(1)) if m else None


def llm_score(llm: LLM, text: str, job: dict, runs: int = 1) -> float | None:
    vals = []
    for seed in range(runs):
        reply = llm.complete(SCORE_PROMPT.format(job=job_text(job), resume=text),
                             system=SCORE_SYSTEM, temperature=0.0 if runs == 1 else 0.7, seed=seed)
        v = parse_score(reply)
        if v is not None:
            vals.append(v)
    return round(sum(vals) / len(vals), 3) if vals else None
