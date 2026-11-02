"""Tests for the Earned vs Fabricated Advantage pipeline (research/)."""
from __future__ import annotations

import csv
import json

import pytest

from research import analyze, claims as cl, labelling, rewriters as rw
from research.data import load_jobs, load_resumes, make_pairs
from research.llm import FakeLLM
from research.run_experiment import SAMPLE_DIR, run_pair

ORIG = """Jane Doe
Skills: Python, SQL, Excel
Experience
- Assisted with migrating reporting dashboards to a new BI tool.
- Built ETL jobs in Python processing 2 million rows per day.
Education
B.Sc Computer Science, 2019"""

REWRITE = """Jane Doe
Skills: Python, SQL, Excel, Kubernetes, Tableau
Experience
- Led migration of reporting dashboards to a new BI tool, improving efficiency by 35%.
- Built ETL pipelines in Python processing 2 million rows per day.
- Managed a cross-functional team of 8 engineers delivering cloud migration.
Education
M.Sc Computer Science, AWS Certified"""


def _flagged(rep, type_):
    return {c.text for c in rep.unsupported if c.type == type_}


def test_numbers_skip_years_and_normalise():
    assert cl.numbers_in("Joined in 2019, cut cost by 1,000 dollars and 35%") == {"1000", "35%"}


def test_verify_catches_each_fabrication_type():
    rep = cl.verify(ORIG, REWRITE, job_terms=["kubernetes", "tableau"])
    assert {"kubernetes", "tableau"} <= _flagged(rep, "skill")
    assert {"35%", "8"} <= _flagged(rep, "metric")
    assert "led" in _flagged(rep, "role_scope")          # "assisted with" -> "led"
    assert "managed" in _flagged(rep, "role_scope")
    assert {"m.sc", "aws certified"} <= _flagged(rep, "credential")


def test_verify_accepts_honest_rewording():
    rep = cl.verify(ORIG, "- Built ETL pipelines in Python processing 2 million rows daily.")
    assert rep.unsupported == []


def test_verify_supports_existing_skill_synonym():
    rep = cl.verify("Skills: JavaScript, PostgreSQL", "Skills: JS, Postgres")
    assert _flagged(rep, "skill") == set()


def test_skill_next_to_longer_skill_still_counts():
    rep = cl.verify("Skills: Java, JavaScript, SQL, SQLite", "Skills: Java, SQL")
    assert _flagged(rep, "skill") == set()


def test_strip_reverts_mixed_line_and_cuts_list_items():
    rep = cl.verify(ORIG, REWRITE, job_terms=["kubernetes", "tableau"])
    out = cl.strip(REWRITE, rep)
    assert "Skills: Python, SQL, Excel" in out and "Kubernetes" not in out
    assert "Assisted with migrating reporting dashboards" in out   # true content kept via revert
    assert "35%" not in out and "team of 8" not in out
    assert cl.verify(ORIG, out, ["kubernetes", "tableau"]).counts() == {t: 0 for t in cl.CLAIM_TYPES}


def test_strip_by_type_only_touches_that_type():
    rep = cl.verify(ORIG, REWRITE, job_terms=["kubernetes", "tableau"])
    out = cl.strip(REWRITE, rep, ["skill"])
    assert "Kubernetes" not in out and "35%" in out


def test_control_removes_only_supported_units():
    import random
    rep = cl.verify(ORIG, REWRITE, job_terms=["kubernetes", "tableau"])
    out = cl.strip_random_supported(REWRITE, rep, 1, random.Random(0))
    assert "35%" in out and "team of 8" in out
    assert len(cl.units_of(out)) == len(cl.units_of(REWRITE)) - 1


def test_rule_rewrite_adds_no_claims():
    for r in load_resumes(SAMPLE_DIR / "resumes.csv", min_words=40):
        assert cl.verify(r["text"], rw.rule_rewrite(r["text"])).unsupported == []


