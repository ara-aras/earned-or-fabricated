"""Read-only job fetching from several PUBLIC job-board APIs, in parallel.

Why several: any single free feed is flaky (RemoteOK alone timed out in
practice). Every source gets its own short timeout; whatever answers in time
is merged, de-duplicated and ranked against the profile. A dead source is
reported, never fatal.

LinkedIn / Glassdoor / Indeed / Naukri have no public job-search API and
their terms forbid scraping, so this module never fetches them. Instead
`search_links()` builds ready-made search URLs the user opens themselves,
and the frontend lets them paste any listing they find there as a target.
Nothing here ever applies or submits anything.
"""
from __future__ import annotations

import ast
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

import httpx

USER_AGENT = "Mozilla/5.0 (compatible; ai-resume-research/1.0)"
TIMEOUT = httpx.Timeout(7.0, connect=4.0)


def _listish(v) -> list[str]:
    """Some APIs return lists, some return stringified python lists."""
    if isinstance(v, list):
        return [str(x.get("name", x)) if isinstance(x, dict) else str(x) for x in v]
    if isinstance(v, str) and v.startswith("["):
        try:
            return _listish(ast.literal_eval(v))
        except Exception:
            return []
    return [v] if isinstance(v, str) and v else []


def _get(client: httpx.Client, url: str):
    r = client.get(url)
    r.raise_for_status()
    return r.json()


# ---- one function per source: (client, query, skill) -> list[normalized job]

def _remoteok(c, q, skill):
    data = _get(c, "https://remoteok.com/api")
    out = []
    for e in data[1:]:
        if isinstance(e, dict) and e.get("position"):
            out.append(dict(id=e.get("id"), title=e["position"], company=e.get("company", ""),
                            tags=_listish(e.get("tags")), url=e.get("url") or e.get("apply_url", ""),
                            description=e.get("description", ""), location=e.get("location", "Remote"),
                            salary=_salary(e.get("salary_min"), e.get("salary_max")), posted=e.get("date", "")))
    return out


def _remotive(c, q, skill):
    d = _get(c, f"https://remotive.com/api/remote-jobs?search={quote_plus(skill or q)}&limit=40")
    return [dict(id=e["id"], title=e["title"], company=e.get("company_name", ""),
                 tags=_listish(e.get("tags")), url=e.get("url", ""), description=e.get("description", ""),
                 location=e.get("candidate_required_location", "Remote"), salary=e.get("salary", ""),
                 posted=e.get("publication_date", "")) for e in d.get("jobs", [])]


def _himalayas(c, q, skill):
    d = _get(c, f"https://himalayas.app/jobs/api/search?q={quote_plus(q)}&limit=40")
    return [dict(id=e.get("guid"), title=e["title"], company=e.get("companyName", ""),
                 tags=[t.replace("-", " ") for t in _listish(e.get("categories"))][:8],
                 url=e.get("applicationLink") or e.get("guid", ""), description=e.get("description", ""),
                 location=", ".join(_listish(e.get("locationRestrictions"))[:3]) or "Remote",
                 salary=_salary(e.get("minSalary"), e.get("maxSalary")), posted=str(e.get("pubDate", "")))
            for e in d.get("jobs", [])]


def _jobicy(c, q, skill):
    d = _get(c, f"https://jobicy.com/api/v2/remote-jobs?count=40&tag={quote_plus(skill or q)}")
    return [dict(id=e["id"], title=e.get("jobTitle", ""), company=e.get("companyName", ""),
                 tags=_listish(e.get("jobIndustry")) + _listish(e.get("jobType")), url=e.get("url", ""),
                 description=e.get("jobDescription") or e.get("jobExcerpt", ""),
                 location=e.get("jobGeo", "Remote"), salary="", posted=e.get("pubDate", ""))
            for e in d.get("jobs", [])]


def _arbeitnow(c, q, skill):
    d = _get(c, "https://www.arbeitnow.com/api/job-board-api")
    return [dict(id=e["slug"], title=e["title"], company=e.get("company_name", ""),
                 tags=_listish(e.get("tags")), url=e.get("url", ""), description=e.get("description", ""),
                 location=("Remote · " if e.get("remote") else "") + e.get("location", ""), salary="",
                 posted=str(e.get("created_at", ""))) for e in d.get("data", [])]


