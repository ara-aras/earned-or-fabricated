"""Shared, fully interpretable text helpers (NOT neural, NOT trained).

Keyword extraction, term matching and resume parsing used by the job scout,
resume builder, ATS screen and interviewer. Kept deliberately plain so every
score in the UI can be traced back to a readable rule.
"""
from __future__ import annotations

import html
import re
from functools import lru_cache

from app.vocab import ACTION_VERBS, FILLER_WORDS, SKILL_TERMS

SENIORITY_LEVELS = {
    "intern": 0, "internship": 0, "junior": 1, "entry": 1, "graduate": 1, "associate": 1,
    "mid": 2, "senior": 3, "sr": 3, "lead": 4, "staff": 4, "principal": 5,
    "manager": 4, "head": 5, "director": 5, "vp": 6,
}

# Generic RemoteOK tags that say nothing about required skills.
_GENERIC_TAGS = {
    "dev", "developer", "engineer", "engineering", "digital nomad", "remote", "admin",
    "exec", "technical", "support", "customer support", "non tech", "senior", "junior",
    "lead", "teaching", "sales", "marketing", "recruiter", "design", "full time",
    "mobile", "web", "software", "code", "back end", "front end", "full stack",
    "ecommerce", "finance", "health", "saas", "video", "consulting", "operations",
}

_MQ = re.compile(
    r"\b\d+(\.\d+)?\s*(%|percent|x\b|k\b|m\b|b\b|million|billion|thousand|"
    r"ms\b|seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?|times|"
    r"users|customers|clients|students|people|members|engineers|teams?|requests|queries|tickets|"
    r"pages|services|endpoints|servers|models|tests|bugs|features|downloads|stars|gb\b|tb\b|mb\b)"
    r"|\$\s?\d|\b\d{2,}\b|\b\d+\+", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


@lru_cache(maxsize=512)
def _term_re(term: str) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9+#])" + re.escape(term.lower()) + r"(?![a-z0-9+#])")


def has_term(text_lower: str, term: str) -> bool:
    return bool(_term_re(term.lower()).search(text_lower))


def find_skills(text: str) -> list[str]:
    t = text.lower()
    return [s for s in SKILL_TERMS if has_term(t, s)]


def is_quantified(text: str) -> bool:
    return bool(_MQ.search(text))


def starts_with_action_verb(text: str) -> bool:
    first = re.sub(r"^[\s\-*•]+", "", text).split(" ", 1)[0].lower().strip(",.")
    return first in ACTION_VERBS or first.endswith("ed") and len(first) > 4


def filler_hits(text: str) -> list[str]:
    t = text.lower()
    return [f for f in FILLER_WORDS if f in t]


def seniority_of(title: str) -> int | None:
    t = title.lower()
    best = None
    for word, lvl in SENIORITY_LEVELS.items():
        if has_term(t, word):
            best = lvl if best is None else max(best, lvl)
    return best


def job_keywords(job: dict) -> list[str]:
    """Skills this listing asks for: known skill terms found anywhere in the
    title/tags/description, plus any specific (non-generic) tags."""
    desc = strip_html(job.get("description", ""))
    tags = [str(t).lower().strip() for t in (job.get("tags") or [])]
    blob = f"{job.get('title', '')} {' '.join(tags)} {desc}"
    found = find_skills(blob)
    for tag in tags:
        if 2 <= len(tag) <= 24 and tag not in _GENERIC_TAGS and tag not in found:
            found.append(tag)
    return found[:18]


def contact_info(text: str) -> dict:
    return {"email": bool(_EMAIL.search(text)), "phone": bool(_PHONE.search(text))}


SECTION_ALIASES = {
    "summary": ["summary", "profile", "objective", "about"],
    "skills": ["skills", "technical skills", "technologies", "tech stack"],
    "experience": ["experience", "work experience", "employment", "professional experience"],
    "projects": ["projects", "personal projects", "selected projects"],
    "education": ["education", "academics"],
}


def parse_sections(text: str) -> dict[str, list[str]]:
    """Split plain-text resume into sections by heading lines."""
    sections: dict[str, list[str]] = {"_header": []}
    current = "_header"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key = line.lower().rstrip(":").strip()
        matched = next((s for s, al in SECTION_ALIASES.items() if key in al), None)
        if matched and len(line) < 40:
            current = matched
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def bullets_of(lines: list[str]) -> list[str]:
    return [re.sub(r"^[\-*•]\s*", "", l) for l in lines if re.match(r"^[\-*•]", l)]
