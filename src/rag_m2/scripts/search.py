"""Debug: show the chunks retrieved for a query (no LLM call)."""

import sys

from rag_m2.retriever.embedder import Embedder
from rag_m2.settings import settings
from rag_m2.storage.vector_store import SqliteStore

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "What is a Lone Operative?"
    store = SqliteStore(settings.vector_db)
    for r in store.search(query, Embedder().embed_query(query), k=settings.top_k):
        print(f"--- {r.score:.4f} | {r.chunk.header}\n{r.chunk.content[:300]}\n")
