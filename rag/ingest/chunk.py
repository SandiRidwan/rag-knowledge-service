"""
Ingest: read text/markdown files, chunk them, and build the index.

Chunking is heading-aware: a markdown heading starts a new chunk, and long
sections are split on paragraph boundaries with a small overlap so an answer
that spans a boundary is still retrievable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import CORPUS, INDEX, CHUNK_CHARS, CHUNK_OVERLAP
from ..retrieve.bm25 import Chunk, tokenize

_SUPPORTED = {".md", ".markdown", ".txt", ".rst"}


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def chunk_file(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    # split on markdown headings, keeping the heading with its section
    sections = re.split(r"\n(?=#{1,6}\s)", raw)
    chunks: list[Chunk] = []
    idx = 0
    for section in sections:
        section = section.strip()
        if not section:
            continue
        heading = ""
        first = section.splitlines()[0] if section.splitlines() else ""
        if first.startswith("#"):
            heading = first.lstrip("# ").strip()
            section = "\n".join(section.splitlines()[1:]).strip()
        title = heading or path.stem.replace("_", " ").title()

        # pack paragraphs into chunks up to CHUNK_CHARS, with overlap
        buf = ""
        for para in _split_paragraphs(section):
            if len(buf) + len(para) + 2 <= CHUNK_CHARS:
                buf = f"{buf}\n\n{para}".strip()
            else:
                if buf:
                    idx += 1
                    chunks.append(_mk(path, title, buf, idx))
                # start next with an overlap tail of the previous
                tail = buf[-CHUNK_OVERLAP:] if len(buf) > CHUNK_OVERLAP else buf
                buf = f"{tail}\n\n{para}".strip() if tail else para
        if buf:
            idx += 1
            chunks.append(_mk(path, title, buf, idx))
    return chunks


def _mk(path: Path, title: str, text: str, idx: int) -> Chunk:
    chunk_id = f"{path.stem}#{idx}"
    return Chunk(id=chunk_id, source=path.name, title=title, text=text,
                 tokens=tokenize(text))


def ingest(corpus_dir: Path | None = None) -> dict:
    corpus = corpus_dir or CORPUS
    if not corpus.is_dir():
        raise SystemExit(f"corpus folder not found: {corpus}")
    files = sorted(p for p in corpus.rglob("*") if p.suffix.lower() in _SUPPORTED)
    if not files:
        raise SystemExit(f"no .md/.txt files in {corpus}; add some and re-run.")

    chunks: list[Chunk] = []
    for f in files:
        chunks.extend(chunk_file(f))

    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps({
        "files": [f.name for f in files],
        "chunks": [c.to_dict() for c in chunks],
    }, indent=1), encoding="utf-8")
    return {"files": len(files), "chunks": len(chunks), "index": str(INDEX)}


def load_chunks() -> list[Chunk]:
    if not INDEX.is_file():
        raise SystemExit("no index yet; run: python -m rag.ingest.cli")
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    return [Chunk(**c) for c in data["chunks"]]
