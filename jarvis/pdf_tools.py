from pathlib import Path
from pypdf import PdfReader


def extract_pdf_text(path: str) -> str:
    pdf_path = Path(path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    reader = PdfReader(str(pdf_path))
    content = []
    for page in reader.pages:
        content.append(page.extract_text() or "")
    return "\n".join(content).strip()
