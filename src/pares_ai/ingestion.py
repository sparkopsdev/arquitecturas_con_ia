from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

from pypdf import PdfReader

from .db import Database
from .nlp import chunk_text, extract_fact_candidates, extract_title, normalize_text, years_in_text


@dataclass(frozen=True)
class IngestResult:
    document_id: int
    facts_created: int
    chunks_created: int
    title: str


class DocumentIngestor:
    def __init__(self, db: Database):
        self.db = db

    def ingest_path(self, path: Path, source_name: str | None = None) -> IngestResult:
        source_name = source_name or path.name
        text = self._read_path(path)
        return self.ingest_text(source_name=source_name, text=text)

    def ingest_text(self, source_name: str, text: str) -> IngestResult:
        clean_text = normalize_text(text)
        if not clean_text:
            raise ValueError("El documento no contiene texto extraible. En produccion se invocaria OCR/Document Intelligence.")

        content_hash = sha256(clean_text.encode("utf-8")).hexdigest()
        existing = self.db.query_one("SELECT id, title FROM documents WHERE content_hash = ?", (content_hash,))
        if existing:
            return IngestResult(document_id=int(existing["id"]), facts_created=0, chunks_created=0, title=str(existing["title"]))

        title = extract_title(source_name, clean_text)
        years = years_in_text(clean_text)
        year_from = min(years) if years else None
        year_to = max(years) if years else None
        document_id = self.db.insert_document(title, source_name, year_from, year_to, clean_text, content_hash)

        facts = extract_fact_candidates(title, clean_text)
        fact_ids = []
        for fact in facts:
            fact_id = self.db.insert_fact(
                document_id=document_id,
                event_name=fact.event_name,
                date_text=fact.date_text,
                summary=fact.summary,
                people=fact.people,
                places=fact.places,
                ships=fact.ships,
                confidence=fact.confidence,
            )
            fact_ids.append(fact_id)

        chunks = chunk_text(clean_text)
        for index, chunk in enumerate(chunks):
            fact_id = fact_ids[min(index, len(fact_ids) - 1)] if fact_ids else None
            self.db.insert_chunk(document_id, fact_id, chunk)

        return IngestResult(document_id=document_id, facts_created=len(fact_ids), chunks_created=len(chunks), title=title)

    def _read_path(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8")
        if suffix == ".pdf":
            return self._extract_pdf_text(path)
        raise ValueError(f"Formato no soportado para demo local: {suffix}")

    def _extract_pdf_text(self, path: Path) -> str:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n".join(pages)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            raise ValueError("PDF sin capa de texto. Para documentos escaneados reales se requiere OCR.")
        return text


def seed_samples(db: Database, samples_dir: Path) -> list[IngestResult]:
    ingestor = DocumentIngestor(db)
    results: list[IngestResult] = []
    for path in sorted(samples_dir.glob("*.txt")):
        results.append(ingestor.ingest_path(path))
    return results
