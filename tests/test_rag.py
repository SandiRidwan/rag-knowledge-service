"""
Tests for the RAG service. Offline (no API key, no network).

Verifies the things that matter for trust:
  - chunking produces retrievable, size-bounded chunks
  - retrieval finds the right source for a real question
  - the service REFUSES a question the corpus does not cover
  - an answer always carries citations when it is not a refusal
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag import config  # noqa: E402
from rag.ingest.chunk import load_chunks, chunk_file  # noqa: E402
from rag.retrieve.bm25 import BM25, tokenize  # noqa: E402
from rag.service import KnowledgeBase  # noqa: E402


class TestChunking(unittest.TestCase):
    def test_tokenize_drops_stopwords(self):
        toks = tokenize("How do I mock a network request in a test?")
        self.assertIn("mock", toks)
        self.assertNotIn("do", toks)      # stopword
        self.assertNotIn("the", toks)

    def test_chunks_bounded_and_nonempty(self):
        for f in config.CORPUS.glob("*.md"):
            chunks = chunk_file(f)
            for c in chunks:
                self.assertTrue(c.text.strip())
                # allow overlap headroom over the target
                self.assertLessEqual(len(c.text), config.CHUNK_CHARS + 400)

    def test_index_loads(self):
        chunks = load_chunks()
        self.assertGreater(len(chunks), 50)
        self.assertTrue(all(c.source and c.id for c in chunks))


class TestRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()

    def test_relevant_question_finds_right_source(self):
        hits = self.kb.retrieve("How do I mock a network request?")
        self.assertTrue(hits)
        self.assertEqual(hits[0].chunk.source, "request-mocking.md")

    def test_storage_state_question(self):
        hits = self.kb.retrieve("What is storage state used for?")
        self.assertEqual(hits[0].chunk.source, "storage-state.md")

    def test_coverage_high_for_relevant(self):
        hits = self.kb.retrieve("How do I record a video?")
        cov = self.kb.bm25.coverage("How do I record a video?", hits[0].chunk)
        self.assertGreaterEqual(cov, config.REFUSE_BELOW)


class TestRefusal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()

    def test_refuses_off_corpus_question(self):
        ans = self.kb.ask("What is the capital of France?", use_llm=False)
        self.assertTrue(ans.refused)

    def test_refuses_another_off_corpus_question(self):
        ans = self.kb.ask("How do I bake sourdough bread?", use_llm=False)
        self.assertTrue(ans.refused)

    def test_answers_on_corpus_question_with_citations(self):
        ans = self.kb.ask("How do I mock a network request?", use_llm=False)
        self.assertFalse(ans.refused)
        self.assertTrue(ans.citations)
        self.assertEqual(ans.citations[0].source, "request-mocking.md")


class TestEvalSet(unittest.TestCase):
    def test_eval_set_refuses_all_offtopic_and_answers_all_incorpus(self):
        import json
        qs = json.loads(config.EVAL_SET.read_text(encoding="utf-8"))
        kb = KnowledgeBase()
        for item in qs:
            ans = kb.ask(item["question"], use_llm=False)
            if item.get("expect_source"):
                self.assertFalse(ans.refused, f"should answer: {item['question']}")
                self.assertTrue(
                    any(item["expect_source"] in c.source for c in ans.citations),
                    f"wrong source for: {item['question']}")
            else:
                self.assertTrue(ans.refused,
                                f"should refuse: {item['question']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
