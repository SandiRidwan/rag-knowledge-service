# Promo drafts — ready to post

Purpose: get the repos in front of the people who would actually use them.
Two rules for every post:

1. **Lead with the problem, not the repo.** Nobody clicks "I made a thing"; people
   click "here's how to fix the thing that annoys you".
2. **Give the value in the post itself.** A copy-pasteable snippet or a number gets
   upvotes; "check out my repo" gets removed by mods.

Post in this order of leverage: n8n community → r/n8n → r/LocalLLaMA → r/dataengineering
→ Hacker News (Show HN) → LinkedIn. Space them out; don't dump all at once.

---

## 1. rag-knowledge-service — the strongest opener

### r/LocalLLaMA

**Title:** I built a local RAG that refuses to answer when your docs don't cover the question (no API key, no vector DB)

**Body:**

Most RAG demos fail in the one way that actually matters: ask something your
documents don't cover, and the model makes something up. You don't notice, because
the answer looks fine.

I wanted the opposite: a RAG service that **runs with no API key** (local BM25, no
embeddings, no vector DB) and **refuses** when the corpus doesn't cover the
question. Every answer carries the exact chunk it came from.

The design decision that mattered: **refusal is a retrieval decision, not a prompt
trick.** BM25 always returns *a* best hit, so a score threshold never fires. I use
**term coverage** instead — how much of the question the top chunk actually
contains:

```
"how do I mock a request"   -> coverage 0.50 -> answered, cited
"what is the capital of FR" -> coverage 0.00 -> refused
"how do I bake sourdough"   -> coverage 0.00 -> refused
```

(Question words like how/what/do have to be stopwords, or coverage drops and you
refuse valid questions too — that bit me first.)

Ships with a real sample corpus (Playwright docs) and an eval, so you can clone and
see numbers immediately:

```
questions : 10   answered : 7   refused : 3
correct source : 7 (70%)
```

Repo: https://github.com/SandiRidwan/rag-knowledge-service

`pip install -r requirements.txt && python -m rag.ingest.cli --path ~/your/notes`
then `python -m rag.cli ask "..."`. Add an LLM key and answers get synthesised;
without one you still get cited passages.

Happy to answer questions about the chunking / coverage threshold.

---

### n8n community forum (community.n8n.io) — Show & Tell

**Title:** 3 importable n8n AI workflows built around the safe patterns (pre-LLM validation, dedupe, fail-closed approval)

**Body:**

I kept seeing the same three bugs in AI-automation templates, so I packaged three
workflows that handle them, plus a validator.

**01 — email triage:** webhook → validate → LLM classify → route to Slack. The
email is validated *before* the LLM call, and if the model returns junk the item
goes to a human queue — never down a confident wrong route.

**02 — lead enrichment:** a duplicate guard runs **before** the LLM and before the
write, so a retry never creates a second CRM row or pays for enrichment twice. A
failed enrich returns `needs_review`, not a fabricated ICP score.

**03 — refund approval gate:** this one **fails closed.** A refund above
`AUTO_APPROVE_MAX` (default 0) is parked for a Slack approve/reject and is never
executed automatically. Every request writes an audit row.

All three import verified on n8n 2.32:

```
n8n import:workflow --input=workflows/01-email-triage.json
```

There's also `scripts/validate_workflows.py` — point it at any workflow export. It
catches missing top-level keys, duplicate node names (which silently break
connections), connections to non-existent nodes, orphan nodes, HTTP nodes with no
URL, and `$env.*` vars used but not declared. Exits non-zero, so it drops into CI.

(One gotcha worth knowing: a workflow JSON needs a top-level `id` or import fails
with `NOT NULL constraint failed: workflow_entity.id`.)

Repo: https://github.com/SandiRidwan/n8n-ai-workflow-pack

Feedback welcome — especially if your n8n version differs on a node typeVersion.

---

## 2. agent-orchestrator-lab

### r/LocalLLaMA

**Title:** A minimal, readable LLM agent where a bad tool call is rejected instead of executed

**Body:**

Most "AI agent" repos are a loop around one API call. The parts that decide whether
it survives production are usually missing. This one is built the other way round.

- **Typed tools (Pydantic).** A tool call that doesn't match the schema returns
  `validation_failed` and is **not executed**. An agent that will happily write to
  your DB on a typo isn't an agent.
- **Sensitive actions fail closed.** Tools flagged `sensitive` pause for human
  approval, and with no approver the default is **deny**.
- **Multi-provider with fallback.** One router over OpenAI / Claude / Gemini / Groq;
  a 5xx on one moves to the next. Steps are tiered (plan = strong model, extract =
  cheap).
- **Retries + per-step timeout + error taxonomy** (retryable vs terminal).
- **Every run writes an auditable trace.**

Scored on four real tasks against the GitHub API: **100% pass rate, 100% tool
accuracy, avg 2.5 steps.** The repo has a committed real run trace showing a plan,
typed tool calls, an approval-gated write, and the final answer.

Repo: https://github.com/SandiRidwan/agent-orchestrator-lab

`python eval/run_eval.py` — 4 tasks, scored, no key needed for the offline tests.

---

## 3. sql-analytics-lab + tsql-performance-lab

### r/dataengineering

**Title:** Measured query tuning, with the numbers: pre-aggregation 472x, correlated subquery 56x, covering index 132x

**Body:**

"Query performance improvement" is on nearly every SQL job spec and almost never
demonstrated. I built two labs that show the before/after, with the plans kept.

**sql-analytics-lab** — advanced SQL (CTEs, `LAG`/`RANK`/`ROW_NUMBER`, window
frames, gaps-and-islands, conditional-aggregate pivots, anti-joins) run on
PostgreSQL 18, SQL Server 2017 and DuckDB. Tuning measured on a **PostgreSQL
row-store**:

