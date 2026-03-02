from dataclasses import dataclass
from pypdf import PdfReader
import io


@dataclass
class ExtractedDoc:
    raw_text: str
    num_pages: int
    is_text_pdf: bool


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> ExtractedDoc:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    texts = []

    for page in reader.pages:
        t = page.extract_text() or ""
        texts.append(t)

    raw_text = "\n".join(texts).strip()
    is_text_pdf = len(raw_text) > 200

    return ExtractedDoc(
        raw_text=raw_text,
        num_pages=len(reader.pages),
        is_text_pdf=is_text_pdf
    )
