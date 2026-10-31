"""SentenceTransformer wrapper returning normalized numpy vectors."""

import numpy as np
from sentence_transformers import SentenceTransformer

from rag_m2.settings import settings

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "  # bge models


class Embedder:
    def __init__(self, model: str = settings.embedding_model) -> None:
        self.model = SentenceTransformer(model)
        self.prefix = QUERY_PREFIX if "bge" in model.lower() else ""
        self.dimension = self.model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=len(texts) > 64)

    def embed_query(self, text: str) -> np.ndarray:
        return self.model.encode(self.prefix + text, normalize_embeddings=True)
