# Demo dataset

Five ready-made cases for showing the audit live. Each case has three files to paste
into the web app:

| File | Paste into |
| --- | --- |
| `original.txt` | **Your original resume** |
| `job.txt` | **Job title** (first line) and **Job description** (the rest) |
| `rewrite.txt` | **Already rewrote it with ChatGPT…?** (open the section first) |

Untick **Also write a guarded rewrite** for an instant result (no model call). Leave
it ticked to also show the guarded rewrite. That needs Ollama running and takes
30–90 seconds per case.

The people, companies and contact details are made up. Each rewrite is written the
way ChatGPT-style tools typically tailor a resume.

## Cases

| Case | What it shows | Original | Rewrite | Fabricated share |
| --- | --- | --- | --- | --- |
| `01-fresher-skill-stuffing` | Final-year student gets React, Docker, AWS, Kubernetes and a made-up 40% speed-up | 54.7 | 89.5 | 97% |
| `02-honest-rewrite` | **Control.** Same student, rewritten honestly: no flags, the whole gain is earned | 54.7 | 57.4 | 0% |
| `03-marketing-inflated-role` | Executive becomes someone who "led" and "headed" campaigns, with invented follower and revenue numbers | 40.7 | 69.6 | 98% |
| `04-mechanical-credentials` | Gains a Six Sigma Green Belt, a PMP and an M.Tech the candidate never earned | 48.2 | 58.7 | 83% |
| `05-data-analyst-mixed` | A bit of everything: new tools, a "led" project, a 30% saving and a Google certificate | 53.3 | 86.7 | 104% |

Over 100% means the rewrite with its unsupported claims removed scores *below* the
original. The page explains this when it happens.

**Suggested demo order:** 01, then 02 (same person, honest version), then 04 or 05.
Case 01 against 02 makes the point: +35 points from invention against +3 earned.

## Regenerating

`cases.json` is the source. With the backend running on port 8420:

```bash
python demo/run_demo.py
```

This rewrites the files under `cases/` and audits every case. It prints the table and
saves it to `results.md`.
