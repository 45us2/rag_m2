"""2. Clean + chunk the markdown, embed and store it (rebuilds the store)."""

import argparse
from pathlib import Path

from rag_m2.chunker.markdown_chunker import chunk_markdown
from rag_m2.retriever.embedder import Embedder
from rag_m2.settings import settings
from rag_m2.storage.vector_store import SqliteStore

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--markdown_path", type=Path, default=settings.markdown_path)
    p.add_argument("--db_path", type=Path, default=settings.vector_db)
    a = p.parse_args()

    chunks = chunk_markdown(a.markdown_path.read_text(encoding="utf-8"))
    sizes = [len(c.text) for c in chunks]
    print(f"{len(chunks)} chunks (min {min(sizes)}, mean {sum(sizes) // len(sizes)}, max {max(sizes)} chars)")
    vectors = Embedder().embed_documents([c.text for c in chunks])
    store = SqliteStore(a.db_path)
    store.reset(chunks, vectors)
    store.close()
    print(f"Indexed into {a.db_path}")
