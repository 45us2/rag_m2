"""Generate a RAGAS test set from the rules book (many LLM calls: results are saved)."""

import argparse
import json
import random
from pathlib import Path

from langchain_core.documents import Document
from ragas.run_config import RunConfig
from ragas.testset import TestsetGenerator

from rag_m2.chunker.markdown_chunker import chunk_markdown
from rag_m2.evaluations.ragas_adapters import EmbedderRagasEmbeddings, GeminiRagasLLM
from rag_m2.retriever.embedder import Embedder
from rag_m2.settings import DATA, settings


def select_sections(md_path: Path, num_docs: int, min_chars: int, seed: int) -> list[Document]:
    """Regroup chunks by section header and sample sections long enough to ask questions on."""
    sections: dict[str, str] = {}
    for c in chunk_markdown(md_path.read_text(encoding="utf-8")):
        sections[c.header] = sections.get(c.header, "") + "\n" + c.content
    docs = [
        Document(page_content=f"{h}\n{t.strip()}", metadata={"section": h}) for h, t in sections.items() if len(t) >= min_chars
    ]
    random.Random(seed).shuffle(docs)
    return docs[:num_docs]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--markdown_path", type=Path, default=settings.markdown_path)
    p.add_argument("--output", type=Path, default=DATA / "eval" / "testset.jsonl")
    p.add_argument("--size", type=int, default=15)
    p.add_argument("--num_docs", type=int, default=25, help="sections used as source (each costs several LLM calls)")
    p.add_argument("--min_chars", type=int, default=1000)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()

    docs = select_sections(a.markdown_path, a.num_docs, a.min_chars, a.seed)
    print(f"{len(docs)} source sections")
    generator = TestsetGenerator(llm=GeminiRagasLLM(), embedding_model=EmbedderRagasEmbeddings(Embedder()))
    testset = generator.generate_with_langchain_docs(
        docs, testset_size=a.size, run_config=RunConfig(max_workers=2, timeout=600), raise_exceptions=False
    )
    rows = testset.to_pandas().to_dict(orient="records")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in rows), encoding="utf-8")
    print(f"Wrote {len(rows)} samples to {a.output} (review them before evaluating!)")
