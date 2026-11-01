"""Benchmark data: resumes, job descriptions, and resume-job pairs.

Resumes come from the public Kaggle Resume Dataset (snehaanbhawal/resume-dataset,
2,400+ livecareer.com resumes, 24 categories; columns ID, Resume_str,
Resume_html, Category). Jobs come from a dated snapshot built by fetch_jobs.py.

Each resume is paired with two jobs: one in its own category ("matched") and
one in a different category ("changer", the career-changer subgroup).
"""
from __future__ import annotations

import csv
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

CATEGORIES = [
    "HR", "DESIGNER", "INFORMATION-TECHNOLOGY", "TEACHER", "ADVOCATE", "BUSINESS-DEVELOPMENT",
    "HEALTHCARE", "FITNESS", "AGRICULTURE", "BPO", "SALES", "CONSULTANT", "DIGITAL-MEDIA",
    "AUTOMOBILE", "CHEF", "FINANCE", "APPAREL", "ENGINEERING", "ACCOUNTANT", "CONSTRUCTION",
    "PUBLIC-RELATIONS", "BANKING", "ARTS", "AVIATION",
]

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")


def clean_resume(text: str) -> str:
    """Remove contact details; turn the dataset's runs of spaces into line breaks."""
    text = _EMAIL.sub(" ", text or "")
    text = _PHONE.sub(" ", text)
    text = text.replace("\t", " ").replace("\r", "")
    text = re.sub(r" {3,}", "\n", text)
    text = re.sub(r"[  ]{2}", " ", text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def load_resumes(path: str | Path, n: int | None = None, seed: int = 0,
                 min_words: int = 120, max_words: int | None = None) -> list[dict]:
    """Stratified sample: round-robin across categories so each is equally represented.
    `max_words` drops very long resumes so resume + job + rewrite fit the model's context."""
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    by_cat: dict[str, list[dict]] = defaultdict(list)
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            text = clean_resume(row.get("Resume_str", ""))
            words = len(text.split())
            if words < min_words or (max_words and words > max_words):
                continue
            cat = (row.get("Category") or "").strip().upper()
            by_cat[cat].append({"id": str(row.get("ID")), "category": cat, "text": text})
    rng = random.Random(seed)
    for rows in by_cat.values():
        rng.shuffle(rows)
    out, cats = [], sorted(by_cat)
    i = 0
    while (n is None or len(out) < n) and any(by_cat[c] for c in cats):
        c = cats[i % len(cats)]
        if by_cat[c]:
            out.append(by_cat[c].pop())
        i += 1
    return out


def load_jobs(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    jobs = data["jobs"] if isinstance(data, dict) else data
    for j in jobs:
        j["category"] = j.get("category", "").upper()
        j["id"] = str(j["id"])
    return jobs


def make_pairs(resumes: list[dict], jobs: list[dict], seed: int = 0) -> list[dict]:
    """Two pairs per resume: same-category job and different-category job.
    A resume whose category has no job gets only the changer pair."""
    rng = random.Random(seed)
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for j in jobs:
        by_cat[j["category"]].append(j)
    pairs = []
    for r in resumes:
        same = by_cat.get(r["category"], [])
        other = [j for j in jobs if j["category"] != r["category"]]
        if same:
            j = rng.choice(same)
            pairs.append({"pair_id": f"{r['id']}|{j['id']}", "group": "matched", "resume": r, "job": j})
        if other:
            j = rng.choice(other)
            pairs.append({"pair_id": f"{r['id']}|{j['id']}", "group": "changer", "resume": r, "job": j})
    return pairs
