"""Build the dated job-description snapshot the experiment reads.

    python -m research.fetch_jobs --per-category 2 --out research/data/jobs_snapshot.json

Queries the project's public job APIs (app/jobs.py) once per Kaggle category.
Those feeds lean to tech and remote roles, so some categories (Chef,
Agriculture, Aviation ...) usually come back empty: the script lists them,
and you add public postings for them by hand to the same JSON file
(fields: id, title, company, description, tags, category, url).
Live listings change, so always run the experiment from the saved snapshot.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.jobs import fetch_jobs
from app.text_rules import strip_html
from research.data import CATEGORIES

QUERIES: dict[str, tuple[str, list[str]]] = {
    "HR": ("HR generalist", ["recruiting"]),
    "DESIGNER": ("graphic designer", ["figma"]),
    "INFORMATION-TECHNOLOGY": ("IT support engineer", ["linux"]),
    "TEACHER": ("teacher", ["curriculum"]),
    "ADVOCATE": ("legal counsel", ["contracts"]),
    "BUSINESS-DEVELOPMENT": ("business development manager", ["sales"]),
    "HEALTHCARE": ("registered nurse", ["patient care"]),
    "FITNESS": ("fitness coach", ["training"]),
    "AGRICULTURE": ("agriculture", ["agronomy"]),
    "BPO": ("customer support representative", ["customer service"]),
    "SALES": ("account executive", ["salesforce"]),
    "CONSULTANT": ("management consultant", ["strategy"]),
    "DIGITAL-MEDIA": ("digital media specialist", ["social media"]),
    "AUTOMOBILE": ("automotive engineer", ["automotive"]),
    "CHEF": ("chef", ["culinary"]),
    "FINANCE": ("financial analyst", ["excel"]),
    "APPAREL": ("fashion designer", ["apparel"]),
    "ENGINEERING": ("mechanical engineer", ["autocad"]),
    "ACCOUNTANT": ("staff accountant", ["accounting"]),
    "CONSTRUCTION": ("construction project manager", ["construction"]),
    "PUBLIC-RELATIONS": ("public relations manager", ["communications"]),
    "BANKING": ("banking analyst", ["banking"]),
    "ARTS": ("art director", ["design"]),
    "AVIATION": ("aviation", ["aircraft maintenance"]),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-category", type=int, default=2)
    ap.add_argument("--out", default="research/data/jobs_snapshot.json")
    args = ap.parse_args()

    jobs, empty = [], []
    for cat in CATEGORIES:
        role, skills = QUERIES[cat]
        found, _status = fetch_jobs(role, skills, limit=10)
        # The APIs return their best match even when it is unrelated (an "art director" query
        # can come back with sales roles), so keep only titles containing every query word.
        words = [w for w in role.lower().split() if len(w) >= 3]
        found = [j for j in found
                 if len(strip_html(j.get("description", "")).split()) >= 80
                 and all(w in j.get("title", "").lower() for w in words)]
        for j in found[: args.per_category]:
            jobs.append({k: j.get(k) for k in ("id", "title", "company", "description", "tags", "url", "source")}
                        | {"category": cat})
        print(f"{cat:24s} {len(found[: args.per_category])} job(s)")
        if not found:
            empty.append(cat)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"fetched_at": date.today().isoformat(), "jobs": jobs}, indent=1),
                   encoding="utf-8")
    print(f"\nsaved {len(jobs)} jobs -> {out}")
    if empty:
        print("no usable listings for: " + ", ".join(empty) + " -- add public postings by hand")


if __name__ == "__main__":
    main()
