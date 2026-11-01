"""Candidate-facing earned-vs-fabricated audit (objective 7).

One resume, one job: take an LLM rewrite (made here, or pasted in by the user
from ChatGPT etc.), check every claim against the original, and split the ATS
gain into the part the original supports (earned) and the part it does not
(fabricated). Also returns the guarded rewrite, which keeps only earned gain.
Same verifier, stripper and scorer as the experiment, so the app shows on one
resume exactly what the thesis measures over the dataset.
"""
from __future__ import annotations

from app.text_rules import job_keywords
from research import claims as cl
from research import rewriters as rw
from research.analyze import MIN_GAIN
from research.llm import LLM
from research.screeners import ats_score


def _units_by_line(text: str) -> list[list[tuple[int, str]]]:
    """Lines of the rewrite, each a list of (unit index, unit text) -- same numbering as verify()."""
    out, i = [], 0
    for line in cl.split_lines(text):
        row = []
        for u in line:
            row.append((i, u))
            i += 1
        out.append(row)
    return out


def audit(original: str, job: dict, rewrite: str | None = None, llm: LLM | None = None,
          guarded: bool = True, seed: int = 0) -> dict:
    if rewrite is None and llm is None:
        raise ValueError("need either a rewrite to audit or an LLM to make one")
    job_kw = job_keywords(job)
    terms = job_kw + list(job.get("tags") or [])

    source = "pasted" if rewrite is not None else "generated"
    if rewrite is None:
        rewrite = rw.llm_rewrite(llm, original, job, seed=seed)
    rep = cl.verify(original, rewrite, terms)
    texts = {"orig": original, "llm": rewrite, "stripped": cl.strip_fully(original, rewrite, terms)}
    rounds = 0
    if guarded and llm is not None:
        texts["guarded"], rounds = rw.guarded_rewrite(llm, original, job, terms, seed=seed,
                                                      first_draft=rewrite)
    scores = {v: round(ats_score(t, job, job_kw), 1) for v, t in texts.items()}

    gain = scores["llm"] - scores["orig"]
    fabricated = scores["llm"] - scores["stripped"]
    share = fabricated / gain if gain >= MIN_GAIN else None

    by_unit: dict[int, list[dict]] = {}
    for c in rep.unsupported:
        by_unit.setdefault(c.unit_index, []).append({"type": c.type, "text": c.text, "reason": c.reason})
    lines = []
    for row in _units_by_line(rewrite):
        lines.append([{"text": u, "claims": by_unit.get(i, []),
                       "closest_original": rep.evidence.get(i, ("", 0.0))[0] if i in by_unit else ""}
                      for i, u in row])

    return {
        "source": source,
        "refusal": rw.is_refusal(rewrite),
        "model": getattr(llm, "name", None),
        "scores": scores,
        "gain": round(gain, 1),
        "fabricated_gain": round(fabricated, 1),
        "earned_gain": round(scores["stripped"] - scores["orig"], 1),
        "fabricated_share": None if share is None else round(share, 3),
        "min_gain": MIN_GAIN,
        "counts": rep.counts(),
        "n_units": len(rep.units),
        "n_flagged_units": len(rep.unsupported_units()),
        "guarded_rounds": rounds,
        "lines": lines,
        "texts": texts,
    }
