# Usage: make help
RUN := uv run
Q ?= Which Aeldari units have toughness 4?
SIZE ?= 10

.DEFAULT_GOAL := help
.PHONY: help install hooks parse index pipeline search ask-sql chat tui smoke gen-testset eval eval-fast eval-sql lint test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install dependencies (with eval + dev groups) and git hooks
	uv sync --all-groups
	$(RUN) pre-commit install

hooks: ## Run the git hooks (ruff) on all files
	$(RUN) pre-commit run --all-files

parse: ## 1. PDF -> markdown with Docling (slow, output already in the repo)
	$(RUN) python -m rag_m2.scripts.parse

index: ## 2. Chunk, embed and store the markdown -> data/vectors.db
	$(RUN) python -m rag_m2.scripts.index

pipeline: parse index ## Parse then index

search: ## Show retrieved chunks for Q (no LLM)
	$(RUN) python -m rag_m2.scripts.search "$(Q)"

ask-sql: ## Try the text-to-SQL retriever alone on Q
	$(RUN) python -m rag_m2.scripts.ask_sql "$(Q)"

chat: ## Multi-turn chat (terminal)
	$(RUN) python -m rag_m2.scripts.chat

tui: ## Multi-turn chat (Textual interface, with trace panel)
	$(RUN) python -m rag_m2.scripts.tui

smoke: ## Fixed conversations + routing check -> data/chat_logs/smoke_test.md
	$(RUN) python -m rag_m2.scripts.smoke_test

gen-testset: ## Generate the RAGAS test set (SIZE=10)
	$(RUN) --group eval python -m rag_m2.scripts.generate_testset --size $(SIZE) --num_docs $(SIZE)

eval: ## Agent answers (checkpointed) + RAGAS metrics, rules channel only
	$(RUN) --group eval python -m rag_m2.scripts.eval_retrieval --no_sql

eval-fast: ## Only the fuzzy context hit rate (cheap)
	$(RUN) --group eval python -m rag_m2.scripts.eval_retrieval --no_sql --skip_ragas

eval-sql: ## SQL channel: hand-written questions with checked answers -> data/eval/sql_results.csv
	$(RUN) python -m rag_m2.scripts.eval_sql

lint: ## Ruff
	$(RUN) ruff check --fix src tests && $(RUN) ruff format src tests

test: ## Unit tests (no API key needed)
	$(RUN) pytest -q