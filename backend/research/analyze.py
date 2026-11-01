"""Turn experiment JSONL into the numbers the report needs.

    python -m research.analyze research/results/main.jsonl

Writes <name>.report.md and <name>.summary.json next to the input.

Unit of analysis = resume-job pair (LLM samples of one pair are averaged
first), so bootstrap resamples and paired tests never treat repeated samples
of the same pair as independent evidence.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from scipy import stats

from research.claims import CLAIM_TYPES

MIN_GAIN = 2.0          # per-pair ratios only where the LLM gain is at least this many points
BOOT = 1000
VERSIONS = ("orig", "llm", "stripped", "rule", "guarded", "control")


# --------------------------------------------------------------------------- loading
def load(path: str | Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def per_pair(records: list[dict], screener: str) -> list[dict]:
    """Average each score and claim count over a pair's samples."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if screener in r["scores"]:
            groups[r["pair_id"]].append(r)
    rows = []
    for pid, rs in groups.items():
        row = {"pair_id": pid, "group": rs[0]["group"], "n_samples": len(rs)}
        keys = set().union(*(r["scores"][screener].keys() for r in rs))
        for k in keys:
            vals = [r["scores"][screener].get(k) for r in rs]
            vals = [v for v in vals if v is not None]
            row[k] = mean(vals) if vals else None
        for v in ("llm", "stripped", "rule", "guarded"):
            cs = [sum(r["unsupported_counts"][v].values()) for r in rs if v in r["unsupported_counts"]]
            row[f"fab_{v}"] = mean(cs) if cs else None
        for t in CLAIM_TYPES:
            row[f"n_{t}"] = mean(r["unsupported_counts"]["llm"][t] for r in rs)
        rows.append(row)
    return [r for r in rows if all(r.get(v) is not None for v in ("orig", "llm", "stripped"))]


# --------------------------------------------------------------------------- measures
def pooled_share(rows: list[dict], num=("llm", "stripped"), den=("llm", "orig")) -> float | None:
    d = sum(r[den[0]] - r[den[1]] for r in rows)
    if abs(d) < 1e-9:
        return None
    return sum(r[num[0]] - r[num[1]] for r in rows) / d


def bootstrap_ci(rows: list[dict], fn, b: int = BOOT, seed: int = 0) -> tuple[float, float] | None:
    if len(rows) < 2:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(b):
        v = fn([rows[rng.randrange(len(rows))] for _ in rows])
        if v is not None:
            vals.append(v)
    if len(vals) < b * 0.5:
        return None
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def pair_share(r: dict) -> float | None:
    gain = r["llm"] - r["orig"]
    return (r["llm"] - r["stripped"]) / gain if gain >= MIN_GAIN else None


def _wilcoxon(a: list[float], b: list[float]) -> dict:
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 5 or all(abs(x - y) < 1e-12 for x, y in pairs):
        return {"n": len(pairs), "p": None, "note": "too few non-tied pairs"}
    res = stats.wilcoxon([x for x, _ in pairs], [y for _, y in pairs])
    return {"n": len(pairs), "statistic": float(res.statistic), "p": float(res.pvalue),
            "median_diff": median(x - y for x, y in pairs)}


def _holm(pvals: dict[str, float]) -> dict[str, float]:
    order = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(order), {}, 0.0
    for i, (k, p) in enumerate(order):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


# --------------------------------------------------------------------------- research questions
def rq1(rows: list[dict]) -> dict:
    share = pooled_share(rows)
    per = [s for s in (pair_share(r) for r in rows) if s is not None]
    by_group = {}
    for g in ("matched", "changer"):
        gr = [r for r in rows if r["group"] == g]
        by_group[g] = {"pairs": len(gr), "pooled_share": pooled_share(gr),
                       "ci95": bootstrap_ci(gr, pooled_share),
                       "per_pair": [s for s in (pair_share(r) for r in gr) if s is not None]}
    a, b = by_group["matched"]["per_pair"], by_group["changer"]["per_pair"]
    mw = (lambda res: {"U": float(res.statistic), "p": float(res.pvalue)})(stats.mannwhitneyu(a, b)) \
        if len(a) >= 3 and len(b) >= 3 else {"p": None, "note": "too few pairs with gain >= MIN_GAIN"}
    for g in by_group.values():
        g["median_per_pair"] = median(g["per_pair"]) if g["per_pair"] else None
        g["n_per_pair"] = len(g.pop("per_pair"))
    ctl = [r for r in rows if r.get("control") is not None]
    return {
        "pairs": len(rows),
        "mean_gain_llm": mean(r["llm"] - r["orig"] for r in rows),
        "mean_gain_stripped": mean(r["stripped"] - r["orig"] for r in rows),
        "pooled_fabricated_share": share,
        "ci95": bootstrap_ci(rows, pooled_share),
        "median_per_pair_share": median(per) if per else None,
        "pairs_with_gain_ge_min": len(per),
        "subgroups": by_group, "matched_vs_changer": mw,
        "length_control": {
            "mean_drop_fabrication_removed": mean(r["llm"] - r["stripped"] for r in ctl) if ctl else None,
            "mean_drop_supported_removed": mean(r["llm"] - r["control"] for r in ctl) if ctl else None,
            "wilcoxon": _wilcoxon([r["llm"] - r["stripped"] for r in ctl], [r["llm"] - r["control"] for r in ctl]),
        },
    }


