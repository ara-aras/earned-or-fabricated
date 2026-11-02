"""One-minute check that the model behind the audit answers.

    .venv\Scripts\python check_llm.py

Prints where calls go, whether a key is set, and the model's real reply or the real error
(wrong key, no internet, blocked network, unknown model), so a 503 in the app can be explained.
"""
from __future__ import annotations

import os
import sys

import httpx

from research.llm import DEFAULT_BASE_URL   # importing this also loads .env

spec = os.environ.get("AUDIT_LLM", "")
model, _, base = spec.partition("@")
base = (base or os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
model = model or os.environ.get("LLM_MODEL", "")
key = os.environ.get("LLM_API_KEY", "")

print(f"model     : {model or '(not set)'}")
print(f"server    : {base}")
print(f"key set   : {key not in ('', 'ollama', 'your-groq-api-key')}")
if not model or not os.environ.get("AUDIT_LLM"):
    print("\nAUDIT_LLM is not set, so the app uses a local Ollama model. Create .env from .env.example "
          "(next to this folder or inside it), add the Groq key, then restart the server.")

body = {"model": model, "messages": [{"role": "user", "content": "Reply with the single word OK."}], "max_tokens": 200}
if "gpt-oss" in model:
    body["reasoning_effort"] = "low"
try:
    r = httpx.post(f"{base}/chat/completions", json=body, headers={"Authorization": f"Bearer {key}"}, timeout=30)
except httpx.HTTPError as exc:
    print(f"\nFAILED to reach {base}: {type(exc).__name__}: {exc}")
    print("-> no internet, a firewall/proxy blocking the address, or the server is not running (for Ollama).")
    sys.exit(1)

if r.status_code == 200:
    reply = (r.json()["choices"][0]["message"].get("content") or "").strip()
    print(f"\nOK ({r.status_code}). The model replied: {reply!r}")
    sys.exit(0 if reply else 1)

hints = {401: "the key is wrong, expired or has spaces/quotes around it", 403: "the key or network is not allowed (blocked region or network)",
         404: "the model name is wrong for this server", 429: "rate limit or quota: wait a minute and retry"}
print(f"\nFAILED: HTTP {r.status_code}: {r.text[:300]}")
print(f"-> {hints.get(r.status_code, 'see the message above')}")
sys.exit(1)
