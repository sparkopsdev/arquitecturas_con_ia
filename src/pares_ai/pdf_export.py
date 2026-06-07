from __future__ import annotations

from io import BytesIO
from textwrap import wrap

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


class PdfExporter:
    def build_answer_pdf(self, title: str, question: str, answer: str, sources: list[dict]) -> bytes:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin = 2 * cm
        y = height - margin

        def new_page() -> None:
            nonlocal y
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = height - margin

        def line(text: str = "", size: int = 10, leading: int = 14) -> None:
            nonlocal y
            if y < margin:
                new_page()
            pdf.setFont("Helvetica", size)
            pdf.drawString(margin, y, text[:115])
            y -= leading

        def paragraph(text: str, size: int = 10, leading: int = 14, chars: int = 95) -> None:
            for raw_line in text.split("\n"):
                for part in wrap(raw_line, chars) or [""]:
                    line(part, size=size, leading=leading)

        line(title, size=16, leading=22)
        line("Consulta", size=12, leading=18)
        paragraph(question)
        line()
        line("Respuesta", size=12, leading=18)
        paragraph(answer)
        line()
        line("Fuentes consultadas", size=12, leading=18)
        for source in sources:
            source_title = source.get("document_title", "Documento")
            chunk_id = source.get("chunk_id", "-")
            score = source.get("score", 0)
            paragraph(f"- {source_title} / fragmento {chunk_id} / score {score}", size=9, chars=100)
        pdf.save()
        return buffer.getvalue()
