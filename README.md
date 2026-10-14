<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Orbitron&weight=900&size=32&duration=3000&pause=1000&color=0F766E&center=true&vCenter=true&width=980&height=70&lines=RAG+KNOWLEDGE+SERVICE" alt="RAG Knowledge Service" />

![Python](https://img.shields.io/badge/Python-3.10+-1F5C3D?style=for-the-badge&logo=python&logoColor=white)
![No API key](https://img.shields.io/badge/Runs_with-NO_API_key-2E7D32?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-Service-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Tests](https://img.shields.io/badge/tests-10_passing-2E7D32?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-0D1117?style=for-the-badge)

</div>

---

## 🔎 What this is

**Point it at a folder of your documents and ask questions.** It retrieves the
relevant passages, answers **with citations**, and — the part most RAG demos skip —
**refuses** when your documents do not cover the question, instead of letting the
model invent an answer.

**It runs with no API key.** Retrieval is local (BM25), so it works on a laptop, in
CI, or on a $5 VPS. Add an LLM key and answers become synthesised; without one you
still get cited passages. Your documents never leave the machine.

```bash
pip install -r requirements.txt

# 1) ingest a folder (defaults to data/corpus, which ships with a real sample)
python -m rag.ingest.cli
# ...or your own docs:
python -m rag.ingest.cli --path /path/to/your/markdown

# 2) ask
python -m rag.cli ask "How do I mock a network request?"
python -m rag.cli ask "How do I mock a network request?" --extractive   # no LLM

# 3) or use the service / UI
uvicorn api.main:app          # POST /ask  /retrieve  /ingest   GET /health /sources
streamlit run app.py
```

---

## ⚡ Why it is worth using

| Problem with most RAG demos | What this does |
|---|---|
| Needs a paid embedding API + vector DB | **BM25 retrieval, zero dependencies, no key** |
| Answers confidently when the docs don't cover it | **Refuses** below a coverage threshold (`REFUSE_BELOW`) |
| "Sources" are vague | Every answer carries **exact chunk citations** (file › section) |
| Only answers, no audit | `/retrieve` returns raw chunks + scores for inspection |
| Locks you into a stack | ~600 lines, readable, no framework — swap in embeddings at one file |

---

## 🧪 Measured on a real corpus

The repo ships a **real corpus** (Playwright's official docs, 12 files) so you can
run the eval immediately:

```
$ python -m rag.cli eval
questions      : 10
answered       : 7
refused        : 3
correct source : 7  (70%)
```

- **7/7** in-corpus questions answered with the **correct source cited**
- **3/3** off-corpus questions (`capital of France`, `sourdough`, `best stock`)
  correctly **refused**

That refusal rate is the whole point: the failure mode of a RAG system is not a
wrong answer you notice, it is a confident wrong answer you do not.

---

## 🧭 How it works

```
 your docs (.md/.txt)
        │  rag/ingest/chunk.py     heading-aware chunks + overlap
        ▼
   data/index.json
        │  rag/retrieve/bm25.py    BM25 (k1=1.5, b=0.75) + term coverage
        ▼
   hits ──► coverage < REFUSE_BELOW ? ──► refuse (no answer)
        │
        ▼
   rag/service.py                 extractive (cite the passage)
        └── or ──► LLM synthesis  "answer ONLY from context, cite [n], else NOT_IN_CONTEXT"
```

**Refusal is a retrieval decision, not a prompt trick.** BM25 always returns *a*
best hit, so a score threshold is unreliable; this uses **term coverage** (how much
of the question the best chunk actually contains). That is why `capital of France`
scores 0.00 coverage and is refused, while `how do I mock a request` scores 0.50.

| File | Responsibility |
|---|---|
| `rag/ingest/chunk.py` | heading-aware chunking with overlap; builds `index.json` |
| `rag/retrieve/bm25.py` | BM25 ranking + coverage; no dependencies |
| `rag/service.py` | retrieve → cite → synthesise or **refuse** |
| `rag/cli.py` | `ask` and `eval` commands |
| `api/main.py` | FastAPI: `/ask`, `/retrieve`, `/ingest`, `/sources`, `/health` |
| `app.py` | Streamlit UI with citations + refusal |

---

## ✅ Quality — 10 tests (offline)

```
PASS  tokenizer drops stopwords (and question words)
PASS  chunks are non-empty and size-bounded
PASS  index loads (300+ chunks from the sample corpus)
PASS  a relevant question finds the RIGHT source
PASS  coverage is high enough for an in-corpus question
PASS  off-corpus questions are REFUSED (two of them)
PASS  a real answer always carries citations
PASS  the whole eval set: answers all in-corpus, refuses all off-corpus
```

No API key, no network — the suite runs anywhere.

---

## 📁 Structure

```
rag-knowledge-service/
├── rag/
│   ├── config.py          # thresholds, optional LLM provider
│   ├── ingest/chunk.py    # chunking + index build
│   ├── retrieve/bm25.py   # BM25 + coverage (dependency-free)
│   ├── service.py         # the ask() pipeline: cite or refuse
│   └── cli.py             # ask / eval
├── api/main.py            # FastAPI service
├── app.py                 # Streamlit UI
├── data/corpus/           # a REAL sample corpus (Playwright docs) to try now
├── data/eval_questions.json
└── tests/test_rag.py      # 10 tests
```

---

## 🚀 Use it on your own docs

```bash
git clone https://github.com/SandiRidwan/rag-knowledge-service
cd rag-knowledge-service
pip install -r requirements.txt

# empty the sample corpus and drop in your own markdown/text
python -m rag.ingest.cli --path ~/notes

python -m rag.cli ask "what did I decide about the database?"
```

Optional LLM synthesis (better prose, same citations):

```bash
set OPENAI_API_KEY=...        # or TOKENHARBOR_API_KEY / GROQ_API_KEY / GEMINI_API_KEY
```

No key needed to run; the answer is extractive (the passage + its source).

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Retrieval** | BM25 (implemented here) + term coverage for refusal |
| **Chunking** | heading-aware, paragraph packing, overlap |
| **Answer** | extractive by default; LLM synthesis optional (OpenAI/Claude/Gemini/Groq) |
| **Service** | FastAPI; Streamlit UI |
| **Dependencies** | 2 required (`fastapi`, `uvicorn`); retrieval itself is stdlib-only |

---

## ⚠️ Limitations (honest)

- **BM25, not embeddings.** Great for keyword-ish questions and exact terms; a
  question that shares no vocabulary with the answer may miss. `rag/retrieve/` is
  the one place to add embeddings if you need semantic recall.
- **The sample corpus is Playwright docs** — small, and there to make the eval
  reproducible. Point it at your own files for real use.
- **Synthesis cites `[n]` but is not grounded-verified.** The refusal gate protects
  the off-topic case; a strict build would verify each claim against a chunk.
- **Single-process index** (`index.json`). Fine to ~10k chunks; beyond that, move to
  SQLite/pgvector.

---

## 👤 Author

<div align="center">

**Sandi Ridwan** — Data Automation Engineer · RAG & LLM Applications · Python

📍 Palu, Central Sulawesi, Indonesia

[![Upwork](https://img.shields.io/badge/Upwork-Hire_Me-0F766E?style=for-the-badge&logo=upwork&logoColor=white)](https://www.upwork.com/freelancers/~011f6d0fbb4a372974)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/sandi-ridwan)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/SandiRidwan)

</div>

## 📄 License

MIT — code. The sample corpus is Playwright's documentation (Apache-2.0).
