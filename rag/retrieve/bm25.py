"""
Local retrieval: BM25 over chunks. No API key, no vector DB, no network.

This is deliberately dependency-light so the service runs anywhere (laptop, CI,
a $5 VPS). BM25 is strong on the exact case most people have: a folder of
documents and a question about them.

If you want embeddings later, rag/embed.py shows the drop-in point; the rest of
the pipeline (ingest -> chunk -> retrieve -> answer -> cite) is unchanged.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

# a compact English stopword list; extend if your corpus needs it
STOP = set("""a an and are as at be by for from has have he her his i in is it its
of on that the to was were will with this these those you your we our they their
what which who whom whose when where why how do does did can could should would
may might must shall will""".split())

_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in STOP and len(w) > 1]


@dataclass
class Chunk:
    id: str
    source: str          # file name / doc id
    title: str           # heading or file stem
    text: str
    tokens: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "source": self.source, "title": self.title,
                "text": self.text, "tokens": self.tokens}


@dataclass
class Retrieved:
    chunk: Chunk
    score: float


class BM25:
    """Okapi BM25. `k1`/`b` are the standard defaults."""

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.N = len(chunks)
        self.avgdl = (sum(len(c.tokens) for c in chunks) / self.N) if self.N else 0
        self.tf: list[Counter] = [Counter(c.tokens) for c in chunks]
        df: Counter = Counter()
        for tf in self.tf:
            for term in tf:
                df[term] += 1
        self.idf = {
            t: math.log(1 + (self.N - n + 0.5) / (n + 0.5))
            for t, n in df.items()
        }

    def search(self, query: str, top_k: int = 5) -> list[Retrieved]:
        q = tokenize(query)
        if not q or not self.chunks:
            return []
        scored: list[Retrieved] = []
        for i, chunk in enumerate(self.chunks):
            tf = self.tf[i]
            dl = len(chunk.tokens) or 1
            s = 0.0
            for term in q:
                if term not in tf:
                    continue
                idf = self.idf.get(term, 0.0)
                freq = tf[term]
                s += idf * (freq * (self.k1 + 1)) / (
                    freq + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
            if s > 0:
                scored.append(Retrieved(chunk, round(s, 4)))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def coverage(self, query: str, chunk: "Chunk") -> float:
        """Fraction of the query's distinct terms that appear in the chunk."""
        q = set(tokenize(query))
        if not q:
            return 0.0
        present = sum(1 for t in q if t in set(chunk.tokens))
        return present / len(q)
