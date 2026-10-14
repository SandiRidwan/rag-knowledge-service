"""Ask CLI: query the knowledge base.

    python -m rag.cli ask "how do I mock a request?"
    python -m rag.cli ask "..." --extractive      # no LLM, citation only
    python -m rag.cli eval                         # run the eval question set
"""

from __future__ import annotations

import argparse
import json
import sys

from . import config
from .service import KnowledgeBase


def _ask(args) -> None:
    kb = KnowledgeBase()
    ans = kb.ask(args.question, use_llm=not args.extractive)
    print(f"\nQ: {args.question}\n")
    print(ans.answer)
    print(f"\nmode: {ans.mode}   refused: {ans.refused}")
    if ans.citations:
        print("\ncitations:")
        for c in ans.citations:
            print(f"  [{c.score}] {c.source} › {c.title}  ({c.chunk_id})")
    if args.json:
        print("\n" + json.dumps(ans.to_dict(), indent=2))


def _eval(args) -> None:
    if not config.EVAL_SET.is_file():
        sys.exit("no eval set; see data/eval_questions.json")
    qs = json.loads(config.EVAL_SET.read_text(encoding="utf-8"))
    kb = KnowledgeBase()
    answered = refused = correct = 0
    cite_ok = 0
    for item in qs:
        ans = kb.ask(item["question"], use_llm=False)
        expect = item.get("expect_source", "")
        hit = bool(expect) and any(expect in c.source for c in ans.citations)
        if ans.refused:
            refused += 1
        else:
            answered += 1
            if hit:
                correct += 1
                cite_ok += 1
    n = len(qs)
    print(f"questions      : {n}")
    print(f"answered       : {answered}")
    print(f"refused        : {refused}")
    print(f"correct source : {correct}  ({correct / n:.0%})")
    config.REPORTS.mkdir(parents=True, exist_ok=True)
    (config.REPORTS / "eval_summary.json").write_text(json.dumps({
        "questions": n, "answered": answered, "refused": refused,
        "correct_source": correct, "correct_source_rate": round(correct / n, 3),
    }, indent=2), encoding="utf-8")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m rag.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("--extractive", action="store_true")
    a.add_argument("--json", action="store_true")
    a.set_defaults(fn=_ask)

    e = sub.add_parser("eval")
    e.set_defaults(fn=_eval)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
