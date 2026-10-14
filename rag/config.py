"""Config: paths, retrieval settings, optional LLM provider."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CORPUS = DATA / "corpus"
INDEX = DATA / "index.json"
EVAL_SET = DATA / "eval_questions.json"
REPORTS = ROOT / "reports"

# Retrieval
CHUNK_CHARS = 700          # target chunk size
CHUNK_OVERLAP = 120        # overlap between chunks
TOP_K = 5                  # chunks retrieved per question
MIN_SCORE = 0.08           # below this raw BM25 score, ignore a chunk
REFUSE_BELOW = 0.35        # below this term-coverage, refuse instead of guessing

# Optional LLM (for answer synthesis). Without it, answers are extractive.
LLM_PROVIDERS = {
    "tokenharbor": {"base_url": "https://tokenharbor.ai/v1",
                    "key_env": "TOKENHARBOR_API_KEY",
                    "model": "deepseek-v4.1-flash:free"},
    "openai": {"base_url": "https://api.openai.com/v1",
               "key_env": "OPENAI_API_KEY", "model": "gpt-4o-mini"},
    "groq": {"base_url": "https://api.groq.com/openai/v1",
             "key_env": "GROQ_API_KEY", "model": "llama-3.1-8b-instant"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
               "key_env": "GEMINI_API_KEY", "model": "gemini-flash-lite-latest"},
}


def _opencode_auth() -> dict:
    p = Path(os.path.expanduser("~")) / ".local" / "share" / "opencode" / "auth.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def llm_key(provider: str) -> str:
    cfg = LLM_PROVIDERS[provider]
    if os.environ.get(cfg["key_env"]):
        return os.environ[cfg["key_env"]]
    auth = _opencode_auth()
    for name, cred in auth.items():
        if isinstance(cred, dict) and (name == provider or
                                       (provider == "tokenharbor"
                                        and "tokenharbor" in name)):
            return cred.get("key") or cred.get("access") or ""
    return ""


def active_llm() -> str | None:
    for p in LLM_PROVIDERS:
        if llm_key(p):
            return p
    return None