def _themuse(c, q, skill):
    level = "Entry%20Level" if re.search(r"graduate|student|junior|intern|entry", q, re.I) else "Mid%20Level"
    d = _get(c, f"https://www.themuse.com/api/public/jobs?page=0&category=Software%20Engineering&level={level}")
    return [dict(id=e["id"], title=e.get("name", ""), company=(e.get("company") or {}).get("name", ""),
                 tags=_listish(e.get("categories")) + _listish(e.get("levels")),
                 url=(e.get("refs") or {}).get("landing_page", ""), description=e.get("contents", ""),
                 location=", ".join(_listish(e.get("locations"))[:2]), salary="",
                 posted=e.get("publication_date", "")) for e in d.get("results", [])]


SOURCES = {
    "RemoteOK": _remoteok,
    "Remotive": _remotive,
    "Himalayas": _himalayas,
    "Jobicy": _jobicy,
    "Arbeitnow": _arbeitnow,
    "The Muse": _themuse,
}


def _salary(lo, hi) -> str:
    try:
        lo, hi = int(lo or 0), int(hi or 0)
    except (TypeError, ValueError):
        return ""
    if lo and hi:
        return f"${lo // 1000}k–${hi // 1000}k"
    return f"${(lo or hi) // 1000}k" if (lo or hi) else ""


def _score(job: dict, skills_lower: set[str], role_words: set[str], level: int | None = None) -> int:
    tags = [t.lower() for t in job["tags"]]
    text = f"{job['title']} {job['description'][:4000]}".lower()
    s = 0
    for sk in skills_lower:
        if sk in tags:
            s += 3
        elif re.search(r"(?<![a-z0-9+#])" + re.escape(sk) + r"(?![a-z0-9+#])", text):
            s += 1
    title = job["title"].lower()
    s += sum(2 for w in role_words if w in title)
    if level is not None:
        from app.text_rules import seniority_of
        jl = seniority_of(job["title"])
        if jl is not None:
            s -= 4 * max(0, abs(jl - level) - 1) + (3 if abs(jl - level) >= 2 else 0)  # a graduate shouldn't be shown Staff roles first
    return s


def fetch_jobs(role: str, skills: list[str], limit: int = 12) -> tuple[list[dict], list[dict]]:
    """Returns (jobs, source_status). Never raises."""
    q = role or (skills[0] if skills else "software engineer")
    skill = skills[0] if skills else ""
    status: list[dict] = []
    pool: list[dict] = []
    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        with ThreadPoolExecutor(max_workers=len(SOURCES)) as ex:
            futs = {ex.submit(fn, client, q, skill): name for name, fn in SOURCES.items()}
            try:
                for f in as_completed(futs, timeout=12):
                    name = futs[f]
                    try:
                        got = f.result()
                        for j in got:
                            j["source"] = name
                            j["id"] = f"{name}:{j['id']}"
                        pool += got
                        status.append({"source": name, "ok": True, "count": len(got)})
                    except Exception as exc:  # timeout, block, bad JSON...
                        status.append({"source": name, "ok": False, "error": type(exc).__name__})
            except TimeoutError:
                done = {s["source"] for s in status}
                status += [{"source": n, "ok": False, "error": "Timeout"} for n in SOURCES if n not in done]

    from app.text_rules import seniority_of
    level = seniority_of(q)
    level = 1 if level is None else level
    skills_lower = {s.lower() for s in skills}
    role_words = {w for w in re.findall(r"[a-z]+", q.lower()) if len(w) > 3}
    for j in pool:
        j["match"] = _score(j, skills_lower, role_words, level)
    seen, ranked, per_source = set(), [], {}
    for j in sorted(pool, key=lambda j: -j["match"]):
        key = (j["title"].strip().lower(), j["company"].strip().lower())
        if key in seen or not j["title"] or per_source.get(j["source"], 0) >= 4:
            continue
        seen.add(key)
        per_source[j["source"]] = per_source.get(j["source"], 0) + 1
        ranked.append(j)
        if len(ranked) >= limit:
            break
    return ranked, status


def search_links(role: str, skills: list[str], location: str = "") -> list[dict]:
    """Deep links into boards with no public API. Opened by the user, never fetched here."""
    kw = " ".join([role] + skills[:2]).strip()
    k, loc = quote_plus(kw), quote_plus(location or "")
    slug = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-") or "software-engineer"
    return [
        {"name": "LinkedIn", "url": f"https://www.linkedin.com/jobs/search/?keywords={k}&location={loc}"},
        {"name": "Glassdoor", "url": f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={k}"},
        {"name": "Indeed", "url": f"https://www.indeed.com/jobs?q={k}&l={loc}"},
        {"name": "Naukri", "url": f"https://www.naukri.com/{slug}-jobs"},
        {"name": "Wellfound", "url": f"https://wellfound.com/jobs?q={k}"},
        {"name": "Google Jobs", "url": f"https://www.google.com/search?q={k}+jobs&ibp=htl;jobs"},
    ]
