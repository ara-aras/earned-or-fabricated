"""Rule-based ATS screen + HR review.

The composite ATS score is a weighted sum of plain, named checks (keyword
match, sections, measurable results, action verbs, contact, length, filler).
It is the deterministic screener of the research experiment (research/screeners.py).
"""
from __future__ import annotations

import re

from app.text_rules import (bullets_of, contact_info, filler_hits, find_skills,
                            has_term, is_quantified, parse_sections, seniority_of,
                            starts_with_action_verb)

WEIGHTS = {
    "keywords": 30, "sections": 12, "quantified": 14, "action_verbs": 10,
    "contact": 8, "length": 8, "filler": 8,
}


def _status(score: float) -> str:
    return "pass" if score >= 0.75 else "warn" if score >= 0.4 else "fail"


def screen(resume_text: str, job: dict | None, job_kw: list[str]) -> dict:
    text_l = resume_text.lower()
    sections = parse_sections(resume_text)
    bullets = [b for sec in ("experience", "projects") for b in bullets_of(sections.get(sec, []))]
    checks = []

    # keywords
    if job_kw:
        matched = [k for k in job_kw if has_term(text_l, k.lower())]
        missing = [k for k in job_kw if k not in matched]
        ratio = len(matched) / max(5, len(job_kw))  # a listing naming 1 skill isn't a 100% match
        s = min(1.0, ratio / 0.7)
        detail = f"{len(matched)}/{len(job_kw)} of the listing's keywords found" +             (" (the listing names very few skills)" if len(job_kw) < 5 else "")
    else:
        matched, missing = find_skills(resume_text), []
        s = min(1.0, len(matched) / 6)
        detail = f"{len(matched)} recognizable skills (no target job — generic check)"
    checks.append({"id": "keywords", "label": "Keyword match", "score": s, "detail": detail})

    # sections
    need = ["skills", "experience", "education"]  # summary is optional (new grads usually skip it)
    have = [n for n in need if sections.get(n)]
    if sections.get("projects") and "experience" not in have:
        have.append("experience")  # projects stand in for experience for graduates
    s = len(set(have)) / len(need)
    miss = [n for n in need if n not in have]
    checks.append({"id": "sections", "label": "Standard sections", "score": s,
                   "detail": "all standard headings present" if not miss else "missing: " + ", ".join(miss)})

    # quantified bullets
    if bullets:
        q = sum(is_quantified(b) for b in bullets)
        s = min(1.0, (q / len(bullets)) / 0.6)
        detail = f"{q}/{len(bullets)} bullets contain a number or metric"
    else:
        s, detail = 0.0, "no bullet points found under experience/projects"
    checks.append({"id": "quantified", "label": "Measurable results", "score": s, "detail": detail})

    # action verbs
    if bullets:
        a = sum(starts_with_action_verb(b) for b in bullets)
        s = min(1.0, (a / len(bullets)) / 0.8)
        detail = f"{a}/{len(bullets)} bullets open with an action verb"
    else:
        s, detail = 0.0, "no bullets to check"
    checks.append({"id": "action_verbs", "label": "Action verbs", "score": s, "detail": detail})

    # contact
    c = contact_info(resume_text)
    s = (0.7 if c["email"] else 0) + (0.3 if c["phone"] else 0)
    checks.append({"id": "contact", "label": "Contact info", "score": s,
                   "detail": ", ".join(k for k, v in c.items() if v) + " found" if any(c.values())
                   else "no email or phone detected"})

    # length
    words = len(re.findall(r"[A-Za-z']+", resume_text))
    s = 1.0 if 180 <= words <= 800 else 0.6 if 110 <= words <= 1000 else 0.25
    checks.append({"id": "length", "label": "Length", "score": s,
                   "detail": f"{words} words (typical one-page resume: 180–800)"})

    # filler
    f = filler_hits(resume_text)
    s = max(0.0, 1 - 0.34 * len(f))
    checks.append({"id": "filler", "label": "Filler phrases", "score": s,
                   "detail": "none found" if not f else "found: " + ", ".join(f[:5])})

    total = 0.0
    for ch in checks:
        ch["weight"] = WEIGHTS[ch["id"]]
        ch["score"] = round(float(ch["score"]), 3)
        ch["status"] = _status(ch["score"])
        total += ch["weight"] * ch["score"]
    score = int(round(total / sum(WEIGHTS.values()) * 100))
    verdict = "STRONG_MATCH" if score >= 75 else "WEAK_MATCH" if score >= 55 else "REJECT"

    return {
        "score": score,
        "verdict": verdict,
        "checks": checks,
        "keywords": {"matched": matched, "missing": missing},
        "rejection_points": [f"{c['label']}: {c['detail']}" for c in checks if c["status"] == "fail"],
        "hr": _hr_review(score, checks, sections, job, matched, missing, resume_text),
    }


_STRENGTH_COPY = {
    "keywords": "Speaks the listing's language — keyword coverage is solid.",
    "quantified": "Backs claims with numbers, which is what makes a skim stop.",
    "action_verbs": "Bullets read as ownership, not duties.",
    "sections": "Clean, conventional structure — easy to skim.",
    "contact": "Easy to reach.",
    "filler": "No buzzword filler.",
}
_CONCERN_COPY = {
    "keywords": "Missing several things the listing explicitly asks for.",
    "quantified": "Few measurable outcomes — hard to tell the size of the impact.",
    "action_verbs": "Bullets read like job duties rather than accomplishments.",
    "sections": "Non-standard structure; parsers and skimmers may miss content.",
    "contact": "No clear way to contact the candidate.",
    "length": "Length is outside the typical one-page range.",
    "filler": "Relies on generic self-descriptions instead of evidence.",
}


def _hr_review(score, checks, sections, job, matched, missing, resume_text):
    by = {c["id"]: c for c in checks}
    strengths = [_STRENGTH_COPY[i] for i in _STRENGTH_COPY if by[i]["status"] == "pass"][:3]
    concerns = [_CONCERN_COPY[i] for i in _CONCERN_COPY if by[i]["status"] == "fail"][:3]
    if job:
        js = seniority_of(job.get("title", ""))
        header = " ".join(sections.get("_header", [])[:2])
        rs = seniority_of(header) or seniority_of(resume_text[:300])
        if js is not None and js >= 3 and (rs is None or rs < 3):
            concerns.append(f"Listing is a {job['title']} role; the resume doesn't signal that seniority.")
    if score >= 75 and by["keywords"]["score"] >= 0.6:
        decision, label = "advance", "Advance to interview"
    elif score >= 55:
        decision, label = "hold", "Hold — maybe, if the pipeline is thin"
    else:
        decision, label = "reject", "Reject at screen"
    # What a recruiter's ~7-second skim actually lands on.
    first_bullet = next(iter(bullets_of(sections.get("experience", []) + sections.get("projects", []))), "")
    skim = [x for x in [
        " ".join(sections.get("_header", [])[:2]),
        (sections.get("skills") or [""])[0][:120],
        first_bullet[:120],
    ] if x]
    return {"decision": decision, "label": label, "strengths": strengths,
            "concerns": concerns, "skim": skim,
            "must_ask": missing[:3]}

