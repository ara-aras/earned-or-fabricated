"""The resume versions compared in the study (methodology "Rewrite conditions").

  original    as collected
  llm         unguarded LLM tailoring, prompted the way consumer tools are
  stripped    llm minus every unsupported claim        (claims.strip)
  rule        the project's rule-based builder, style-only, cannot fabricate
  guarded     llm -> verifier -> LLM revises flagged lines -> verifier -> strip leftovers
  control     llm minus the same NUMBER of supported units (length-matched control)

The LLM prompt deliberately says nothing about honesty either way: the study
measures what ordinary tailoring does, not what a jailbreak or a careful
prompt does.
"""
from __future__ import annotations

import re
from typing import Callable, Iterable

from app.resume_builder import _rewrite as _style_rewrite
from app.text_rules import strip_html
from research import claims as cl
from research.llm import LLM

REWRITE_SYSTEM = "You are an expert resume writer."
REWRITE_PROMPT = """Tailor the resume below to the job description so the candidate has the best possible chance of passing the employer's screening. Return only the full rewritten resume as plain text, one bullet or line per line, with no commentary.

<job>
{job}
</job>

<resume>
{resume}
</resume>"""

REVISE_PROMPT = """### REVISE
Some lines of a tailored resume make claims the candidate's ORIGINAL resume does not support. Rewrite each numbered line so it only states facts found in the original resume. Keep the wording style. If nothing in the line can be supported, return the number with nothing after it.

Reply with the same numbers, one per line, in the form "N. rewritten line". No commentary.

<original>
{original}
</original>

<lines>
{lines}
</lines>"""

MAX_JOB_CHARS = 4000


def job_text(job: dict) -> str:
    tags = ", ".join(job.get("tags") or [])
    desc = strip_html(job.get("description", ""))[:MAX_JOB_CHARS]
    return f"{job.get('title', '')}\n{('Tags: ' + tags) if tags else ''}\n{desc}".strip()


# Small models sometimes answer with an assessment ("the candidate's background is
# entirely unrelated ...") instead of a resume. Such outputs are not rewrites: they are
# counted as refusals and left out of the fabricated-share estimates.
_REFUSAL_RE = re.compile(
    r"\b(?:the|this) candidate(?:'s)?\b|\bno resume can\b|\bcannot be (?:successfully )?tailored\b"
    r"|\bplease provide\b|\bi (?:cannot|can't|am unable)\b|\bas an ai\b|\bmismatch between\b", re.I)


def is_refusal(text: str) -> bool:
    return bool(_REFUSAL_RE.search(text or ""))


def _clean_llm_output(text: str) -> str:
    text = re.sub(r"^```[a-z]*\n|\n```$", "", text.strip())
    text = re.sub(r"^(here is|here's)[^\n]*:\s*\n", "", text, flags=re.I)
    return text.replace("**", "").strip()


def llm_rewrite(llm: LLM, original: str, job: dict, seed: int, temperature: float = 0.7) -> str:
    out = llm.complete(REWRITE_PROMPT.format(job=job_text(job), resume=original),
                       system=REWRITE_SYSTEM, temperature=temperature, seed=seed)
    return _clean_llm_output(out)


def rule_rewrite(original: str) -> str:
    """Style-only pass of resume_builder over each sentence/bullet. Adds nothing."""
    out = []
    for line in cl.split_lines(original):
        new = []
        for unit in line:
            if len(unit.split()) < 4:
                new.append(unit)
                continue
            bullet = unit.lstrip().startswith(("-", "*", "•"))
            text, _ = _style_rewrite(unit, False, [])
            text = text or unit
            new.append(("- " if bullet else "") + text + ("." if unit.rstrip().endswith(".") else ""))
        out.append(new)
    return cl.join_lines(out)


def replace_units(text: str, new_units: dict[int, str]) -> str:
    """Swap units by index (as numbered by claims.units_of); "" deletes the unit."""
    lines, idx, out = cl.split_lines(text), 0, []
    for line in lines:
        kept = []
        for unit in line:
            rep = new_units.get(idx, unit).strip()
            if rep:
                kept.append(rep)
            idx += 1
        if kept or not line:
            out.append(kept)
    return cl.join_lines(out)


def guarded_rewrite(llm: LLM, original: str, job: dict, job_terms: Iterable[str], seed: int,
                    first_draft: str | None = None, rounds: int = 2,
                    judge: Callable[[str, str], bool] | None = None) -> tuple[str, int]:
    """Returns (text, revision rounds used). `first_draft` reuses the unguarded
    rewrite so guarded and unguarded start from the same draft."""
    text = first_draft if first_draft is not None else llm_rewrite(llm, original, job, seed)
    used = 0
    for _ in range(rounds):
        rep = cl.verify(original, text, job_terms, judge)
        bad = sorted(rep.unsupported_units())
        if not bad:
            break
        used += 1
        numbered = "\n".join(f"{n + 1}. {rep.units[i]}" for n, i in enumerate(bad))
        reply = llm.complete(REVISE_PROMPT.format(original=original, lines=numbered),
                             system=REWRITE_SYSTEM, temperature=0.2, seed=seed)
        fixes: dict[int, str] = {}
        for num, body in re.findall(r"^\s*(\d+)\.[ \t]*(.*)$", reply, re.M):
            n = int(num) - 1
            if 0 <= n < len(bad):
                fixes[bad[n]] = body.strip()
        if not fixes:
            break
        text = replace_units(text, fixes)
    return cl.strip_fully(original, text, job_terms, judge=judge), used
