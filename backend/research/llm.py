"""LLM access for the experiment: one small interface, three backends.

* OpenAICompatLLM -- any server speaking the OpenAI chat-completions API.
  Ollama (local, free: http://127.0.0.1:11434/v1), Groq, OpenRouter, vLLM and
  LM Studio all do. Configured by env vars or constructor args.
* CachedLLM -- wraps any backend with an on-disk cache keyed by the full
  request, so re-running the experiment after a crash costs nothing and every
  number in the report can be reproduced from the cache.
* FakeLLM -- deterministic stand-in used by the tests and the smoke run. Its
  rewrites fabricate on purpose (JD skills, a metric, an inflated verb, an
  invented team) so the whole pipeline can be exercised without a model.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Protocol

import httpx

def _load_dotenv() -> None:
    """Read KEY=VALUE lines from a .env file (backend/ or the repo root) into os.environ.
    Variables that are already set win, so a shell export still overrides the file."""
    here = Path(__file__).resolve()
    for folder in (here.parents[1], here.parents[2]):
        env = folder / ".env"
        if not env.is_file():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"   # Ollama's OpenAI-compatible endpoint
DEFAULT_MODEL = "qwen3.5-4b-8k"


class LLM(Protocol):
    name: str

    def complete(self, prompt: str, *, system: str | None = None,
                 temperature: float = 0.7, seed: int | None = None) -> str: ...


class OpenAICompatLLM:
    def __init__(self, model: str | None = None, base_url: str | None = None,
                 api_key: str | None = None, timeout: float = 300.0, retries: int = 3):
        self.model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "ollama")
        self.name = self.model
        self.retries = retries
        # Thinking models (Qwen3, Qwen3.5, DeepSeek-R1 ...) otherwise spend hundreds of hidden
        # tokens per call -- ~40x slower on Ollama for no gain here. "none" turns it off;
        # set LLM_REASONING_EFFORT="" to send nothing (some hosted APIs reject the field).
        default_effort = "none" if ":11434" in self.base_url else ""
        self.reasoning_effort = os.environ.get("LLM_REASONING_EFFORT", default_effort)
        self._client = httpx.Client(timeout=timeout)

    def complete(self, prompt: str, *, system: str | None = None,
                 temperature: float = 0.7, seed: int | None = None) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        body = {"model": self.model, "messages": messages, "temperature": temperature}
        if seed is not None:
            body["seed"] = seed
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        last: Exception | None = None
        for attempt in range(self.retries):
            try:
                r = self._client.post(f"{self.base_url}/chat/completions", json=body,
                                      headers={"Authorization": f"Bearer {self.api_key}"})
                if r.status_code == 429 or r.status_code >= 500:
                    if "repeat limit" in r.text and ":11434" in self.base_url:
                        self._reload_ollama_model()
                    raise httpx.HTTPStatusError(f"HTTP {r.status_code}: {r.text[:200]}",
                                                request=r.request, response=r)
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                return re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last = exc
                time.sleep(2 ** attempt)
        raise RuntimeError(f"LLM call to {self.base_url} ({self.model}) failed: {last}")

    def _reload_ollama_model(self) -> None:
        """Unload the model so the next call gets a fresh instance. Ollama's llama.cpp
        runner can get stuck answering every request with "token repeat limit reached"
        (seen with Qwen3.5's hybrid memory after long runs); reloading clears it."""
        root = self.base_url.removesuffix("/v1")
        try:
            self._client.post(f"{root}/api/generate", json={"model": self.model, "keep_alive": 0})
        except httpx.HTTPError:
            pass


class CachedLLM:
    """Disk cache in front of any LLM. One JSON file per distinct request."""

    def __init__(self, inner: LLM, cache_dir: str | Path):
        self.inner = inner
        self.name = inner.name
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def complete(self, prompt: str, *, system: str | None = None,
                 temperature: float = 0.7, seed: int | None = None) -> str:
        key = hashlib.sha256(json.dumps([self.name, system, prompt, temperature, seed]).encode()).hexdigest()
        path = self.dir / f"{key[:2]}" / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["output"]
        out = self.inner.complete(prompt, system=system, temperature=temperature, seed=seed)
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"model": self.name, "system": system, "prompt": prompt,
                                    "temperature": temperature, "seed": seed, "output": out}),
                        encoding="utf-8")
        return out


class FakeLLM:
    """Deterministic test double. Recognises the experiment's three prompt kinds
    by marker lines (see rewriters.py / screeners.py) and answers each one."""

    name = "fake"

    def complete(self, prompt: str, *, system: str | None = None,
                 temperature: float = 0.7, seed: int | None = None) -> str:
        if "### SCORE" in prompt:
            return self._score(prompt)
        if "### REVISE" in prompt:
            return self._revise(prompt)
        return self._rewrite(prompt)

    @staticmethod
    def _section(prompt: str, name: str) -> str:
        m = re.search(rf"<{name}>\n(.*?)\n</{name}>", prompt, re.S)
        return m.group(1) if m else ""

    def _rewrite(self, prompt: str) -> str:
        resume, job = self._section(prompt, "resume"), self._section(prompt, "job")
        lines = resume.splitlines()
        job_skills = [w for w in ("kubernetes", "terraform", "salesforce", "tableau", "python")
                      if w in job.lower() and w not in resume.lower()]
        out, bulleted = [], False
        for ln in lines:
            ln = re.sub(r"\b(Assisted|Helped) (with )?", "Led ", ln)          # role inflation
            if ln.lower().startswith("skills") and job_skills:
                ln = ln.rstrip() + ", " + ", ".join(job_skills)                # skills taken from the JD
            if ln.startswith("- ") and not bulleted:
                ln = ln.rstrip(".") + ", improving efficiency by 35%"           # invented metric
                bulleted = True
            out.append(ln)
        out.append("- Managed a cross-functional team of 8 engineers delivering cloud migration")
        return "\n".join(out)

    def _revise(self, prompt: str) -> str:
        # Honest reviser: returns each numbered line with the unsupported parts cut.
        lines = re.findall(r"^(\d+)\. (.*)$", self._section(prompt, "lines"), re.M)
        fixed = []
        for n, text in lines:
            text = re.sub(r", improving efficiency by \d+%", "", text)
            text = re.sub(r"^- Led ", "- Assisted with ", text)
            if "team of 8" in text:
                text = ""
            fixed.append(f"{n}. {text}")
        return "\n".join(fixed)

    def _score(self, prompt: str) -> str:
        resume, job = self._section(prompt, "resume").lower(), self._section(prompt, "job").lower()
        words = set(re.findall(r"[a-z][a-z+#.]{2,}", job))
        hit = sum(1 for w in words if w in resume)
        return json.dumps({"score": min(100, 20 + int(80 * hit / max(1, len(words))))})


def make_llm(spec: str, cache_dir: str | Path | None = None) -> LLM:
    """`fake`, or `model` / `model@base_url` for an OpenAI-compatible server."""
    if spec == "fake":
        return FakeLLM()
    model, _, base = spec.partition("@")
    llm: LLM = OpenAICompatLLM(model=model or None, base_url=base or None)
    return CachedLLM(llm, cache_dir) if cache_dir else llm
