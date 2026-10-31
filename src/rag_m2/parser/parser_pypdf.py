from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "Core Rules.pdf"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "core_rules_pypdf.md"


def parse_document(document_path: str | Path) -> str:
    """Extract PDF text as lightweight Markdown without OCR or PyTorch."""
    document_path = Path(document_path)
    if not document_path.is_file():
        raise FileNotFoundError(f"Input document not found: {document_path}")

    reader = PdfReader(str(document_path))
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"## Page {page_number}\n\n{text}")

    return "\n\n".join(pages) + "\n"


def parse_to_file(
    document_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Extract a PDF and write its text as Markdown."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(parse_document(document_path), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    output = parse_to_file()
    print(f"Parsed document written to {output}", flush=True)