def rq2(rows: list[dict]) -> dict:
    per_type, drops = {}, {}
    for t in CLAIM_TYPES:
        key = f"minus_{t}"
        vals = [(r["llm"] - r[key]) / r[f"n_{t}"] for r in rows
                if r.get(key) is not None and r[f"n_{t}"] > 0]
        drops[t] = {r["pair_id"]: (r["llm"] - r[key]) / r[f"n_{t}"] for r in rows
                    if r.get(key) is not None and r[f"n_{t}"] > 0}
        per_type[t] = {"pairs": len(vals), "mean_drop_per_claim": mean(vals) if vals else None,
                       "mean_claims_per_resume": mean(r[f"n_{t}"] for r in rows)}
    present = [t for t in CLAIM_TYPES if len(drops[t]) >= 5]
    blocks = set.intersection(*(set(drops[t]) for t in present)) if len(present) >= 3 else set()
    test: dict = {"types_compared": present}
    if len(blocks) >= 5:
        res = stats.friedmanchisquare(*[[drops[t][b] for b in sorted(blocks)] for t in present])
        test |= {"test": "friedman", "blocks": len(blocks), "statistic": float(res.statistic), "p": float(res.pvalue)}
        raw = {f"{x} vs {y}": _wilcoxon([drops[x][b] for b in sorted(blocks)],
                                        [drops[y][b] for b in sorted(blocks)])["p"]
               for x, y in itertools.combinations(present, 2)}
    elif len(present) >= 2:
        res = stats.kruskal(*[list(drops[t].values()) for t in present])
        test |= {"test": "kruskal (too few pairs carry every type for Friedman)",
                 "statistic": float(res.statistic), "p": float(res.pvalue)}
        raw = {f"{x} vs {y}": float(stats.mannwhitneyu(list(drops[x].values()), list(drops[y].values())).pvalue)
               for x, y in itertools.combinations(present, 2)}
    else:
        test["test"], raw = "none (fewer than 2 claim types with 5+ pairs)", {}
    test["posthoc_holm"] = _holm({k: v for k, v in raw.items() if v is not None})
    return {"per_type": per_type, "test": test}


def rq3(rows: list[dict]) -> dict:
    g = [r for r in rows if r.get("guarded") is not None and r.get("fab_guarded") is not None]
    if not g:
        return {"note": "no guarded runs"}
    rate = {v: {"mean_unsupported_per_resume": mean(r[f"fab_{v}"] for r in g),
                "pct_resumes_with_any": 100 * mean(1.0 if r[f"fab_{v}"] > 0 else 0.0 for r in g)}
            for v in ("llm", "guarded", "rule", "stripped")}

    def kept(rs):
        return pooled_share(rs, num=("guarded", "orig"), den=("stripped", "orig"))
    return {
        "pairs": len(g), "fabrication": rate,
        "earned_gain_kept": kept(g), "earned_gain_kept_ci95": bootstrap_ci(g, kept),
        "guarded_vs_llm_fabrication": _wilcoxon([r["fab_guarded"] for r in g], [r["fab_llm"] for r in g]),
        "guarded_vs_stripped_score": _wilcoxon([r["guarded"] for r in g], [r["stripped"] for r in g]),
        "guarded_vs_rule_score": _wilcoxon([r["guarded"] for r in g], [r["rule"] for r in g]),
        "mean_scores": {v: mean(r[v] for r in g) for v in VERSIONS if all(r.get(v) is not None for r in g)},
    }


# --------------------------------------------------------------------------- report
def _f(x, pct=False, nd=2):
    if x is None:
        return "n/a"
    return f"{100 * x:.1f}%" if pct else f"{x:.{nd}f}"


def _ci(ci, pct=False):
    return "n/a" if not ci else f"{_f(ci[0], pct)} to {_f(ci[1], pct)}"


def _p(d):
    return "n/a" if d.get("p") is None else f"{d['p']:.4f}"


