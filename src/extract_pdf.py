from __future__ import annotations

from dataclasses import dataclass
from pypdf import PdfReader


@dataclass
class ExtractedDoc:
    raw_text: str
    num_pages: int
    is_text_pdf: bool


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> ExtractedDoc:
    """
    V0: extraction texte d'un PDF "texte".
    (On ajoutera OCR + fallback plus tard pour les PDF scannés.)
    """
    reader = PdfReader(_bytes_to_filelike(pdf_bytes))

    texts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        texts.append(t)

    raw_text = "\n".join(texts).strip()
    is_text_pdf = len(raw_text) > 200  # heuristique simple

    return ExtractedDoc(
        raw_text=raw_text,
        num_pages=len(reader.pages),
        is_text_pdf=is_text_pdf,
    )


def _bytes_to_filelike(b: bytes):
    import io
    return io.BytesIO(b)
