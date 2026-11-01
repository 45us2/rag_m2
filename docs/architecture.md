# Architecture and design choices

This document explains how the assistant works and why it was built this way. For setup and commands, see the [README](../README.md).

## 1. Overview

The assistant answers Warhammer 40,000 questions from two **channels**:

| Channel | Source | Good for | Retrieval |
|---|---|---|---|
| Text | *Core Rules* PDF | how the game works: phases, movement, shooting, charges, core abilities, keywords | hybrid search over chunks |
| SQL | `wahadb.sqlite` (21 tables) | army data: units, stats, weapons, points, stratagems, detachments | text-to-SQL |

```
user message + history
        │
        ▼
   ┌─────────┐   route = rules ──► hybrid search (vectors + BM25) ──┐
   │ router  │   route = sql   ──► text-to-SQL on wahadb.sqlite ─────┼──► answer (grounded, with sources)
   │  (LLM)  │   route = both  ──► both, in parallel ────────────────┤
   └─────────┘   route = none  ──► (small talk, no retrieval) ───────┘
```

The two channels are complementary: the rules book never lists unit stats, and the database never explains how a rule works. A question like *"Does Eldrad Ulthran have Lone Operative, and what does it do?"* needs both.

## 2. Parsing (`parser/`)

Two parsers were compared on the rules book:

- **pypdf** (`parser_pypdf.py`): fast and light, but it only extracts raw text page by page. Headings, lists and the two-column layout are lost, so chunks cannot follow the structure of the rules.
- **Docling** (`parser_docling.py`, used): layout analysis, exports Markdown with headings and lists. OCR is disabled because the PDF has a text layer (much faster).

Known issues of the Docling output (`data/processed/core_rules.md`):

- All headings come out at the same level (`##`), so the hierarchy (e.g. *Shooting phase → Making attacks → 1. Hit roll*) is flattened. This is handled at chunking time.
- The first summary pages, laid out in many columns, are partly interleaved. They have little rules content, so they were left as is.

Since parsing is slow, the parsed Markdown is committed to the repo.

## 3. Chunking (`chunker/markdown_chunker.py`)

1. **Cleaning**: remove `<!-- image -->` placeholders, normalise bullets and whitespace.
2. **Header split** (LangChain `MarkdownHeaderTextSplitter`): one section per heading, the heading being kept as metadata.
3. **Merge of small sections**: because of the flattened headings, many sections are tiny (a title like `1. HIT ROLL` followed by one sentence). A section shorter than 300 characters is merged with the next one, and both headings are kept (`ATTACHED UNITS | DESTROYED`).
4. **Recursive split** (`RecursiveCharacterTextSplitter`, 1000 characters, overlap 150) for long sections.

The heading is prepended to each chunk before embedding (`Chunk.text`), so a chunk about *Lone Operative* contains that name even if the body does not repeat it.

Result: **224 chunks**, about 650 characters on average.

## 4. Indexing and retrieval (`retriever/embedder.py`, `storage/vector_store.py`)

- **Embeddings**: `BAAI/bge-small-en-v1.5` (sentence-transformers, normalised vectors, with the bge query prefix). It is small, runs on CPU and is strong for English retrieval.
- **Storage**: one SQLite file (`data/vectors.db`) holds the chunks, their vectors (as BLOBs) and an **FTS5** full-text index (BM25, Porter stemming). With only 224 chunks, exact cosine search with numpy is instant, so no ANN library is needed.
- **Hybrid search**: dense search and BM25 each return 4×k candidates, merged with **Reciprocal Rank Fusion** (RRF, k = 60).
  - Dense search handles paraphrases and informal wording (RAGAS questions with typos or slang).
  - BM25 handles exact game terms that embeddings blur (*Lone Operative*, *Feel No Pain*, *Battle-shock*).
- Generic words (*warhammer*, *40k*, *core*, *rules* plus usual stopwords) are ignored by BM25: the smoke test showed that a query rewritten as *"... in the Warhammer 40,000 core rules"* pulled the book's introduction instead of the charge rules.

## 5. Text-to-SQL (`retriever/sql_retriever.py`)