def test_guarded_rewrite_removes_fabrications():
    r = load_resumes(SAMPLE_DIR / "resumes.csv", min_words=40)[0]
    job = load_jobs(SAMPLE_DIR / "jobs.json")[0]
    terms = ["kubernetes", "terraform", "aws"]
    out, rounds = rw.guarded_rewrite(FakeLLM(), r["text"], job, terms, seed=0)
    assert rounds >= 1
    assert cl.verify(r["text"], out, terms).unsupported == []


def test_run_pair_record_shape():
    resumes = load_resumes(SAMPLE_DIR / "resumes.csv", n=2, min_words=40)
    pair = make_pairs(resumes, load_jobs(SAMPLE_DIR / "jobs.json"))[0]
    rec = run_pair(pair, 0, FakeLLM(), FakeLLM(), 1, True, True)
    for v in ("orig", "llm", "stripped", "rule", "guarded", "control"):
        assert v in rec["scores"]["ats"] and v in rec["scores"]["llm"]
    assert sum(rec["unsupported_counts"]["llm"].values()) > 0
    assert sum(rec["unsupported_counts"]["guarded"].values()) == 0
    json.dumps(rec)  # serialisable


def test_pairs_matched_and_changer():
    resumes = load_resumes(SAMPLE_DIR / "resumes.csv", min_words=40)
    pairs = make_pairs(resumes, load_jobs(SAMPLE_DIR / "jobs.json"))
    for p in pairs:
        same = p["resume"]["category"] == p["job"]["category"]
        assert same == (p["group"] == "matched")


def test_pooled_share_and_per_pair():
    rows = [{"orig": 50, "llm": 70, "stripped": 60}, {"orig": 40, "llm": 50, "stripped": 40}]
    assert analyze.pooled_share(rows) == pytest.approx((10 + 10) / (20 + 10))
    assert analyze.pair_share({"orig": 50, "llm": 51, "stripped": 50}) is None   # gain < MIN_GAIN


def test_cohen_kappa():
    assert labelling.cohen_kappa(["u", "s", "u", "s"], ["u", "s", "u", "s"]) == 1.0
    assert labelling.cohen_kappa(["u", "u", "s", "s"], ["u", "s", "u", "s"]) == pytest.approx(0.0)


def test_labelling_evaluate_weighted(tmp_path):
    sheet = tmp_path / "sheet.csv"
    rows = [  # verifier, gold, weight
        ("unsupported", "U", 1), ("unsupported", "S", 1), ("supported", "U", 3), ("supported", "S", 3)]
    with open(sheet, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=labelling.FIELDS)
        w.writeheader()
        for i, (pred, gold, wt) in enumerate(rows):
            w.writerow({"row_id": i, "type": "skill", "verifier": pred, "weight": wt,
                        "label_a": gold, "label_b": gold})
    res = labelling.evaluate(str(sheet))
    assert res["precision_unsupported"] == pytest.approx(0.5)
    assert res["recall_unsupported"] == pytest.approx(1 / 4)
    assert res["cohen_kappa"] == 1.0


def test_audit_splits_gain_and_marks_lines():
    from research.audit import audit
    r = load_resumes(SAMPLE_DIR / "resumes.csv", min_words=40)[0]
    job = load_jobs(SAMPLE_DIR / "jobs.json")[0]
    res = audit(r["text"], job, llm=FakeLLM())
    s = res["scores"]
    assert res["gain"] == pytest.approx(s["llm"] - s["orig"], abs=0.11)
    assert res["earned_gain"] + res["fabricated_gain"] == pytest.approx(res["gain"], abs=0.11)
    flagged = [u for line in res["lines"] for u in line if u["claims"]]
    assert flagged and len(flagged) == res["n_flagged_units"]
    assert "guarded" in res["texts"]


def test_audit_pasted_rewrite_needs_no_llm():
    from research.audit import audit
    res = audit(ORIG, {"title": "Data Engineer", "description": "Kubernetes and Tableau"},
                rewrite=REWRITE, guarded=False)
    assert res["source"] == "pasted" and sum(res["counts"].values()) > 0


def test_verbatim_original_sentence_is_supported():
    orig = "Assisted in the managing of the company database."
    assert cl.verify(orig, orig + "\nLed the database team of 12 engineers.").unsupported_units() == {1}


