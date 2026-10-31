"""Adapters so RAGAS uses our own Gemini client (rate-limited) and SBERT embedder."""

import asyncio

from langchain_core.outputs import Generation, LLMResult
from ragas.embeddings import BaseRagasEmbeddings
from ragas.llms import BaseRagasLLM
from ragas.run_config import RunConfig

from rag_m2.llm.gemini import generate
from rag_m2.retriever.embedder import Embedder


class GeminiRagasLLM(BaseRagasLLM):
    def __init__(self) -> None:
        super().__init__(run_config=RunConfig())

    def generate_text(self, prompt, n=1, temperature=0.01, stop=None, callbacks=None) -> LLMResult:
        text = generate(prompt.to_string())
        return LLMResult(generations=[[Generation(text=text) for _ in range(n)]])

    async def agenerate_text(self, prompt, n=1, temperature=0.01, stop=None, callbacks=None) -> LLMResult:
        return await asyncio.to_thread(self.generate_text, prompt, n)

    def is_finished(self, response: LLMResult) -> bool:
        return True


class EmbedderRagasEmbeddings(BaseRagasEmbeddings):
    def __init__(self, embedder: Embedder) -> None:
        super().__init__()
        self.run_config = RunConfig()
        self.embedder = embedder

    def embed_query(self, text: str) -> list[float]:
        return self.embedder.embed_query(text).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(texts).tolist()

    async def aembed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self.embed_query, text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_documents, texts)
