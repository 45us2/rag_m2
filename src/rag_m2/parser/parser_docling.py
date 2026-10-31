import warnings
from pathlib import Path

from docling.document_converter import DocumentConverter

warnings.filterwarnings(
    "ignore",
    message="Using padding='same' with even kernel lengths",
    category=UserWarning,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "Core Rules.pdf"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "core_rules.md"


def parse_document(document_path: str | Path) -> str:
    """Convert a document to Markdown using Docling."""
    document_path = Path(document_path)
    if not document_path.is_file():
        raise FileNotFoundError(f"Input document not found: {document_path}")

    print(f"Loading {document_path}...", flush=True)
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import PdfFormatOption

    pipeline_options = PdfPipelineOptions(do_ocr=False)
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )
    print("Converting document without OCR...", flush=True)
    result = converter.convert(str(document_path))
    print("Exporting Markdown...", flush=True)
    return result.document.export_to_markdown()


def parse_to_file(
    document_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Parse a document and write its Markdown representation to a file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(parse_document(document_path), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    try:
        output = parse_to_file()
    except Exception as error:
        print(f"Parsing failed: {error}", flush=True)
        raise
    print(f"Parsed document written to {output}", flush=True)