def render(summary: dict) -> str:
    out = [f"# Results: {summary['source']}", "",
           f"{summary['records']} records, {summary['screeners']} screener(s). "
           f"Per-pair ratios use pairs with an LLM gain of at least {MIN_GAIN} points.", "",
           f"Refusals (the rewriter returned an assessment instead of a resume): "
           f"{summary.get('refusals', 0)} of {summary['records'] + summary.get('refusals', 0)} records, "
           "excluded from every table below.", ""]
    for name, s in summary["by_screener"].items():
        r1, r2, r3 = s["rq1"], s["rq2"], s["rq3"]
        out += [f"## Screener: {name}", "", "### RQ1: how much of the advantage is fabricated?", "",
                "| Measure | Value |", "| --- | --- |",
                f"| Pairs | {r1['pairs']} |",
                f"| Mean gain, LLM rewrite vs original | {_f(r1['mean_gain_llm'])} points |",
                f"| Mean gain, stripped vs original (earned) | {_f(r1['mean_gain_stripped'])} points |",
                f"| **Fabricated share (pooled)** | **{_f(r1['pooled_fabricated_share'], True)}** "
                f"(95% CI {_ci(r1['ci95'], True)}) |",
                f"| Median per-pair share | {_f(r1['median_per_pair_share'], True)} "
                f"({r1['pairs_with_gain_ge_min']} pairs) |", ""]
        out += ["| Subgroup | Pairs | Pooled share | 95% CI | Median per pair |", "| --- | --- | --- | --- | --- |"]
        for g, d in r1["subgroups"].items():
            out.append(f"| {g} | {d['pairs']} | {_f(d['pooled_share'], True)} | {_ci(d['ci95'], True)} | "
                       f"{_f(d['median_per_pair'], True)} |")
        lc = r1["length_control"]
        out += ["", f"Matched vs career-changer (Mann-Whitney U): p = {_p(r1['matched_vs_changer'])}.", "",
                f"Length control: removing fabrications drops the score by {_f(lc['mean_drop_fabrication_removed'])} "
                f"points; removing the same number of supported lines drops it by "
                f"{_f(lc['mean_drop_supported_removed'])} (Wilcoxon p = {_p(lc['wilcoxon'])}).", "",
                "### RQ2: which fabrications pay?", "",
                "| Claim type | Pairs | Unsupported per resume | Score drop per claim |", "| --- | --- | --- | --- |"]
        for t, d in sorted(r2["per_type"].items(), key=lambda kv: -(kv[1]["mean_drop_per_claim"] or -1e9)):
            out.append(f"| {t} | {d['pairs']} | {_f(d['mean_claims_per_resume'])} | {_f(d['mean_drop_per_claim'])} |")
        tst = r2["test"]
        out += ["", f"Test: {tst['test']}" + (f", p = {tst['p']:.4f}" if tst.get("p") is not None else "") + ".", ""]
        if tst.get("posthoc_holm"):
            out += ["| Comparison | Holm-adjusted p |", "| --- | --- |"] + \
                   [f"| {k} | {v:.4f} |" for k, v in tst["posthoc_holm"].items()] + [""]
        out += ["### RQ3: can the earned part be kept?", ""]
        if "note" in r3:
            out += [r3["note"], ""]
            continue
        out += ["| Version | Unsupported claims per resume | Resumes with any |", "| --- | --- | --- |"]
        for v, d in r3["fabrication"].items():
            out.append(f"| {v} | {_f(d['mean_unsupported_per_resume'])} | {_f(d['pct_resumes_with_any'] / 100, True)} |")
        out += ["", f"Earned gain kept by the guarded rewriter: **{_f(r3['earned_gain_kept'], True)}** "
                    f"(95% CI {_ci(r3['earned_gain_kept_ci95'], True)}).", "",
                f"- Guarded vs unguarded, unsupported claims: Wilcoxon p = {_p(r3['guarded_vs_llm_fabrication'])}",
                f"- Guarded vs stripped, score: Wilcoxon p = {_p(r3['guarded_vs_stripped_score'])}",
                f"- Guarded vs rule-based, score: Wilcoxon p = {_p(r3['guarded_vs_rule_score'])}", "",
                "Mean scores: " + ", ".join(f"{k} {_f(v)}" for k, v in r3["mean_scores"].items()) + ".", ""]
    return "\n".join(out)


def analyze(path: str | Path) -> dict:
    from research.rewriters import is_refusal
    all_records = load(path)
    records = [r for r in all_records if not (r.get("refusal") or is_refusal(r["texts"]["llm"]))]
    screeners = sorted({s for r in records for s in r["scores"]})
    summary = {"source": Path(path).name, "records": len(records), "screeners": len(screeners),
               "refusals": len(all_records) - len(records), "by_screener": {}}
    for s in screeners:
        rows = per_pair(records, s)
        if rows:
            summary["by_screener"][s] = {"rq1": rq1(rows), "rq2": rq2(rows), "rq3": rq3(rows)}
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    args = ap.parse_args()
    summary = analyze(args.results)
    p = Path(args.results)
    p.with_suffix(".summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    p.with_suffix(".report.md").write_text(render(summary), encoding="utf-8")
    print(render(summary))


if __name__ == "__main__":
    main()
