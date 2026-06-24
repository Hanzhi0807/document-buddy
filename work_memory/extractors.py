from __future__ import annotations

import io
from html.parser import HTMLParser
from pathlib import Path


class _PlainHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".log"}:
        return data.decode("utf-8", errors="replace")
    if suffix in {".html", ".htm"}:
        parser = _PlainHTMLParser()
        parser.feed(data.decode("utf-8", errors="replace"))
        return parser.text()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception as exc:  # pragma: no cover - optional parser
            return f"[PDF text extraction failed: {exc}]"
    if suffix == ".docx":
        try:
            from docx import Document

            doc = Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:  # pragma: no cover - optional parser
            return f"[DOCX text extraction failed: {exc}]"
    return data.decode("utf-8", errors="replace")
