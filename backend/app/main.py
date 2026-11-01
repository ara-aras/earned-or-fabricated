"""FastAPI app for AI Resume: Earned vs Fabricated Advantage.

The web front of the research in research/: one resume and one job in, an
audit of an LLM rewrite out -- which claims the original supports, how much
of the ATS gain they earn, and a guarded rewrite that keeps only that part.

  /api/health          backend up, which rewriter model the audit uses
  /api/jobs            the dated job snapshot the experiment runs on
  /api/audit           earned-vs-fabricated audit of an LLM rewrite
  /api/audit/example   a sample resume + job for the demo
  /api/demo/cases      the five ready-made demo cases (demo/cases.json)

The rewriter is a local LLM (Ollama by default; see research/README.md),
set with AUDIT_LLM.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.text_rules import strip_html
from research.audit import audit
from research.data import load_jobs, load_resumes
from research.llm import make_llm

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "research"
AUDIT_LLM = os.environ.get("AUDIT_LLM", "qwen3.5-4b-8k")

app = FastAPI(title="AI Resume: Earned vs Fabricated Advantage")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Job(BaseModel):
    id: str = ""
    title: str
    company: str = ""
    tags: list[str] = []
    url: str = ""
    description: str = ""
    source: str = ""
    category: str = ""


class AuditRequest(BaseModel):
    resume_text: str
    job: Job
    rewrite_text: str = ""     # paste a ChatGPT/Gemini rewrite to audit it; empty = generate one
    guarded: bool = True


_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = make_llm(AUDIT_LLM, RESEARCH / "cache" / "llm")
    return _llm


@app.get("/api/health")
def health():
    return {"ok": True, "rewriter": AUDIT_LLM}


@app.get("/api/jobs")
def jobs():
    path = RESEARCH / "data" / "jobs_snapshot.json"
    # Plain text for the form; the audit strips HTML too, so scores are the same either way.
    return {"jobs": [j | {"description": strip_html(j.get("description", ""))} for j in load_jobs(path)]}


@app.post("/api/audit")
def audit_rewrite(req: AuditRequest):
    if not req.resume_text.strip():
        raise HTTPException(status_code=400, detail="resume_text is empty")
    if not (req.job.title.strip() or req.job.description.strip()):
        raise HTTPException(status_code=400, detail="the job needs a title or a description")
    pasted = req.rewrite_text.strip() or None
    llm = _get_llm() if (pasted is None or req.guarded) else None
    try:
        return audit(req.resume_text, req.job.model_dump(), rewrite=pasted, llm=llm, guarded=req.guarded)
    except RuntimeError as exc:   # model server down or model missing
        raise HTTPException(status_code=503, detail=(
            f"Could not reach the rewriter model ({AUDIT_LLM}). Start Ollama and create the model "
            f"(see backend/research/README.md), or paste a rewrite and untick the guarded rewrite. {exc}"))


@app.get("/api/demo/cases")
def demo_cases():
    # demo/cases.json: ready-made original + job + rewrite triples for the live demo and the game
    path = ROOT.parent / "demo" / "cases.json"
    if not path.exists():
        return {"cases": []}
    return {"cases": json.loads(path.read_text(encoding="utf-8"))}


@app.get("/api/audit/example")
def audit_example():
    sample = RESEARCH / "sample_data"
    resume = load_resumes(sample / "resumes.csv", min_words=40)[0]
    job = next(j for j in load_jobs(sample / "jobs.json") if j["category"] == resume["category"])
    return {"resume_text": resume["text"], "job": job}