def test_strip_fully_leaves_nothing_flagged():
    out = cl.strip_fully(ORIG, REWRITE, ["kubernetes", "tableau"])
    assert cl.verify(ORIG, out, ["kubernetes", "tableau"]).unsupported == []


def test_refusal_detected():
    assert rw.is_refusal("No resume can be successfully tailored to this job.")
    assert not rw.is_refusal("- Built ETL pipelines in Python.")


def test_api_audit_pasted_and_jobs():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    assert c.get("/api/health").json()["ok"]
    assert len(c.get("/api/jobs").json()["jobs"]) >= 24
    ex = c.get("/api/audit/example").json()
    r = c.post("/api/audit", json={"resume_text": ORIG, "job": {"title": "Data Engineer",
               "description": "Kubernetes and Tableau"}, "rewrite_text": REWRITE, "guarded": False})
    assert r.status_code == 200 and r.json()["source"] == "pasted" and ex["resume_text"]


def test_labelling_single_labeller_counts(tmp_path):
    sheet = tmp_path / "sheet.csv"
    with open(sheet, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=labelling.FIELDS)
        w.writeheader()
        w.writerow({"row_id": 1, "type": "skill", "verifier": "unsupported", "weight": 1, "label_a": "U"})
        w.writerow({"row_id": 2, "type": "skill", "verifier": "supported", "weight": 1, "label_a": "S"})
    res = labelling.evaluate(str(sheet))
    assert res["rows_with_gold"] == 2 and res["precision_unsupported"] == 1.0 and res["cohen_kappa"] is None


def _unsupported_credentials(original, rewrite):
    return [c.text for c in cl.verify(original, rewrite, []).claims if c.type == "credential" and not c.supported]


def test_degree_spelled_out_is_not_a_new_credential():
    for orig, rew in [
        ("Education\nB.E. in Computer Science", "Education\nBachelor of Engineering in Computer Science"),
        ("Education\nBE Computer Science", "Education\nBachelor of Engineering in Computer Science"),
        ("Education\nB.Tech in Information Technology", "Education\nBachelor of Technology in Information Technology"),
        ("Education\nBachelors in Commerce", "Education\nBachelor of Commerce"),
        ("Education\nMSc Physics", "Education\nMaster of Science in Physics"),
        ("Education\nMaster of Business Administration", "Education\nMBA"),
    ]:
        assert _unsupported_credentials(orig, rew) == [], (orig, rew)


def test_a_different_or_missing_degree_is_still_flagged():
    assert _unsupported_credentials("Education\nHigh school diploma", "Education\nBachelor of Engineering in CS")
    assert _unsupported_credentials("Education\nBachelor of Engineering", "Education\nMBA from XYZ")
    assert _unsupported_credentials("Education\nBachelor of Engineering", "Education\nMaster of Engineering")
    # the verb "be" in the original is not a degree
    assert _unsupported_credentials("Skills\nIt will be fine to be here", "Education\nBachelor of Science")


def _flags(original, rewrite):
    return [(c.type, c.text) for c in cl.verify(original, rewrite, []).claims if not c.supported]


def test_inflected_verb_in_original_is_not_a_promotion():
    orig = "Built a database-driven system to organize and manage second-hand car sales, keeping track of vehicle details, buyers and transactions."
    rew = "- Simplified record handling and improved the efficiency of managing vehicle sales information."
    assert not [f for f in _flags(orig, rew) if f[0] == "role_scope"]


def test_summary_that_rephrases_the_candidates_facts_is_grounded():
    orig = ("Passionate software engineer with a focus on continuous learning and real-world application of technology.\n"
            "Built a database-driven platform. CookCraft is an AI-powered platform. Developing software applications.")
    rew = ("Familiar with database management and AI-powered applications. "
           "A quick learner with a strong interest in continuous technical growth and software development.")
    assert _flags(orig, rew) == []


def test_new_substance_in_a_soft_sentence_is_still_flagged():
    orig = "Built a database-driven platform. Developing software applications."
    assert _flags(orig, "Strong enterprise ERP migration experience across SAP landscapes.")
    assert _flags("Assisted the team lead with testing.", "Led the testing team.")
