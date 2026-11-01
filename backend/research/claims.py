"""Claim verifier: which claims in a rewrite does the original resume not support?

Pipeline (methodology section "Claim verifier"):
  1. split   -- document -> lines -> units (bullets / sentences)
  2. extract -- typed atomic claims per unit:
        skill       a known skill term (vocab + taxonomy + the target job's keywords)
        metric      a number, %, money amount or multiplier (dates excluded)
        role_scope  ownership verbs (led, managed ...) and seniority titles
        credential  degrees and certifications
        content     the unit as a whole -- catches new sentences that carry
                    no checkable token but are still not grounded
  3. support -- deterministic checks against the original first; the content
     check uses lexical containment, with an optional `judge` (e.g. an NLI
     model or LLM) for units in the uncertain band.
  4. validate -- see labelling.py (hand labels, kappa, precision/recall/F1).

Everything is plain, readable rules so each verdict comes with a reason a
person can check. Thresholds are module constants, to be calibrated on the
hand-labelled set before the main run.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterable

from app import resume_kb as kb
from app.text_rules import _term_re, has_term
from app.vocab import DEGREE_TERMS, SKILL_TERMS

CLAIM_TYPES = ("skill", "metric", "role_scope", "credential", "content")

# Containment of a unit's content words in the original resume. Below LOW the
# unit is new content; at/above HIGH it is grounded; in between a judge decides
# when one is given, else the midpoint rule applies.
CONTENT_LOW, CONTENT_HIGH = 0.35, 0.65
MIN_CONTENT_WORDS = 4

# General (non-tech) skills: the Kaggle set spans 24 fields, not just IT.
GENERAL_SKILLS = [
    "project management", "customer service", "sales", "marketing", "digital marketing", "seo",
    "budgeting", "forecasting", "payroll", "recruiting", "recruitment", "onboarding", "negotiation",
    "accounting", "bookkeeping", "auditing", "financial analysis", "financial modeling", "quickbooks",
    "sap", "salesforce", "crm", "hubspot", "photoshop", "illustrator", "indesign", "autocad",
    "solidworks", "six sigma", "lean", "inventory management", "supply chain", "logistics",
    "procurement", "risk management", "compliance", "contract management", "public speaking",
    "copywriting", "social media", "content strategy", "event planning", "patient care", "cpr",
    "first aid", "teaching", "curriculum development", "lesson planning", "data entry",
    "microsoft office", "word", "powerpoint", "outlook", "excel", "tableau", "power bi",
]
SKILL_SYNONYMS = {
    "js": "javascript", "node": "node.js", "nodejs": "node.js", "k8s": "kubernetes",
    "postgres": "postgresql", "golang": "go", "ml": "machine learning", "nextjs": "next.js",
    "reactjs": "react", "react.js": "react", "ms excel": "excel", "microsoft excel": "excel",
    "google cloud": "gcp", "amazon web services": "aws", "ms office": "microsoft office",
    "recruiting": "recruitment",
}

OWNERSHIP = {"led", "lead", "leading", "leads", "managed", "manage", "manages", "managing", "owned",
             "own", "owns", "spearheaded", "directed", "headed", "oversaw", "oversee", "supervised",
             "supervise", "architected", "drove", "championed", "orchestrated"}
LIMITING = {"assisted", "assist", "assisting", "helped", "help", "helping", "supported", "contributed",
            "participated", "shadowed", "observed", "learned", "learning", "familiar", "exposure",
            "basic", "prototype", "trainee", "coursework", "academic", "involved"}
TITLES = {"senior", "lead", "principal", "staff", "manager", "director", "head", "chief", "vp",
          "supervisor", "architect"}
CREDENTIALS = ["bachelor", "master", "mba", "phd", "doctorate", "b.tech", "m.tech", "b.sc", "m.sc",
               "b.e", "m.e", "associate degree", "diploma", "pmp", "cpa", "cfa", "ccna", "cissp",
               "scrum master", "six sigma green belt", "six sigma black belt", "aws certified",
               "certified", "certification", "certificate", "licensed", "license"]

_CRED_TERMS = sorted(set(CREDENTIALS) | set(DEGREE_TERMS)
                     - {"university", "college", "gpa", "coursework", "computer science", "mathematics",
                        "physics", "software engineering", "electrical engineering", "information technology",
                        "data science degree", "statistics degree", "bootcamp"},
                     key=len, reverse=True)

STOP = set("""a an the and or of to in on for with by at from as into via per is are was were be been
being this that these those it its their our my your his her them they we i you he she over under
than then also such using use used including include includes across within while both each
other more most very new all any""".split())

_DATE_RE = re.compile(r"^(?:19|20)\d{2}$")
_NUM_RE = re.compile(
    r"(?<![\w.])(\$|₹|€|£)?\s?(\d[\d,]*(?:\.\d+)?)\s?(%|percent|\+|x\b|k\b|m\b|mm\b|million|billion|lakh|crore)?",
    re.I)


@dataclass
class Claim:
    type: str
    text: str            # the claimed token or phrase
    unit: str            # the sentence/bullet it sits in
    unit_index: int
    supported: bool
    reason: str
    evidence: str = ""   # best-matching original sentence, for reviewers


@dataclass
class Report:
    units: list[str]
    claims: list[Claim] = field(default_factory=list)
    # unit index -> (closest original sentence, Jaccard similarity); used by strip()
    evidence: dict[int, tuple[str, float]] = field(default_factory=dict)

    @property
    def unsupported(self) -> list[Claim]:
        return [c for c in self.claims if not c.supported]

    def counts(self) -> dict[str, int]:
        out = {t: 0 for t in CLAIM_TYPES}
        for c in self.unsupported:
            out[c.type] += 1
        return out

    def unsupported_units(self, types: Iterable[str] | None = None) -> set[int]:
        keep = set(types) if types is not None else set(CLAIM_TYPES)
        return {c.unit_index for c in self.unsupported if c.type in keep}


# --------------------------------------------------------------------------- splitting
_SENT_SPLIT = re.compile(r"(?<=[.!?;])\s+(?=[A-Z(])|\s{3,}|\s+[•▪●]\s+")


def split_lines(text: str) -> list[list[str]]:
    """Document -> lines -> units. Keeps line structure so stripping can rebuild text."""
    out = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            out.append([])
            continue
        parts = [p.strip() for p in _SENT_SPLIT.split(line) if p and p.strip()]
        out.append(parts)
    return out


def units_of(text: str) -> list[str]:
    return [u for line in split_lines(text) for u in line]


def join_lines(lines: list[list[str]]) -> str:
    return "\n".join(" ".join(units) for units in lines).strip()


# --------------------------------------------------------------------------- tokens
def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def content_words(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z][a-z+#.]*[a-z+#]|[a-z]", text.lower())
            if len(w) > 2 and w not in STOP}


def containment(unit: str, against: set[str]) -> float:
    words = content_words(unit)
    return len(words & against) / len(words) if words else 1.0


def _best_match(unit: str, orig_units: list[str]) -> tuple[str, float]:
    words = content_words(unit)
    best, score = "", 0.0
    for o in orig_units:
        ow = content_words(o)
        if not words or not ow:
            continue
        s = len(words & ow) / len(words | ow)
        if s > score:
            best, score = o, s
    return best, score


def numbers_in(text: str) -> set[str]:
    """Normalised numeric claims; 4-digit years are dates, not metrics."""
    out = set()
    for cur, num, unit in _NUM_RE.findall(text):
        n = num.replace(",", "").rstrip(".")
        if not n or _DATE_RE.match(n):
            continue
        try:
            val = float(n)
        except ValueError:
            continue
        if val == int(val):
            n = str(int(val))
        u = (unit or "").lower().replace("percent", "%")
        out.add(f"{cur}{n}{u}")
    return out


def _bare(n: str) -> str:
    return re.sub(r"[^\d.]", "", n)


# --------------------------------------------------------------------------- skills
def skill_vocab(extra: Iterable[str] = ()) -> list[str]:
    terms = set(SKILL_TERMS) | set(GENERAL_SKILLS) | {s for ss in kb.SKILL_GROUPS.values() for s in ss}
    terms |= {t.lower().strip() for t in extra if t and 2 <= len(t.strip()) <= 30}
    terms -= {"c", "r", "go", "word", "lean", "sales"}  # too ambiguous as bare words in prose
    return sorted(terms, key=len, reverse=True)


def canonical(skill: str) -> str:
    s = skill.lower().strip()
    return SKILL_SYNONYMS.get(s, s)


def skills_in(text: str, vocab: list[str]) -> set[str]:
    t = text.lower()
    found = set()
    for term in vocab:                       # longest first, so "power bi" beats "bi"
        if has_term(t, term):
            found.add(canonical(term))
            # blank out the match so "bi" inside "power bi" is not counted again,
            # while a separate "SQL" next to "SQLite" (or Java next to JavaScript) still is
            t = _term_re(term.lower()).sub(" ", t)
    for alias, target in SKILL_SYNONYMS.items():
        if has_term(t, alias):
            found.add(target)
    return found


# --------------------------------------------------------------------------- verify
def _flat(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9+#%]+", text.lower()))


def verify(original: str, rewrite: str, job_terms: Iterable[str] = (),
           judge: Callable[[str, str], bool] | None = None) -> Report:
    """Type and check every claim in `rewrite` against `original`.

    `judge(unit, original) -> supported?` is consulted only for content
    claims whose containment falls between CONTENT_LOW and CONTENT_HIGH.
    """
    vocab = skill_vocab(job_terms)
    orig_l = original.lower()
    orig_units = units_of(original)
    orig_words = content_words(original)
    orig_nums = numbers_in(original)
    orig_bare = {_bare(n) for n in orig_nums}
    orig_skills = skills_in(original, vocab)
    orig_owner = {w for w in OWNERSHIP if has_term(orig_l, w)}

    orig_flat = _flat(original)
    units = units_of(rewrite)
    rep = Report(units=units)
    for i, unit in enumerate(units):
        ul = unit.lower()
        evidence, sim = _best_match(unit, orig_units)
        rep.evidence[i] = (evidence, sim)
        if _flat(unit) and _flat(unit) in orig_flat:
            continue                         # copied verbatim from the original: nothing new is claimed
        ev_l = evidence.lower()

        for s in sorted(skills_in(unit, vocab)):
            ok = s in orig_skills
            rep.claims.append(Claim("skill", s, unit, i, ok,
                                    "skill appears in original" if ok else "skill not in original", evidence))

        for n in sorted(numbers_in(unit)):
            ok = n in orig_nums or _bare(n) in orig_bare
            rep.claims.append(Claim("metric", n, unit, i, ok,
                                    "number appears in original" if ok else "number not in original", evidence))

        owners = sorted(w for w in OWNERSHIP if has_term(ul, w))
        for w in owners:
            limited = sorted(x for x in LIMITING if has_term(ev_l, x))
            if limited and sim >= 0.2:
                ok, why = False, f"inflated: original says '{limited[0]}'"
            elif any(has_term(ev_l, o) for o in OWNERSHIP) or (w in orig_owner and sim >= 0.2):
                ok, why = True, "ownership stated in original"
            else:
                ok, why = False, "ownership not stated in original"
            rep.claims.append(Claim("role_scope", w, unit, i, ok, why, evidence))
        for t in sorted(t for t in TITLES if has_term(ul, t)):
            if t in owners:
                continue
            ok = has_term(orig_l, t)
            rep.claims.append(Claim("role_scope", t, unit, i, ok,
                                    "title word in original" if ok else "seniority title not in original",
                                    evidence))

        seen_cred: list[str] = []
        for c in _CRED_TERMS:                # longest first: "aws certified" hides "certified"
            if has_term(ul, c) and not any(c in big for big in seen_cred):
                seen_cred.append(c)
                ok = has_term(orig_l, c)
                rep.claims.append(Claim("credential", c, unit, i, ok,
                                        "credential in original" if ok else "credential not in original",
                                        evidence))

        if len(content_words(unit)) >= MIN_CONTENT_WORDS:
            cont = containment(unit, orig_words)
            if cont >= CONTENT_HIGH:
                ok, why = True, f"grounded ({cont:.2f} of words in original)"
            elif cont < CONTENT_LOW:
                ok, why = False, f"new content ({cont:.2f} of words in original)"
            elif judge is not None:
                ok = bool(judge(unit, original))
                why = f"judge: {'supported' if ok else 'unsupported'} ({cont:.2f} overlap)"
            else:
                ok = cont >= (CONTENT_LOW + CONTENT_HIGH) / 2
                why = f"{'grounded' if ok else 'weakly grounded'} ({cont:.2f} of words in original)"
            rep.claims.append(Claim("content", unit[:80], unit, i, ok, why, evidence))
    return rep


# --------------------------------------------------------------------------- strip
def _is_list_unit(unit: str) -> bool:
    return unit.count(",") >= 2 or bool(re.match(r"^(technical\s+)?skills?\b", unit.strip(), re.I))


def _remove_item(unit: str, term: str) -> str:
    pat = re.compile(r"(?:,\s*)?(?<![a-z0-9+#])" + re.escape(term) + r"(?![a-z0-9+#])(?:\s*,)?", re.I)
    out = pat.sub(",", unit, count=1)
    out = re.sub(r",\s*,", ",", out)
    out = re.sub(r"(:\s*),", r"\1", out)
    return re.sub(r"\s*,\s*$", "", out).replace(" ,", ",").strip()


REVERT_MIN_SIM = 0.25   # a flagged line reverts to its closest original sentence only if this close


def strip(rewrite: str, report: Report, types: Iterable[str] | None = None) -> str:
    """Undo unsupported claims of `types` (default: all), adding nothing the original lacks.

    * a skill in a list-like unit ("Skills: a, b, c") loses just that item;
    * any other flagged unit is REVERTED to its closest original sentence when
      one is close enough (so the candidate's true content in a mixed line
      survives), and deleted otherwise -- also when that original sentence
      already appears elsewhere in the text.
    """
    keep = set(types) if types is not None else set(CLAIM_TYPES)
    flagged: set[int] = set()
    item_cuts: dict[int, list[str]] = {}
    for c in report.unsupported:
        if c.type not in keep:
            continue
        if c.type == "skill" and _is_list_unit(c.unit):
            item_cuts.setdefault(c.unit_index, []).append(c.text)
        elif c.type == "content" and _is_list_unit(c.unit):
            continue  # a skills list's words are judged item by item, not as prose
        else:
            flagged.add(c.unit_index)

    present = {u.strip() for i, u in enumerate(report.units) if i not in flagged}
    lines, idx = split_lines(rewrite), 0
    out: list[list[str]] = []
    for line in lines:
        kept = []
        for unit in line:
            if idx in flagged:
                orig, sim = report.evidence.get(idx, ("", 0.0))
                if orig and sim >= REVERT_MIN_SIM and orig.strip() not in present:
                    kept.append(orig)
                    present.add(orig.strip())
            else:
                for term in item_cuts.get(idx, []):
                    unit = _remove_item(unit, term)
                if unit.strip(" ,:-"):
                    kept.append(unit)
            idx += 1
        if kept or not line:
            out.append(kept)
    return join_lines(out)


def strip_fully(original: str, rewrite: str, job_terms: Iterable[str] = (),
                types: Iterable[str] | None = None, judge=None, passes: int = 3) -> str:
    """strip() until verify() finds nothing of `types` left. One pass is not always
    enough: rejoining edited lines can re-split sentences into new units."""
    types = list(types) if types is not None else None
    text = rewrite
    for _ in range(passes):
        rep = verify(original, text, job_terms, judge)
        if not rep.unsupported_units(types):
            break
        text = strip(text, rep, types)
    return text


def strip_random_supported(rewrite: str, report: Report, k: int, rng) -> str:
    """Length-matched control: delete k units that hold NO unsupported claim."""
    bad = report.unsupported_units()
    candidates = [i for i in range(len(report.units)) if i not in bad]
    chosen = set(rng.sample(candidates, min(k, len(candidates)))) if k > 0 else set()
    lines, idx, out = split_lines(rewrite), 0, []
    for line in lines:
        kept = []
        for unit in line:
            if idx not in chosen:
                kept.append(unit)
            idx += 1
        if kept or not line:
            out.append(kept)
    return join_lines(out)
