from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .audit import AuditService
from .auth import Principal, create_token, current_principal, require_admin
from .config import Settings, get_settings
from .db import Database
from .ingestion import DocumentIngestor, seed_samples
from .models import HealthResponse, IngestResponse, LoginRequest, LoginResponse, QueryRequest, QueryResponse, SearchResponseItem, SourceSnippet
from .nlp import select_relevant_sentences
from .pdf_export import PdfExporter
from .search import TfidfSearchEngine


settings = get_settings()
db = Database(settings.database_path)
app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def startup() -> None:
    db.init_schema()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (static_dir / "index.html").read_text(encoding="utf-8")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, environment=settings.app_env)


@app.post("/api/auth/demo-login", response_model=LoginResponse)
def demo_login(payload: LoginRequest) -> LoginResponse:
    username = payload.username or ("admin@pares" if payload.role == "admin" else "user@pares")
    token = create_token(username=username, role=payload.role, settings=settings)
    db.add_audit(username, payload.role, "auth.demo_login", {"role": payload.role})
    return LoginResponse(access_token=token, role=payload.role, username=username)


@app.post("/api/admin/ingest/samples", response_model=list[IngestResponse])
def ingest_samples(principal: Annotated[Principal, Depends(require_admin)]) -> list[IngestResponse]:
    samples_dir = settings.data_dir / "samples"
    if not samples_dir.exists():
        raise HTTPException(status_code=404, detail="No existe data/samples")
    results = seed_samples(db, samples_dir)
    AuditService(db).record(principal, "ingest.samples", {"count": len(results)})
    return [
        IngestResponse(
            document_id=item.document_id,
            facts_created=item.facts_created,
            chunks_created=item.chunks_created,
            title=item.title,
        )
        for item in results
    ]


@app.post("/api/admin/documents", response_model=IngestResponse)
async def upload_document(
    principal: Annotated[Principal, Depends(require_admin)],
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
) -> IngestResponse:
    suffix = Path(file.filename or "upload.txt").suffix or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        result = DocumentIngestor(db).ingest_path(tmp_path, source_name=title or file.filename or tmp_path.name)
    finally:
        tmp_path.unlink(missing_ok=True)
    AuditService(db).record(principal, "ingest.upload", {"filename": file.filename, "document_id": result.document_id})
    return IngestResponse(
        document_id=result.document_id,
        facts_created=result.facts_created,
        chunks_created=result.chunks_created,
        title=result.title,
    )


def _parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return []


@app.get("/api/facts", response_model=list[SearchResponseItem])
def list_facts(principal: Annotated[Principal, Depends(current_principal)]) -> list[SearchResponseItem]:
    rows = db.query_all(
        """
        SELECT f.id AS fact_id, f.event_name, f.date_text, f.summary, f.people, f.places, f.ships, f.confidence,
               d.id AS document_id, d.title AS document_title
        FROM facts f
        JOIN documents d ON d.id = f.document_id
        ORDER BY f.id DESC
        LIMIT 100
        """
    )
    AuditService(db).record(principal, "facts.list", {"count": len(rows)})
    return [
        SearchResponseItem(
            fact_id=int(row["fact_id"]),
            event_name=row["event_name"],
            date_text=row["date_text"] or "",
            summary=row["summary"],
            document_id=int(row["document_id"]),
            document_title=row["document_title"],
            people=_parse_list(row["people"]),
            places=_parse_list(row["places"]),
            ships=_parse_list(row["ships"]),
            confidence=float(row["confidence"]),
        )
        for row in rows
    ]


