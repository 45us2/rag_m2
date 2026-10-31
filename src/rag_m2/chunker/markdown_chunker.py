"""Header-aware chunking of the Docling markdown."""

import re
from dataclasses import dataclass

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from rag_m2.settings import settings


@dataclass
class Chunk:
    header: str
    content: str

    @property
    def text(self) -> str:
        """Text that is embedded / shown to the LLM."""
        return f"{self.header}\n{self.content}" if self.header else self.content


def clean(md: str) -> str:
    md = md.replace("<!-- image -->", "").replace("■", "-")
    md = re.sub(r"[ \t]+", " ", md)
    return re.sub(r"\n{3,}", "\n\n", md)


def chunk_markdown(md: str) -> list[Chunk]:
    headers = [("#", "h1"), ("##", "h2"), ("###", "h3")]
    sections = MarkdownHeaderTextSplitter(headers, strip_headers=True).split_text(clean(md))

    # Docling flattens headers (all "##"), so tiny sections like "1. HIT ROLL" are merged forward.
    merged: list[Chunk] = []
    for s in sections:
        header = " > ".join(s.metadata.values())
        body = s.page_content.strip()
        if merged and len(merged[-1].content) < settings.chunk_min_size:
            prev = merged[-1]
            merged[-1] = Chunk(f"{prev.header} | {header}", f"{prev.content}\n\n## {header}\n{body}".strip())
        else:
            merged.append(Chunk(header, body))

    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    return [Chunk(c.header, part) for c in merged for part in splitter.split_text(c.content) if part.strip()]
