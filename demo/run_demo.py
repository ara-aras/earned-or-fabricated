"""Split cases.json into paste-ready text files and audit each case against the
running backend (uvicorn on port 8420).

    python demo/run_demo.py            # write files + audit (pasted rewrite, no LLM)
    python demo/run_demo.py --files    # only write the text files
"""
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
API = "http://localhost:8420/api/audit"
TYPES = ["skill", "metric", "role_scope", "credential", "content"]


def write_files(cases):
    for c in cases:
        d = HERE / "cases" / c["id"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "original.txt").write_text(c["original"] + "\n", encoding="utf-8")
        (d / "rewrite.txt").write_text(c["rewrite"] + "\n", encoding="utf-8")
        j = c["job"]
        (d / "job.txt").write_text(f"{j['title']}, {j['company']}\n\n{j['description']}\n", encoding="utf-8")


def audit(c):
    body = {"resume_text": c["original"], "rewrite_text": c["rewrite"], "guarded": False,
            "job": {"title": c["job"]["title"], "company": c["job"]["company"],
                    "description": c["job"]["description"]}}
    req = urllib.request.Request(API, json.dumps(body).encode(), {"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main():
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    write_files(cases)
    if "--files" in sys.argv:
        return
    rows = ["| Case | Original | Rewrite | Stripped | Fabricated share | " + " | ".join(TYPES) + " |",
            "| --- " * (5 + len(TYPES)) + "|"]
    for c in cases:
        r = audit(c)
        s = r["scores"]
        share = "n/a" if r["fabricated_share"] is None else f"{max(0, round(r['fabricated_share'] * 100))}%"
        rows.append(f"| {c['id']} | {s['orig']} | {s['llm']} | {s['stripped']} | {share} | "
                    + " | ".join(str(r["counts"][t]) for t in TYPES) + " |")
    table = "\n".join(rows)
    print(table)
    (HERE / "results.md").write_text(table + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
