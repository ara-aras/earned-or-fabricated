"""Run the experiment: every resume-job pair -> every version -> every screener.

    # smoke run, no model needed (bundled sample data + FakeLLM)
    python -m research.run_experiment --sample --rewriter fake --screener fake --out research/results/smoke.jsonl

    # real run: local Ollama rewriter, a different model family as LLM screener
    python -m research.run_experiment --resumes research/data/Resume.csv \
        --jobs research/data/jobs_snapshot.json --n 500 --samples 3 \
        --rewriter qwen3.5-4b-8k --screener gemma3-4b-8k --out research/results/main.jsonl

Writes one JSON line per (pair, sample). Pairs already in --out are skipped,
so an interrupted run continues where it stopped; with the LLM cache, a
rerun reproduces every number.
"""
from __future__ import annotations

import argparse
import json
import random
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.text_rules import job_keywords
from research import claims as cl
from research import rewriters as rw
from research import screeners as sc
from research.data import load_jobs, load_resumes, make_pairs
from research.llm import make_llm

HERE = Path(__file__).parent
SAMPLE_DIR = HERE / "sample_data"


def run_pair(pair: dict, sample: int, rewriter, screener, screener_runs: int,
             do_guarded: bool, ablate_llm: bool) -> dict:
    resume, job = pair["resume"]["text"], pair["job"]
    job_kw = job_keywords(job)
    terms = job_kw + list(job.get("tags") or [])

    texts = {"orig": resume}
    texts["llm"] = rw.llm_rewrite(rewriter, resume, job, seed=sample)
    rep = cl.verify(resume, texts["llm"], terms)
    texts["stripped"] = cl.strip_fully(resume, texts["llm"], terms)
    texts["rule"] = rw.rule_rewrite(resume)
    k = len(cl.units_of(texts["llm"])) - len(cl.units_of(texts["stripped"]))
    rng = random.Random(zlib.crc32(f"{pair['pair_id']}|{sample}".encode()))
    texts["control"] = cl.strip_random_supported(texts["llm"], rep, k, rng)
    rounds = 0
    if do_guarded:
        texts["guarded"], rounds = rw.guarded_rewrite(rewriter, resume, job, terms, seed=sample,
                                                       first_draft=texts["llm"])
    ablations = {f"minus_{t}": cl.strip_fully(resume, texts["llm"], terms, [t])
                 for t in cl.CLAIM_TYPES if rep.counts()[t] > 0}

    counts = {"llm": rep.counts()}
    for v in ("stripped", "rule", "guarded"):
        if v in texts:
            counts[v] = cl.verify(resume, texts[v], terms).counts()

    scores: dict[str, dict[str, float | None]] = {"ats": {}}
    for v, t in {**texts, **ablations}.items():
        scores["ats"][v] = sc.ats_score(t, job, job_kw)
    if screener is not None:
        scores["llm"] = {}
        for v, t in {**texts, **(ablations if ablate_llm else {})}.items():
            scores["llm"][v] = sc.llm_score(screener, t, job, runs=screener_runs)

    return {
        "pair_id": pair["pair_id"], "sample": sample, "group": pair["group"],
        "refusal": rw.is_refusal(texts["llm"]),
        "resume_id": pair["resume"]["id"], "resume_category": pair["resume"]["category"],
        "job_id": job["id"], "job_category": job["category"], "job_title": job.get("title", ""),
        "job_terms": terms,
        "unsupported_counts": counts, "units_removed": k, "guarded_rounds": rounds,
        "unsupported_claims": [{"type": c.type, "text": c.text, "reason": c.reason}
                               for c in rep.unsupported],
        "scores": scores, "texts": texts,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resumes", help="Kaggle Resume.csv")
    ap.add_argument("--jobs", help="job snapshot JSON from fetch_jobs.py")
    ap.add_argument("--sample", action="store_true", help="use the bundled sample_data instead")
    ap.add_argument("--n", type=int, default=500, help="resumes to sample (stratified by category)")
    ap.add_argument("--max-words", type=int, default=1500,
                    help="skip longer resumes (98 of 2,482 Kaggle resumes) so prompts fit an 8k context")
    ap.add_argument("--samples", type=int, default=1, help="LLM rewrites per pair")
    ap.add_argument("--rewriter", default="qwen3.5-4b-8k", help="'fake', 'model' or 'model@base_url'")
    ap.add_argument("--screener", default="none", help="LLM screener spec, or 'none' for ATS only")
    ap.add_argument("--screener-runs", type=int, default=1)
    ap.add_argument("--no-guarded", action="store_true")
    ap.add_argument("--no-llm-ablation", action="store_true",
                    help="score per-type ablations with the ATS only (saves LLM calls)")
    ap.add_argument("--limit-pairs", type=int)
    ap.add_argument("--workers", type=int, default=1, help="parallel pairs (useful with hosted APIs)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cache", default=str(HERE / "cache"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.sample:
        resumes = load_resumes(SAMPLE_DIR / "resumes.csv", n=args.n, seed=args.seed, min_words=40)
        jobs = load_jobs(SAMPLE_DIR / "jobs.json")
    else:
        if not (args.resumes and args.jobs):
            ap.error("--resumes and --jobs are required unless --sample is given")
        resumes = load_resumes(args.resumes, n=args.n, seed=args.seed, max_words=args.max_words)
        jobs = load_jobs(args.jobs)
    pairs = make_pairs(resumes, jobs, seed=args.seed)[: args.limit_pairs]

    cache = Path(args.cache)
    rewriter = make_llm(args.rewriter, cache / "llm")
    screener = None if args.screener == "none" else make_llm(args.screener, cache / "llm")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["pair_id"], r["sample"]))
    (out.with_suffix(".config.json")).write_text(json.dumps(vars(args) | {
        "n_resumes": len(resumes), "n_jobs": len(jobs), "n_pairs": len(pairs),
        "started": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1), encoding="utf-8")

    todo = [(p, s) for p in pairs for s in range(args.samples) if (p["pair_id"], s) not in done]
    print(f"{len(resumes)} resumes, {len(jobs)} jobs, {len(pairs)} pairs x {args.samples} samples; "
          f"{len(done)} done, {len(todo)} to run")
    lock, t0, finished = threading.Lock(), time.time(), 0

    def work(item):
        p, s = item
        return run_pair(p, s, rewriter, screener, args.screener_runs,
                        not args.no_guarded, not args.no_llm_ablation)

    with open(out, "a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(work, it): it for it in todo}
        for fut in as_completed(futs):
            p, s = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:  # one bad pair must not kill a multi-hour run
                print(f"  ! {p['pair_id']} sample {s}: {type(exc).__name__}: {exc}")
                continue
            with lock:
                f.write(json.dumps(rec) + "\n")
                f.flush()
                finished += 1
                if finished % 10 == 0 or finished == len(todo):
                    rate = (time.time() - t0) / finished
                    print(f"  {finished}/{len(todo)}  ~{rate * (len(todo) - finished) / 60:.0f} min left")
    print(f"results -> {out}")


if __name__ == "__main__":
    main()