@app.get("/api/search", response_model=list[SearchResponseItem])
def search_facts(
    principal: Annotated[Principal, Depends(current_principal)],
    q: str = Query(..., min_length=1),
) -> list[SearchResponseItem]:
    pattern = f"%{q}%"
    rows = db.query_all(
        """
        SELECT f.id AS fact_id, f.event_name, f.date_text, f.summary, f.people, f.places, f.ships, f.confidence,
               d.id AS document_id, d.title AS document_title
        FROM facts f
        JOIN documents d ON d.id = f.document_id
        WHERE f.event_name LIKE ? OR f.summary LIKE ? OR f.people LIKE ? OR f.places LIKE ? OR f.ships LIKE ?
        ORDER BY f.confidence DESC, f.id DESC
        LIMIT 50
        """,
        (pattern, pattern, pattern, pattern, pattern),
    )
    AuditService(db).record(principal, "facts.search", {"q": q, "count": len(rows)})
    return [
        SearchResponseItem(
            fact_id=int(row["fact_id"]),
            event_name=row["event_name"],
            date_text=row["date_text"] or "",
            summary=row["summary"],
            document_id=int(row["document_id"]),
            document_title=row["document_title"],
            people=_parse_list(row["people"]),
            places=_parse_list(row["places"]),
            ships=_parse_list(row["ships"]),
            confidence=float(row["confidence"]),
        )
        for row in rows
    ]


def build_answer(question: str, snippets: list[SourceSnippet]) -> str:
    if not snippets:
        return "No he encontrado evidencias suficientes en los documentos indexados. Carga o ingiere mas documentos y vuelve a intentarlo."
    relevant = select_relevant_sentences(question, [snippet.text for snippet in snippets])
    if not relevant:
        relevant = [snippet.text[:350] for snippet in snippets[:3]]
    bullet_lines = [f"- {sentence}" for sentence in relevant]
    sources_line = "; ".join({f"{s.document_title} (doc {s.document_id})" for s in snippets[:5]})
    return (
        "Respuesta generada a partir de los fragmentos recuperados:\n"
        + "\n".join(bullet_lines)
        + "\n\n"
        + f"Fuentes utilizadas: {sources_line}."
        + "\n\nNota: en el prototipo local se usa recuperacion TF-IDF y resumen extractivo. En la arquitectura productiva se conectaria un LLM con RAG, citas y controles de calidad."
    )


@app.post("/api/query")
def natural_language_query(
    principal: Annotated[Principal, Depends(current_principal)],
    payload: QueryRequest,
):
    search_engine = TfidfSearchEngine(db)
    results = search_engine.search(payload.question, top_k=payload.top_k)
    snippets = [
        SourceSnippet(
            document_id=item.document_id,
            document_title=item.document_title,
            chunk_id=item.chunk_id,
            score=item.score,
            text=item.text,
        )
        for item in results
    ]
    answer = build_answer(payload.question, snippets)
    AuditService(db).record(principal, "query.ask", {"question": payload.question, "sources": len(snippets), "format": payload.output_format})

    if payload.output_format == "pdf":
        pdf_bytes = PdfExporter().build_answer_pdf(
            title="Respuesta PARES AI RAG",
            question=payload.question,
            answer=answer,
            sources=[snippet.model_dump() for snippet in snippets],
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=respuesta-pares-ai.pdf"},
        )

    return QueryResponse(question=payload.question, answer=answer, sources=snippets)


@app.get("/api/admin/audit")
def audit_logs(principal: Annotated[Principal, Depends(require_admin)]):
    rows = db.query_all("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
    AuditService(db).record(principal, "audit.list", {"count": len(rows)})
    return rows


@app.get("/api/admin/model-control")
def model_control(principal: Annotated[Principal, Depends(require_admin)]):
    AuditService(db).record(principal, "model_control.read", {})
    return {
        "pipeline": [
            "ingesta documental",
            "extraccion OCR o texto",
            "normalizacion",
            "extraccion de metadatos",
            "chunking",
            "indexacion",
            "recuperacion RAG",
            "generacion de respuesta",
            "evaluacion y auditoria",
        ],
        "calibration_controls": [
            "muestras doradas validadas por archivistas",
            "revision de OCR en baja confianza",
            "umbral minimo de confianza de entidades",
            "evaluacion periodica de precision y cobertura",
            "trazabilidad de prompt, fragmentos fuente y version de modelo",
        ],
        "local_demo": {
            "retrieval": "TF-IDF",
            "generation": "extractive_summary",
            "idp": "demo_token",
        },
    }
