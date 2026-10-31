"""SQLite store: dense vectors (numpy cosine) + FTS5 (BM25), fused with RRF."""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from rag_m2.chunker.markdown_chunker import Chunk

STOPWORDS = set(
    "a an and are as at be by can do does for from how i if in is it of on or that the this to what when which who with you your warhammer 40 000 40k core rules rule".split()
)


@dataclass
class SearchResult:
    chunk: Chunk
    score: float


class SqliteStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY, header TEXT, content TEXT, vec BLOB)")
        self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(header, content, tokenize='porter')")
        self._load()

    def _load(self) -> None:
        rows = self.db.execute("SELECT id, header, content, vec FROM chunks ORDER BY id").fetchall()
        self.ids = [r[0] for r in rows]
        self.chunks = {r[0]: Chunk(r[1], r[2]) for r in rows}
        self.matrix = np.vstack([np.frombuffer(r[3], dtype=np.float32) for r in rows]) if rows else None

    def reset(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        self.db.execute("DELETE FROM chunks")
        self.db.execute("DELETE FROM fts")
        for i, (c, v) in enumerate(zip(chunks, vectors, strict=True)):
            self.db.execute("INSERT INTO chunks VALUES (?,?,?,?)", (i, c.header, c.content, v.astype(np.float32).tobytes()))
            self.db.execute("INSERT INTO fts(rowid, header, content) VALUES (?,?,?)", (i, c.header, c.content))
        self.db.commit()
        self._load()

    def dense(self, qvec: np.ndarray, k: int) -> list[int]:
        scores = self.matrix @ qvec.astype(np.float32)
        return [self.ids[i] for i in np.argsort(-scores)[:k]]

    def lexical(self, query: str, k: int) -> list[int]:
        terms = [t for t in re.findall(r"\w+", query.lower()) if t not in STOPWORDS]
        if not terms:
            return []
        q = " OR ".join(f'"{t}"' for t in terms)
        return [r[0] for r in self.db.execute("SELECT rowid FROM fts WHERE fts MATCH ? ORDER BY rank LIMIT ?", (q, k))]

    def search(self, query: str, qvec: np.ndarray, k: int = 5, rrf_k: int = 60) -> list[SearchResult]:
        """Hybrid search: reciprocal rank fusion of dense and BM25 rankings."""
        if self.matrix is None:
            raise RuntimeError("Empty vector store: run `make index` first")
        fused: dict[int, float] = {}
        for ranking in (self.dense(qvec, 4 * k), self.lexical(query, 4 * k)):
            for rank, cid in enumerate(ranking):
                fused[cid] = fused.get(cid, 0.0) + 1 / (rrf_k + rank + 1)
        best = sorted(fused.items(), key=lambda x: -x[1])[:k]
        return [SearchResult(self.chunks[cid], s) for cid, s in best]

    def close(self) -> None:
        self.db.close()
