"""
The RAG service: retrieve → answer with citations → refuse when unsupported.

Design decisions that make it trustworthy (and different from a tutorial):
  1. Every answer carries CITATIONS: the exact chunks it used, with source + title.
  2. If retrieval is weak, it REFUSES ("I could not find this in the knowledge
     base") instead of letting the model improvise. The refusal threshold is in
     config, not buried in the prompt.
  3. Answers can be EXTRACTIVE (no LLM) or SYNTHESISED (with an LLM), and both
     cite. So the service works with zero API keys, and improves with one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from . import config
from .ingest.chunk import load_chunks
from .retrieve.bm25 import BM25, Retrieved


@dataclass
class Citation:
    source: str
    title: str
    chunk_id: str
    score: float
    excerpt: str

    def to_dict(self) -> dict:
        return self.__dict__


@dataclass
class Answer:
    question: str
    answer: str
    refused: bool
    mode: str                      # "extractive" | "synthesised"
    citations: list[Citation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "question": self.question, "answer": self.answer,
            "refused": self.refused, "mode": self.mode,
            "citations": [c.to_dict() for c in self.citations],
        }


class KnowledgeBase:
    def __init__(self, chunks=None):
        self.chunks = chunks if chunks is not None else load_chunks()
        self.bm25 = BM25(self.chunks)

    def retrieve(self, question: str, top_k: int = config.TOP_K) -> list[Retrieved]:
        return self.bm25.search(question, top_k=top_k)

    def _citations(self, hits: list[Retrieved]) -> list[Citation]:
        out = []
        for h in hits:
            excerpt = h.chunk.text.strip().replace("\n", " ")
            out.append(Citation(source=h.chunk.source, title=h.chunk.title,
                                chunk_id=h.chunk.id, score=h.score,
                                excerpt=excerpt[:300]))
        return out

    def _synthesise(self, question: str, hits: list[Retrieved]) -> str | None:
        provider = config.active_llm()
        if not provider:
            return None
        cfg = config.LLM_PROVIDERS[provider]
        key = config.llm_key(provider)
        context = "\n\n".join(
            f"[{i+1}] ({h.chunk.source} › {h.chunk.title})\n{h.chunk.text}"
            for i, h in enumerate(hits))
        system = (
            "You answer ONLY from the provided context. Cite sources inline as "
            "[1], [2] matching the context blocks. If the context does not contain "
            "the answer, reply exactly: NOT_IN_CONTEXT. Never use outside knowledge.")
        user = f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER (with [n] citations):"
        try:
            r = httpx.post(f"{cfg['base_url'].rstrip('/')}/chat/completions",
                           headers={"Authorization": f"Bearer {key}",
                                    "Content-Type": "application/json"},
                           json={"model": cfg["model"], "temperature": 0.0,
                                 "max_tokens": 500,
                                 "messages": [{"role": "system", "content": system},
                                              {"role": "user", "content": user}]},
                           timeout=40)
            if r.status_code != 200:
                return None
            text = r.json()["choices"][0]["message"]["content"].strip()
            if "NOT_IN_CONTEXT" in text:
                return None
            return text
        except Exception:
            return None

    def ask(self, question: str, top_k: int = config.TOP_K,
            use_llm: bool = True) -> Answer:
        hits = self.retrieve(question, top_k=top_k)

        # Refusal is decided by COVERAGE: how much of the question the best chunk
        # actually contains. A scoring-only threshold is unreliable because BM25
        # always returns its best hit. If the question's own terms are largely
        # absent from the top chunk, the corpus does not cover it - refuse.
        coverage = self.bm25.coverage(question, hits[0].chunk) if hits else 0.0
        if not hits or coverage < config.REFUSE_BELOW:
            return Answer(
                question=question,
                answer=("I could not find this in the knowledge base. The corpus "
                        "does not appear to cover it, so I will not guess. Try "
                        "rephrasing, or add the source document."),
                refused=True, mode="extractive",
                citations=self._citations(hits[:2]))

        citations = self._citations(hits)
        if use_llm:
            synth = self._synthesise(question, hits)
            if synth:
                return Answer(question, synth, False, "synthesised", citations)

        # extractive fallback: return the strongest passage with its source
        top = hits[0].chunk
        answer = (f"{top.text.strip()[:700]}\n\n"
                  f"(Source: {top.source} › {top.title})")
        return Answer(question, answer, False, "extractive", citations)