- **Prompt**: the full data dictionary (`SQL_AGENT_DATA_DICTIONARY.md`) and rules learned from testing:
  - `SELECT DISTINCT`, because many rows are duplicated across sources (the same Land Raider cost line appears several times).
  - `LIKE '%...%'` on names (all columns are TEXT, names have variants).
  - Where abilities are stored: core/faction abilities (*Lone Operative*, *Leader*) through `abilityId → abilities.name`, unit-specific ones in `datasheets_abilities.name`.
  - To check if a unit has something, list what it has instead of filtering (an empty result is ambiguous).
- **Safety**: the database is opened **read-only** (`mode=ro`), and only a single `SELECT`/`WITH` statement is accepted.
- **Self-correction**: if the query fails or returns no rows, the error is sent back to the LLM, which tries again (2 retries).
- **Cleaning of results**: HTML tags removed, mojibake fixed (`Tâ€™au` → `T’au`), at most 30 rows, long cells truncated.

## 6. Agent and conversation (`chat/agent.py`)

The agent is a **LangGraph** graph: `router → (rules | sql | both | none) → answer`.

- **Router** (one LLM call, JSON output): picks the route and **rewrites the last message as a standalone question** from the conversation (*"and what is their toughness?"* → *"What is the toughness of a Hellblaster Squad?"*). This rewritten question is what both retrievers receive. If the JSON is invalid, it falls back to the rules route.
- **Parallel retrieval**: with `both`, the two retrieval nodes run in the same step and the answer node waits for both.
- **Answer**: grounded prompt (context only, say "I don't know" otherwise, keep exact numbers, cite sources). The last messages of the conversation are included.
- **Memory**: a `MemorySaver` checkpointer stores the state per `thread_id`. `/reset` in the chat just starts a new thread.

## 7. LLM client (`llm/gemini.py`)

- Gemini through `google-genai`, model set in `.env` (`LLM_MODEL`), API key never committed.
- **Rate limiter** (thread-safe, 10 requests/min by default) for the free tier.
- **Retries** with backoff on 429/500/503 errors.
- **JSON retries**: `flash-lite` sometimes returns empty or truncated JSON (especially for multi-line SQL), so the call is repeated up to 2 times; if it still fails, the SQL channel returns an error message instead of crashing the conversation.

## 8. Evaluation

Three levels, from cheapest to most expensive:

1. **Unit tests** (`tests/`, no API key): chunk merging, SQL safety, routing and memory with a fake LLM.
2. **Smoke test** (`scripts/smoke_test.py`): 13 fixed questions (rules, SQL, mixed, a 3-turn conversation, small talk), checks the route and saves the answers for manual review. Final run: **13/13 routes**, all answers correct.
3. **RAGAS** (`scripts/generate_testset.py`, `scripts/eval_retrieval.py`): synthetic questions generated from the rules book, then Faithfulness, Factual correctness, Context precision, Context recall, plus `context_hit`, a fuzzy match without LLM. Results and their interpretation are in the README.

The smoke test drove most of the fixes listed above:

| Problem seen | Cause | Fix |
|---|---|---|
| *Time to Strike* description cut | SQL cells truncated at 400 chars | limit raised to 2000 |
| Missing Land Raider variants | duplicate rows filled the 30-row limit | `SELECT DISTINCT` |
| "I don't know" for Eldrad's abilities | core abilities stored in another table | ability storage explained in the SQL prompt |
| Mixed question routed to SQL only | unclear definition of `both` | routing examples in the router prompt |
| Crash `Expecting value` | empty JSON from Gemini | JSON retries + SQL error isolated |
| "I don't know" on charge after Advance | query rewriting added generic words | rewriting kept short + BM25 stopwords |

## 9. Limitations and future work

- **Multi-hop questions** were the weak point: with 5 chunks, retrieval often covered only one of the two rules involved. Raising k to 8 brought context recall from 0.78 to 0.95 (see README results), but precision stays low. Next options: a cross-encoder reranker, or one search per sub-question.
- **The SQL channel is not evaluated by RAGAS** (the test set comes from the rules book only); a small hand-written set of SQL questions with expected answers would be needed.
- **Memory is in RAM**: the conversation is lost when the chat closes (a `SqliteSaver` checkpointer would persist it).
- **Free tier**: the rate limit makes the evaluation slow (about 30 to 60 minutes) and limits the size of the test set.
- **One LLM call decides everything**: a wrong route means a wrong answer; `both` could be used as a safer default for ambiguous questions.
