# Usage: make help
RUN := uv run
Q ?= Which Aeldari units have toughness 4?
SIZE ?= 10

.DEFAULT_GOAL := help
.PHONY: help install parse index pipeline search ask-sql chat smoke gen-testset eval eval-fast lint test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install dependencies (with eval + dev groups)
	uv sync --all-groups

parse: ## 1. PDF -> markdown with Docling (slow, output already in the repo)
	$(RUN) python -m rag_m2.scripts.parse

index: ## 2. Chunk, embed and store the markdown -> data/vectors.db
	$(RUN) python -m rag_m2.scripts.index

pipeline: parse index ## Parse then index

search: ## Show retrieved chunks for Q (no LLM)
	$(RUN) python -m rag_m2.scripts.search "$(Q)"

ask-sql: ## Try the text-to-SQL retriever alone on Q
	$(RUN) python -m rag_m2.scripts.ask_sql "$(Q)"

chat: ## Multi-turn chat
	$(RUN) python -m rag_m2.scripts.chat

smoke: ## Fixed conversations + routing check -> data/chat_logs/smoke_test.md
	$(RUN) python -m rag_m2.scripts.smoke_test

gen-testset: ## Generate the RAGAS test set (SIZE=10)
	$(RUN) --group eval python -m rag_m2.scripts.generate_testset --size $(SIZE) --num_docs $(SIZE)

eval: ## Agent answers (checkpointed) + RAGAS metrics, rules channel only
	$(RUN) --group eval python -m rag_m2.scripts.eval_retrieval --no_sql

eval-fast: ## Only the fuzzy context hit rate (cheap)
	$(RUN) --group eval python -m rag_m2.scripts.eval_retrieval --no_sql --skip_ragas

lint: ## Ruff
	$(RUN) ruff check --fix src tests && $(RUN) ruff format src tests

test: ## Unit tests (no API key needed)
	$(RUN) pytest -q