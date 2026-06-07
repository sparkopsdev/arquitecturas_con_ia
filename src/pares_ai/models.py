from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


Role = Literal["admin", "user"]


class LoginRequest(BaseModel):
    role: Role = "user"
    username: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    username: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    output_format: Literal["text", "pdf"] = "text"
    top_k: int = Field(default=5, ge=1, le=12)


class SourceSnippet(BaseModel):
    document_id: int
    document_title: str
    chunk_id: int
    score: float
    text: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceSnippet]


class SearchResponseItem(BaseModel):
    fact_id: int
    event_name: str
    date_text: str
    summary: str
    document_id: int
    document_title: str
    people: list[str]
    places: list[str]
    ships: list[str]
    confidence: float


class IngestResponse(BaseModel):
    document_id: int
    facts_created: int
    chunks_created: int
    title: str


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
