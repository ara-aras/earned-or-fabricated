# AI Resume: Earned vs Fabricated Advantage

LLM resume rewriters raise applicant-tracking (ATS) scores. This project measures
**how much of that gain comes from claims the original resume does not support**:
skills the candidate never listed, numbers they never wrote, inflated roles, degrees
and certificates they do not hold. It also tests a **guarded rewriter** that keeps
only the earned part of the gain.

```
fabricated share = (S_llm − S_stripped) ÷ (S_llm − S_orig)
```

`S_orig` is the original resume's score, `S_llm` the LLM rewrite's, and `S_stripped`
the rewrite's with every unsupported claim removed.

## What is here

| Path | What it is |
| --- | --- |
| `backend/research/` | The experiment: claim verifier, rewriters, screeners, runner, statistics, labelling tools. See [backend/research/README.md](backend/research/README.md) |
| `backend/app/` | Shared rule layers (ATS screen, resume style rules, job fetch) and the web API |
| `frontend/` | The web app: audit one resume against one job |
| `backend/tests/` | Tests (`python -m pytest tests -q` from `backend/`) |

## Run the web app

Needs Python 3.10+, Node 20+, and [Ollama](https://ollama.com) with the rewriter model
(setup in [backend/research/README.md](backend/research/README.md#2-get-the-models)).

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --port 8420
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the address `npm run dev` prints. Paste a resume, pick a listing (or paste one),
and either let the local model rewrite it or paste a rewrite made with ChatGPT,
Gemini or another tool. The page highlights every unsupported claim, splits the score
gain into earned and fabricated parts, and offers the guarded rewrite.

## Run the experiment

See [backend/research/README.md](backend/research/README.md): data download, model
setup, verifier calibration (hand labelling), main run, and analysis.
