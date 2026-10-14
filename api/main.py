"""
FastAPI service for the knowledge base.

    uvicorn api.main:app --reload
    curl -s localhost:8000/health
    curl -s -X POST localhost:8000/ask -H 'content-type: application/json' \
         -d '{"question":"How do I mock a request?","extractive":true}'

Endpoints:
  GET  /health          service + index + provider status
  GET  /sources         the files in the corpus
  POST /ask             retrieve + answer with citations (or refuse)
  POST /retrieve        raw chunks, no answer synthesis
  POST /ingest          rebuild the index from the corpus
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag import config
from rag.ingest.chunk import ingest, load_chunks
from rag.service import KnowledgeBase

app = FastAPI(title="RAG Knowledge Service", version="1.0.0")
_kb: KnowledgeBase | None = None


def kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        try:
            _kb = KnowledgeBase()
        except SystemExit as e:
            raise HTTPException(503, str(e))
    return _kb


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(config.TOP_K, ge=1, le=20)
    extractive: bool = Field(False, description="skip the LLM, cite the passage")


class RetrieveRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(config.TOP_K, ge=1, le=20)


@app.get("/health")
def health() -> dict:
    files = chunks = 0
    if config.INDEX.is_file():
        chunks = len(load_chunks())
        files = len({c.source for c in load_chunks()})
    return {"status": "ok", "files": files, "chunks": chunks,
            "llm_provider": config.active_llm(),
            "refuse_below": config.REFUSE_BELOW}


@app.get("/sources")
def sources() -> dict:
    try:
        names = sorted({c.source for c in load_chunks()})
    except SystemExit as e:
        raise HTTPException(503, str(e))
    return {"count": len(names), "sources": names}


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    ans = kb().ask(req.question, top_k=req.top_k, use_llm=not req.extractive)
    return ans.to_dict()


@app.post("/retrieve")
def retrieve(req: RetrieveRequest) -> dict:
    hits = kb().retrieve(req.question, top_k=req.top_k)
    return {"question": req.question,
            "hits": [{"source": h.chunk.source, "title": h.chunk.title,
                      "chunk_id": h.chunk.id, "score": h.score,
                      "text": h.chunk.text[:400]} for h in hits]}


@app.post("/ingest")
def rebuild() -> dict:
    global _kb
    result = ingest()
    _kb = None  # force reload
    return result
