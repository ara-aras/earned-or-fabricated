"""Validate the claim verifier against human labels (methodology "Claim verifier", step 4).

1) Export a labelling sheet from a results file:
       python -m research.labelling export research/results/main.jsonl --n 100 --out research/labels/

   Samples claims stratified by the verifier's verdict (half flagged, half
   not) so both precision and recall get enough examples, and records a
   sampling weight per row so the metrics stay unbiased. Writes sheet.csv
   plus originals/<row>.txt with the full original resume for each row.

2) Label. Easiest: the local labelling page, which shows the claim, the
   rewritten line and the full original side by side and saves into sheet.csv:
       python -m research.labelling serve research/labels/sheet.csv
   (or edit sheet.csv by hand). Fill `label_a` with "supported" / "unsupported"
   (S / U also accepted) without looking at the `verifier` column. With a
   second labeller, they fill `label_b` independently and disagreements are
   settled in `label_final`. One labeller is enough for precision / recall;
   Cohen's kappa needs two.

3) Score it:
       python -m research.labelling evaluate research/labels/sheet.csv
   -> Cohen's kappa between labellers, and the verifier's precision, recall
   and F1 for "unsupported" (weighted by the sampling weights).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

from research import claims as cl

FIELDS = ["row_id", "pair_id", "sample", "type", "claim", "rewritten_line", "closest_original_line",
          "verifier", "verifier_reason", "weight", "label_a", "label_b", "label_final", "notes"]


def _norm(label: str) -> str | None:
    s = (label or "").strip().lower()
    if s in ("s", "supported", "yes", "y", "1"):
        return "supported"
    if s in ("u", "unsupported", "no", "n", "0", "fabricated"):
        return "unsupported"
    return None


def export(results: str, n: int, out_dir: str, seed: int = 0) -> Path:
    records = [json.loads(l) for l in Path(results).read_text(encoding="utf-8").splitlines() if l.strip()]
    from research.rewriters import is_refusal
    pool = []
    for r in records:
        if is_refusal(r["texts"]["llm"]):  # not a resume: nothing to validate
            continue
        rep = cl.verify(r["texts"]["orig"], r["texts"]["llm"], r.get("job_terms", []))
        for c in rep.claims:
            pool.append((r, c))
    rng = random.Random(seed)
    strata = {True: [x for x in pool if x[1].supported], False: [x for x in pool if not x[1].supported]}
    picked = []
    for ok, items in strata.items():
        k = min(len(items), n // 2 + (n % 2 if not ok else 0))
        for item in rng.sample(items, k):
            picked.append((item, len(items) / k))
    rng.shuffle(picked)

    out = Path(out_dir)
    (out / "originals").mkdir(parents=True, exist_ok=True)
    with open(out / "sheet.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, ((r, c), weight) in enumerate(picked, 1):
            (out / "originals" / f"{i:04d}.txt").write_text(r["texts"]["orig"], encoding="utf-8")
            w.writerow({"row_id": f"{i:04d}", "pair_id": r["pair_id"], "sample": r["sample"], "type": c.type,
                        "claim": c.text, "rewritten_line": c.unit, "closest_original_line": c.evidence,
                        "verifier": "supported" if c.supported else "unsupported",
                        "verifier_reason": c.reason, "weight": f"{weight:.4f}"})
    return out / "sheet.csv"


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    if not a:
        return None
    labels = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / len(a)
    pe = sum((a.count(l) / len(a)) * (b.count(l) / len(b)) for l in labels)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def evaluate(sheet: str) -> dict:
    with open(sheet, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    both = [(_norm(r["label_a"]), _norm(r["label_b"])) for r in rows]
    both = [(x, y) for x, y in both if x and y]
    kappa = cohen_kappa([x for x, _ in both], [y for _, y in both])

    tp = fp = fn = tn = 0.0
    used, disagreements = 0, 0
    by_type: dict[str, list[float]] = {}
    for r in rows:
        a, b, final = _norm(r["label_a"]), _norm(r["label_b"]), _norm(r["label_final"])
        gold = final or (a if a and (a == b or not b) else None) or (b if b and not a else None)
        if a and b and a != b and not final:
            disagreements += 1
        if not gold:
            continue
        used += 1
        wt = float(r.get("weight") or 1)
        pred_u, gold_u = r["verifier"] == "unsupported", gold == "unsupported"
        tp += wt * (pred_u and gold_u)
        fp += wt * (pred_u and not gold_u)
        fn += wt * (not pred_u and gold_u)
        tn += wt * (not pred_u and not gold_u)
        by_type.setdefault(r["type"], []).append(1.0 if pred_u == gold_u else 0.0)
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else None
    return {"rows": len(rows), "rows_with_gold": used, "unresolved_disagreements": disagreements,
            "cohen_kappa": kappa, "precision_unsupported": prec, "recall_unsupported": rec, "f1": f1,
            "accuracy_by_type": {t: sum(v) / len(v) for t, v in by_type.items()}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("results")
    e.add_argument("--n", type=int, default=100)
    e.add_argument("--out", default="research/labels")
    e.add_argument("--seed", type=int, default=0)
    v = sub.add_parser("evaluate")
    v.add_argument("sheet")
    s = sub.add_parser("serve", help="local labelling page that saves into the sheet")
    s.add_argument("sheet")
    s.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    if args.cmd == "export":
        print(f"labelling sheet -> {export(args.results, args.n, args.out, args.seed)}")
    elif args.cmd == "serve":
        from research.label_server import serve
        serve(args.sheet, args.port)
    else:
        print(json.dumps(evaluate(args.sheet), indent=1))


if __name__ == "__main__":
    main()