```
pre-aggregation (join+group by -> mart)     103.98 ms -> 0.22 ms   472x
correlated subquery -> grouped join        8837.30 ms -> 157.69 ms  56x
SARGability (YEAR(col)=n -> range + index)    35.66 ms -> 25.74 ms  1.39x
```

`EXPLAIN (ANALYZE, BUFFERS)` before/after committed — the plan shape changes, not
just the time (Nested Loop per row -> single Hash Join).

Repo: https://github.com/SandiRidwan/sql-analytics-lab

**tsql-performance-lab** — 10 T-SQL tuning cases on **real SQL Server data**
(Morrisons catalogue + Udacity A/B, ~300k rows). Covering index 132x, implicit
nvarchar/varchar fix 17.9x, prefix-vs-wildcard `LIKE` 658x, `NOT IN`->`NOT EXISTS`
2.65x. Slow and tuned queries are **tested to return identical rows** — a speedup
is worthless if the tuned query answers a different question.

Repo: https://github.com/SandiRidwan/tsql-performance-lab

Both run locally, no cloud, no paid services.

---

### Hacker News — Show HN (title format matters)

**Option A (SQL):**
`Show HN: SQL labs with measured query tuning (472x, 56x) and committed plans`
https://github.com/SandiRidwan/sql-analytics-lab

**Option B (RAG):**
`Show HN: Local RAG that refuses to answer when your docs don't cover it`
https://github.com/SandiRidwan/rag-knowledge-service

**First comment (post this immediately, it carries the post):**

I kept hitting the same two things in RAG setups: a vector DB + embedding key just
to ask questions about my own notes, and an answer that sounded confident about
something the docs never said. This runs fully local (BM25, stdlib) and refuses
below a term-coverage threshold instead of guessing. Every answer cites the chunk.
There's a real corpus and an eval included, so it's `clone -> run -> see the
number`. Happy to talk about why coverage beats a score threshold for the refusal.

---

## 4. data-quality-operations + analytics-warehouse

### r/dataengineering

**Title:** DQ checks that distinguish "the source never had it" from "the data is broken"

**Body:**

Two repos from an operational-analyst angle.

**data-quality-operations** — 13 SQL checks (completeness, uniqueness, validity,
referential, freshness, distribution) → PASS/WARN/FAIL with a plain-English root
cause per check, plus a run history and a Streamlit dashboard. Rules live in SQL,
thresholds live in Python, so you change policy without touching queries.

The design point: on **real** Hacker News data, `points` is 100% empty — that's a
**source limitation**, not a pipeline bug. Meanwhile a stale feed is a **real
break**. A DQ system that flags both with the same label trains people to ignore
both. This one tells them apart.

Repo: https://github.com/SandiRidwan/data-quality-operations

**analytics-warehouse** — a star schema with a **type-2 SCD** on real BPS data.
344 dimension rows for 270 regencies (54 changed band), so "what was this
attribute in 2021?" still answers correctly. 10 tests check the integrity that
matters: exactly one current version, no overlapping or gap versions.

Repo: https://github.com/SandiRidwan/analytics-warehouse

---

## 5. LinkedIn (short, professional, one repo at a time)

**RAG post:**

> Most RAG demos have one failure that matters: ask something the documents don't
> cover, and the model invents an answer you don't catch.
>
> I built a small RAG service that does the opposite. It runs with **no API key**
> (local BM25, no vector DB), **cites the exact chunk** for every answer, and
> **refuses** when the corpus doesn't cover the question.
>
> The part I'd highlight: refusal is a *retrieval* decision, not a prompt trick.
> BM25 always returns a best hit, so a score threshold never fires — I use term
> coverage instead.
>
> Real eval included: 7/7 in-corpus answered with the correct source, 3/3
> off-corpus refused.
>
> Code: https://github.com/SandiRidwan/rag-knowledge-service
>
> #RAG #LLM #Python #AIEngineering #Retrieval

**SQL post:**

> "Query performance improvement" is on almost every SQL spec, and almost never
> shown. So I built a lab where it's measured, with plans kept.
>
> On a real PostgreSQL row-store: pre-aggregation 472x, correlated subquery → join
> 56x (8.8s → 0.16s). On real SQL Server data: covering index 132x, implicit
> conversion 17.9x, prefix-vs-wildcard LIKE 658x.
>
> Every case has `EXPLAIN ANALYZE` before/after, and the fast query is tested to
> return the same rows as the slow one — because a speedup means nothing if you
> answer a different question.
>
> https://github.com/SandiRidwan/sql-analytics-lab
> https://github.com/SandiRidwan/tsql-performance-lab
>
> #SQL #PostgreSQL #TSQL #DataEngineering #Performance

---

## Posting checklist (do these before each post)

- [ ] Repo has **topics set** (done for all 7) so GitHub search finds it
- [ ] Repo has a **screenshot / trace** near the top of the README
- [ ] The post includes a **copy-pasteable command or a number** — not just a link
- [ ] You reply to **every comment in the first hour** (this is what drives ranking)
- [ ] Read the subreddit/forum rules first (r/n8n and r/LocalLLaMA allow
      project posts; some subs want a flair like "Show and Tell")
- [ ] Don't cross-post the same text to 5 places in 10 minutes; space them out

## What actually earns stars (honest)

- A **one-command demo** that produces a visible result beats any amount of prose.
- A **screenshot or trace** in the README (people star what they can see working).
- Posting where practitioners are, and answering their questions.
- A repo that **solves a problem they already have** (the RAG one has the highest
  ceiling because "local, no key, refuses to guess" is a real pain).

Stars are a slow compounding effect. One good Hacker News or r/LocalLLaMA post can
outperform months of commits if the repo is genuinely useful.
