"""Resume builder: restructures and tailors the USER'S OWN material.

This builder never adds a fact the user didn't give it. Using the rule
knowledge base in app/resume_kb.py it:

  * parses each role/project header into title / org / location / dates and
    normalises the dates ("Jun–Aug 2025" -> "Jun 2025 – Aug 2025"),
  * rewrites bullets for style only: weak openers -> action verbs, drops
    first-person pronouns and filler adverbs, fixes tense (past for finished
    roles, present for current ones), breaks up repeated opening verbs with
    same-meaning synonyms,
  * groups skills by type and puts the ones the listing asks for first,
  * picks the page budget and section order from the experience level
    (students lead with education, one page; 10+ years may use two),
  * runs a guideline lint (every item cites a rule id in resume_kb.GUIDELINES)
    and reports gaps / unquantified bullets as suggestions -- never filled in.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date

from app import resume_kb as kb
from app.text_rules import has_term, is_quantified

MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
_MONTH_RE = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_DATE_TOKEN = rf"(?:{_MONTH_RE}\s*)?(?:\d{{4}})?|present|current|now|summer\s+\d{{4}}|fall\s+\d{{4}}|spring\s+\d{{4}}|winter\s+\d{{4}}"
_DATES_RE = re.compile(
    rf"[\(\[,|·—–-]?\s*((?:{_MONTH_RE}\s*\d{{0,4}}|\d{{4}}|summer|fall|spring|winter)"
    rf"(?:\s*\d{{4}})?(?:\s*(?:-|–|—|to)\s*(?:{_MONTH_RE}\s*\d{{0,4}}|\d{{4}}|present|current|now))?)\s*[\)\]]?\s*$",
    re.I)


# --------------------------------------------------------------------------- dates
def _norm_month(tok: str) -> str:
    return tok[:3].capitalize()


def normalize_dates(raw: str) -> tuple[str, bool, int | None, int | None]:
    """-> (display, is_current, start_year, end_year)"""
    s = raw.strip().strip("()[]").replace("—", "–").replace(" to ", " – ")
    parts = [p.strip() for p in re.split(r"\s*[–-]\s*", s) if p.strip()]
    current = bool(re.search(r"present|current|now", s, re.I))

    def parse(p: str):
        m = re.match(rf"({_MONTH_RE})?\s*(\d{{4}})?", p, re.I)
        mon = _norm_month(m.group(1)) if m and m.group(1) else None
        yr = int(m.group(3)) if m and m.group(3) else None
        season = re.match(r"(summer|fall|spring|winter)\s*(\d{4})?", p, re.I)
        if season:
            return season.group(1).capitalize(), int(season.group(2)) if season.group(2) else yr
        return mon, yr

    if not parts:
        return raw, False, None, None
    a = parse(parts[0])
    if len(parts) == 1:
        disp = " ".join(x for x in [a[0], str(a[1]) if a[1] else None] if x)
        return disp or raw, current, a[1], a[1]
    if re.match(r"present|current|now", parts[1], re.I):
        b = ("Present", None)
    else:
        b = parse(parts[1])
    ay = a[1] or b[1]  # "Jun–Aug 2025": borrow the year
    left = " ".join(x for x in [a[0], str(ay) if ay else None] if x)
    right = b[0] if b[0] == "Present" else " ".join(x for x in [b[0], str(b[1]) if b[1] else None] if x)
    return f"{left} – {right}", current, ay, (date.today().year if current else b[1])


def _split_header(line: str, kind: str = "experience") -> dict:
    """'Software Intern — Acme Corp, Berlin (Jun–Aug 2025)' -> parts."""
    dates, cur, y0, y1 = "", False, None, None
    m = _DATES_RE.search(line)
    if m and re.search(r"\d{4}|present|current", m.group(1), re.I):
        dates, cur, y0, y1 = normalize_dates(m.group(1))
        line = line[: m.start()].rstrip(" ,|·—–-(")
    # strong separators first (— – | - at); commas only split org from location
    chunks = [b.strip() for b in re.split(r"\s+[—–|]\s+|\s+-\s+|\s+at\s+", line) if b.strip()]
    if len(chunks) >= 2 and kind == "projects":
        # "Course Planner — React, FastAPI, PostgreSQL": the rest is the tech stack
        title, org, loc = chunks[0], ", ".join(chunks[1:]), []
    elif len(chunks) >= 2:
        title = chunks[0]
        org_bits = [b.strip() for b in chunks[1].split(",") if b.strip()]
        org, loc = org_bits[0], org_bits[1:] + chunks[2:]
    else:
        bits = [b.strip() for b in line.split(",") if b.strip()] or [line]
        title, org, loc = bits[0], (bits[1] if len(bits) > 1 else ""), bits[2:]
    return {"title": title, "org": org, "location": ", ".join(loc),
            "dates": dates, "current": cur, "y0": y0, "y1": y1}


# --------------------------------------------------------------------------- bullets
_GERUNDS = {
    "building": "Built", "developing": "Developed", "designing": "Designed", "maintaining": "Maintained",
    "managing": "Managed", "creating": "Created", "writing": "Wrote", "testing": "Tested",
    "implementing": "Implemented", "running": "Ran", "leading": "Led", "migrating": "Migrated",
    "deploying": "Deployed", "automating": "Automated", "analyzing": "Analyzed", "improving": "Improved",
    "coordinating": "Coordinated", "supporting": "Supported", "monitoring": "Monitored",
    "teaching": "Taught", "training": "Trained", "handling": "Handled", "reviewing": "Reviewed",
}
_WEAK_OPENERS = [
    (r"^(i\s+was\s+|was\s+)?responsible\s+for\s+(" + "|".join(_GERUNDS) + r")\s+",
     lambda m: _GERUNDS[m.group(2).lower()] + " "),
    (r"^(i\s+was\s+|was\s+)?responsible\s+for\s+", "Owned "),
    (r"^(i\s+|we\s+)?worked\s+on\s+", "Contributed to "),
    (r"^(i\s+|we\s+)?helped\s+(with\s+|to\s+)?", "Contributed to "),
    (r"^(i\s+|we\s+)?assisted\s+(with\s+|in\s+)?", "Supported "),
    (r"^(i\s+|we\s+)?(was|were)\s+part\s+of\s+", "Contributed to "),
    (r"^(i\s+|we\s+)?participated\s+in\s+", "Took part in "),
    (r"^duties\s+included\s+", "Handled "),
    (r"^tasked\s+with\s+(" + "|".join(_GERUNDS) + r")\s+", lambda m: _GERUNDS[m.group(1).lower()] + " "),
    (r"^(i|we)\s+made\s+", "Built "),
    (r"^(i|we)\s+", ""),
]
_PAST_TO_BASE = {v: k for k, v in kb.PAST_TENSE.items()}


def _first_word(t: str) -> str:
    return t.split(" ", 1)[0].lower().strip(",.;:")


def _rewrite(text: str, current: bool, flags: list[dict]) -> tuple[str, list[str]]:
    changes: list[str] = []
    t = re.sub(r"^[\s\-*•]+", "", text).strip().rstrip(".").strip()
    for pat, rep in _WEAK_OPENERS:
        new = re.sub(pat, rep, t, count=1, flags=re.I)
        if new != t:
            changes.append("opener")
            t = new
            break
    for pat, rep, rule, why in kb.WEAK_PHRASES:
        if re.search(pat, t, re.I):
            if rep is None:
                flags.append({"rule": rule, "text": t, "why": why})
            else:
                t = re.sub(pat, rep, t, flags=re.I).replace("  ", " ")
                changes.append(rule)
    if re.search(kb.PRONOUNS, t[1:] if t else t):
        flags.append({"rule": "no-pronouns", "text": t, "why": "first-person pronoun inside the bullet"})
    # tense
    w = _first_word(t)
    rest = t[len(w):]
    if not current and w in kb.PAST_TENSE:
        t = kb.PAST_TENSE[w].capitalize() + rest
        changes.append("tense")
    elif current and w in _PAST_TO_BASE:
        t = kb.present_tense(_PAST_TO_BASE[w]).capitalize() + rest
        changes.append("tense")
    if t:
        t = t[0].upper() + t[1:]
    return t, changes


def _vary_openers(blocks: list[dict]) -> int:
    """Swap the 2nd+ use of an opening verb for an unused same-meaning synonym."""
    seen: Counter = Counter()
    swaps = 0
    all_first = Counter(_first_word(b["text"]) for blk in blocks for b in blk["bullets"])
    for blk in blocks:
        for b in blk["bullets"]:
            w = _first_word(b["text"])
            seen[w] += 1
            if seen[w] < 2:
                continue
            group = next((g for g in kb.SYNONYMS if w in g), None)
            if not group:
                continue
            alt = next((s for s in sorted(group) if s != w and all_first[s] == 0), None)
            if alt:
                b["text"] = alt.capitalize() + b["text"][len(w):]
                b["changes"].append("variety")
                all_first[alt] += 1
                swaps += 1
    return swaps


def _parse_blocks(text: str, kind: str) -> list[dict]:
    blocks: list[dict] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^[\-*•]", line):
            if not blocks:
                blocks.append({**_split_header("", kind), "bullets_raw": []})
            blocks[-1]["bullets_raw"].append(line)
        else:
            blocks.append({**_split_header(line, kind), "bullets_raw": []})
    return blocks


# --------------------------------------------------------------------------- level
def infer_level(profile: dict, exp_blocks: list[dict]) -> str:
    role = (profile.get("role") or "").lower()
    if re.search(r"senior|staff|principal|lead|manager|director|head of", role):
        return "senior"
    years = 0.0
    for b in exp_blocks:
        if b.get("y0") and not re.search(r"intern|assistant|ta\b|tutor", b["title"], re.I):
            years += max(0, (b.get("y1") or b["y0"]) - b["y0"]) or 0.5
    if re.search(r"student|graduate|grad\b|intern|entry|junior|fresher", role) and years < 2:
        return "student"
    if years >= 10:
        return "senior"
    return "early" if years >= 1.5 else "student"


def _education(text: str) -> list[dict]:
    out = []
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-•* ")
        if not line:
            continue
        h = _split_header(line)
        degree, school = h["title"], h["org"]
        if re.search(r"university|college|institute|school|iit|nit", degree, re.I) and school:
            degree, school = school, degree
        out.append({"degree": degree, "school": school, "location": h["location"], "dates": h["dates"],
                    "raw": line})
    return out


# --------------------------------------------------------------------------- build
def build_resume(profile: dict, job: dict | None, job_kw: list[str], emphasis: dict | None = None) -> dict:
    emphasis = emphasis or {}
    role = (profile.get("role") or "Software Engineer").strip()
    name = (profile.get("name") or "").strip()
    skills = [s.strip() for s in profile.get("skills") or [] if s.strip()]
    flags: list[dict] = []
    tally = Counter()

    exp = _parse_blocks(profile.get("experience", ""), "experience")
    proj = _parse_blocks(profile.get("projects", ""), "projects")
    level = infer_level(profile, exp)
    spec = kb.LEVELS[level]
    family = kb.role_family(f"{job['title'] if job else ''} {role}")

    # bullet caps: level budget, optionally nudged by an emphasis hint (0-1)
    exp_cap = max(2, min(6, spec["max_bullets"] - 1 + round(2 * emphasis.get("emphasize_experience", 0.5))))
    proj_cap = max(1, min(4, 1 + round(2 * emphasis.get("emphasize_projects", 0.5))))

    def finish(blocks, cap):
        out = []
        for b in blocks:
            bullets = []
            for raw in b["bullets_raw"]:
                text, ch = _rewrite(raw, b["current"], flags)
                if not text:
                    continue
                tally.update(ch)
                hits = [k for k in job_kw if has_term(text.lower(), k.lower())]
                q = is_quantified(text)
                bullets.append({"text": text, "keywords": hits, "quantified": q,
                                "strong_verb": _first_word(text) in kb.ALL_VERBS, "changes": ch,
                                "words": len(text.split()),
                                "_rank": 3 * len(hits) + 2 * q + (_first_word(text) in kb.ALL_VERBS)})
            bullets.sort(key=lambda x: -x["_rank"])
            for x in bullets:
                x.pop("_rank")
            out.append({k: v for k, v in b.items() if k not in ("bullets_raw",)} |
                       {"bullets": bullets[:cap], "trimmed": max(0, len(bullets) - cap),
                        "relevance": sum(len(x["keywords"]) for x in bullets)})
        return out

    experience = finish(exp, exp_cap)
    projects = finish(proj, proj_cap)
    # experience stays reverse-chronological; projects by relevance
    experience.sort(key=lambda b: -(b.get("y1") or b.get("y0") or 0))
    projects.sort(key=lambda b: -b["relevance"])
    tally["variety"] += _vary_openers(experience + projects)
    education = _education(profile.get("education", ""))

    # skills: grouped, listing keywords first within each group
    kw_lower = {k.lower() for k in job_kw}
    matched = {s for s in skills if s.lower() in kw_lower or any(has_term(s.lower(), k) for k in kw_lower)}
    groups: dict[str, list[dict]] = {}
    for s in sorted(skills, key=lambda s: (s not in matched)):
        groups.setdefault(kb.skill_group(s), []).append({"name": s, "matched": s in matched})
    group_order = ["Languages", "Frameworks", "Data & ML", "Cloud & DevOps", "Tools", "Other"]
    skill_groups = [{"group": g, "items": groups[g]} for g in group_order if g in groups]

    # section order: level guideline; the emphasis hint breaks the projects/experience tie for students
    order = list(spec["order"])
    if level == "student" and (not experience or emphasis.get("emphasize_projects", 0) > emphasis.get("emphasize_experience", 0)):
        order = ["education", "projects", "experience", "skills"]
    order = [s for s in order if {"experience": experience, "projects": projects,
                                  "education": education, "skills": skill_groups}[s]]

    # summary (only where the level guideline calls for one; facts from the user only)
    summary = ""
    if spec["summary"]:
        years = sum(max(0, (b.get("y1") or 0) - (b.get("y0") or 0)) for b in experience)
        top = [s["name"] for g in skill_groups for s in g["items"]][:3]
        best = max((b for blk in experience + projects for b in blk["bullets"] if b["quantified"]),
                   key=lambda b: len(b["keywords"]), default=None)
        summary = f"{role}" + (f" with {years}+ years" if years >= 2 else "") + \
                  (f" building with {', '.join(top[:-1])} and {top[-1]}" if len(top) > 1 else "")
        if best:
            summary += "; " + best["text"][0].lower() + best["text"][1:]
        summary += "."

    contact = {"email": profile.get("email", ""), "phone": profile.get("phone", ""),
               "location": profile.get("location", ""),
               "links": [l.strip() for l in re.split(r"[,\s]+", profile.get("links", "")) if l.strip()]}

    resume = {
        "name": name, "role": role, "contact": contact, "level": level, "family": family,
        "summary": summary, "education": education, "experience": experience, "projects": projects,
        "skills": skill_groups, "order": order, "page_budget": spec["pages"],
        "emphasis": {k: round(v, 3) for k, v in emphasis.items()},
    }
    resume["raw_text"] = to_text(resume)
    resume["lint"] = lint(resume, job_kw, flags)

    # tailoring notes
    all_bullets = [b for blk in experience + projects for b in blk["bullets"]]
    changes = []
    if matched and job:
        changes.append(f"put {len(matched)} skill(s) the listing asks for first in their group")
    for key, label in [("opener", "rewrote weak openers into action verbs"), ("tense", "fixed verb tense"),
                       ("variety", "swapped repeated opening verbs for synonyms"),
                       ("concise", "cut filler words"), ("specific", "removed vague words")]:
        if tally[key]:
            changes.append(f"{label} ({tally[key]})")
    changes.append(f"layout for {level} level — {spec['why']}")
    trimmed = sum(b["trimmed"] for b in experience + projects)
    if trimmed:
        changes.append(f"kept the strongest bullets per role; {trimmed} weaker one(s) left out")
    blob = " ".join([role, " ".join(skills), profile.get("experience", ""), profile.get("projects", ""),
                     profile.get("education", "")]).lower()
    gaps = [k for k in job_kw if not has_term(blob, k.lower())][:8]
    fam_gaps = [k for k in kb.ROLE_FAMILIES[family]["keywords"] if not has_term(blob, k)][:6]
    suggestions = [f"add a measurable result to “{b['text'][:80]}{'…' if len(b['text']) > 80 else ''}”"
                   for b in all_bullets if not b["quantified"]][:3]
    if gaps:
        suggestions.append("the listing asks for " + ", ".join(gaps[:5]) +
                           " — add a bullet only if you've genuinely used them")
    if fam_gaps:
        suggestions.append(f"{family} resumes usually show " + ", ".join(fam_gaps[:4]))
    resume["tailoring"] = {
        "target_job": {"title": job["title"], "company": job.get("company", "")} if job else None,
        "keywords": job_kw, "changes": changes, "gaps": gaps, "suggestions": suggestions,
    }
    return resume


# --------------------------------------------------------------------------- lint
def lint(r: dict, job_kw: list[str], flags: list[dict]) -> list[dict]:
    bullets = [b for blk in r["experience"] + r["projects"] for b in blk["bullets"]]
    out = []

    def add(rid, ok, detail, items=None, warn=False):
        title, why = kb.GUIDELINES[rid]
        out.append({"id": rid, "title": title, "why": why, "detail": detail, "items": items or [],
                    "status": "pass" if ok else ("warn" if warn else "fail")})

    c = r["contact"]
    have = [k for k in ("email", "phone") if c.get(k)] + (["links"] if c.get("links") else [])
    add("contact", bool(c.get("email")) and len(have) >= 2, f"has {', '.join(have) or 'nothing'}",
        warn=bool(c.get("email")))
    add("headings", True, "standard headings only")
    add("single-column", True, "single-column LaTeX layout, no tables or icons")
    if bullets:
        vf = [b for b in bullets if not b["strong_verb"]]
        add("verb-first", not vf, f"{len(bullets) - len(vf)}/{len(bullets)} start with an action verb",
            [b["text"] for b in vf], warn=len(vf) <= 1)
        firsts = Counter(_first_word(b["text"]) for b in bullets)
        rep = [f"{w} ×{n}" for w, n in firsts.items() if n >= 3]
        add("verb-variety", not rep, "no opener used 3+ times" if not rep else "repeated: " + ", ".join(rep))
        q = [b for b in bullets if not b["quantified"]]
        ratio = 1 - len(q) / len(bullets)
        add("quantified", ratio >= 0.6, f"{len(bullets) - len(q)}/{len(bullets)} bullets have a number",
            [b["text"] for b in q], warn=ratio >= 0.34)
        long_ = [b for b in bullets if b["words"] > 28]
        short = [b for b in bullets if b["words"] < 6]
        add("concise", not long_ and not short,
            "all bullets 6–28 words" if not (long_ or short) else f"{len(long_)} too long, {len(short)} too short",
            [b["text"] for b in long_ + short], warn=True)
    by_rule: dict[str, list[str]] = {}
    for f in flags:
        by_rule.setdefault(f["rule"], []).append(f"{f['why']}: “{f['text'][:70]}”")
    for rid in ("no-pronouns", "specific", "show-dont-tell", "confidence", "ownership"):
        items = by_rule.get(rid, [])
        add(rid, not items, "none found" if not items else f"{len(items)} to fix", items, warn=True)
    add("tense", True, "past tense for finished roles, present for current ones (auto-fixed)")
    dated = [b for b in r["experience"] if b["title"]]
    undated = [b["title"] for b in dated if not b["dates"]]
    add("dates", not undated, "all roles dated, one format" if not undated else "missing dates", undated, warn=True)
    add("skills-grouped", True, " / ".join(g["group"] for g in r["skills"]) or "no skills listed")
    if job_kw:
        text = r["raw_text"].lower()
        hit = [k for k in job_kw if has_term(text, k.lower())]
        add("keywords", len(hit) / len(job_kw) >= 0.4, f"{len(hit)}/{len(job_kw)} listing keywords present",
            [k for k in job_kw if k not in hit], warn=len(hit) / len(job_kw) >= 0.2)
    return out


# --------------------------------------------------------------------------- text
def to_text(r: dict) -> str:
    c = r["contact"]
    lines = [r["name"] or r["role"]]
    lines.append(" | ".join(x for x in [c.get("phone"), c.get("email"), c.get("location"), *c.get("links", [])] if x))
    if r["summary"]:
        lines += ["", "SUMMARY", r["summary"]]
    for sec in r["order"]:
        if sec == "education":
            lines += ["", "EDUCATION"]
            for e in r["education"]:
                lines.append(" | ".join(x for x in [e["school"], e["degree"], e["dates"]] if x))
        elif sec == "skills":
            lines += ["", "TECHNICAL SKILLS"] + [f"{g['group']}: {', '.join(i['name'] for i in g['items'])}"
                                                   for g in r["skills"]]
        else:
            lines += ["", sec.upper()]
            for b in r[sec]:
                head = " | ".join(x for x in [b["title"], b["org"], b["location"], b["dates"]] if x)
                if head:
                    lines.append(head)
                lines += [f"- {x['text']}" for x in b["bullets"]]
    return "\n".join(lines)
