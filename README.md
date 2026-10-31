# Warhammer 40,000 RAG assistant

Multi-turn chatbot answering Warhammer 40,000 questions from two channels:

- **Text**: the *Core Rules* PDF, parsed with Docling (`data/processed/core_rules.md`, tracked in the repo), chunked and indexed in SQLite (dense vectors + FTS5/BM25, fused with RRF).
- **SQL**: the game database `wahadb.sqlite` (units, stats, weapons, stratagems…), queried by text-to-SQL.

```
question + history ─> router (LLM) ──┬─> hybrid search (Core Rules chunks) ─┐
   (rewrites a standalone question)   └─> text-to-SQL (wahadb.sqlite) ───────┴─> answer (LLM, grounded + sources)
```

The agent is a LangGraph graph (`src/rag_m2/chat/agent.py`) with a `MemorySaver` checkpointer: each conversation is a `thread_id`, so follow-up questions ("and what is its toughness?") are resolved by the router.

## Setup

```bash
uv sync --all-groups
echo "GOOGLE_API_KEY=..." > .env      # Google AI Studio key, never committed
```

Optional `.env` overrides: `LLM_MODEL` (default `gemini-3.5-flash-lite`), `LLM_REQUESTS_PER_MINUTE` (default 10, free tier), `EMBEDDING_MODEL` (default `BAAI/bge-small-en-v1.5`), `TOP_K`.

Put `Core Rules.pdf` and `wahadb.sqlite` + `SQL_AGENT_DATA_DICTIONARY.md` in `data/raw/`.

## Usage

With `make` (`make help`) or directly with `uv run python -m ...`:

| Step | make | command |
|---|---|---|
| 1. Parse PDF → markdown (slow, already done) | `make parse` | `uv run python -m rag_m2.scripts.parse` |
| 2. Chunk + embed + store | `make index` | `uv run python -m rag_m2.scripts.index` |
| Debug retrieval (no LLM) | `make search Q="..."` | `uv run python -m rag_m2.scripts.search "What is Lone Operative?"` |
| Debug text-to-SQL | `make ask-sql Q="..."` | `uv run python -m rag_m2.scripts.ask_sql "Which Aeldari units have toughness 4?"` |
| **Chat** | `make chat` | `uv run python -m rag_m2.scripts.chat` |
| Generate RAGAS test set | `make gen-testset SIZE=15` | `uv run --group eval python -m rag_m2.scripts.generate_testset --size 15` |
| Evaluate (RAGAS) | `make eval` | `uv run --group eval python -m rag_m2.scripts.eval_retrieval --no_sql` |
| Tests (offline) | `make test` | `uv run pytest -q` |

Chat commands: `/reset` (new conversation), `/trace` (show route, SQL and sources), `/exit`.

## Evaluation

- `generate_testset` samples sections of the rules book and lets RAGAS generate single-hop / multi-hop questions → `data/eval/testset.jsonl` (review it by hand).
- `eval_retrieval` runs the agent on each question (answers are checkpointed in `data/eval_checkpoints/` so a crash/rate limit does not lose work), then computes RAGAS `Faithfulness`, `FactualCorrectness`, `LLMContextPrecisionWithReference`, `LLMContextRecall`, plus a cheap LLM-free `context_hit` (fuzzy match of reference contexts in retrieved chunks) → `data/eval/results.csv`.
- RAGAS uses the project's own rate-limited Gemini client and embedder through adapters (`src/rag_m2/evaluations/ragas_adapters.py`).
- `smoke_test` runs a fixed list of conversations (rules, SQL, mixed, multi-turn, small talk) and checks the routing → `data/chat_logs/smoke_test.md` (13/13 routes correct).

### Results (rules channel, `gemini-3.5-flash-lite`, 12 RAGAS questions, top-k = 5)

| Questions | Faithfulness | Factual correctness | Context precision | Context recall | Context hit |
|---|---:|---:|---:|---:|---:|
| Single-hop (4) | 1.00 | 0.86 | 0.88 | 1.00 | 0.50 |
| Multi-hop (8) | 0.94 | 0.45 | 0.18 | 0.68 | 0.52 |
| **All (12)** | **0.96** | **0.59** | **0.41** | **0.78** | **0.51** |

- **The agent does not hallucinate** (faithfulness 0.96): answers stick to the retrieved chunks, and it says "I don't know" when the context is missing.
- **Single-hop questions are almost perfect.** Scores drop on multi-hop questions, which combine two unrelated rules: with 5 chunks, retrieval often finds only one side and adds off-topic chunks (low context precision).
- Part of the drop comes from the synthetic test set: one multi-hop question is incoherent (the agent correctly answered "I don't know", scored 0), and three are near-duplicates.
- `context_hit` (fuzzy string match) is stricter than RAGAS's LLM-judged recall.

## Layout

```
src/rag_m2/
  settings.py                # pydantic-settings singleton (.env)
  parser/                    # Docling (used) and pypdf (baseline) parsers
  chunker/markdown_chunker.py# header split + merge of tiny sections + recursive split
  retriever/embedder.py      # sentence-transformers
  retriever/sql_retriever.py # text-to-SQL, read-only, SELECT only, self-correction on error/empty result
  storage/vector_store.py    # SQLite: vectors + FTS5, hybrid RRF search
  llm/gemini.py              # google-genai client, rate limiter, retries on 429/503
  chat/agent.py              # LangGraph router agent with memory
  evaluations/ragas_adapters.py
  scripts/                   # entry points
```
