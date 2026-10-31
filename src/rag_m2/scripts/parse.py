"""1. PDF -> markdown with Docling."""

import argparse
from pathlib import Path

from rag_m2.parser.parser_docling import parse_to_file
from rag_m2.settings import settings

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pdf_path", type=Path, default=settings.pdf_path)
    p.add_argument("--target_markdown", type=Path, default=settings.markdown_path)
    a = p.parse_args()
    print(f"Written {parse_to_file(a.pdf_path, a.target_markdown)}")
