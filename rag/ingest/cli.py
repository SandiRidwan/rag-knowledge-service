"""Ingest CLI: build/rebuild the index from a folder of docs.

    python -m rag.ingest.cli                 # ingests data/corpus
    python -m rag.ingest.cli --path <dir>    # ingest any folder of .md/.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .chunk import ingest


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="", help="folder of .md/.txt (default data/corpus)")
    args = ap.parse_args(argv)
    result = ingest(Path(args.path) if args.path else None)
    print(f"Ingested {result['files']} files -> {result['chunks']} chunks")
    print(f"Index: {result['index']}")


if __name__ == "__main__":
    main()
