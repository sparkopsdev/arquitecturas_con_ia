from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from typing import Any

from .db import Database
from .nlp import tokenize


@dataclass(frozen=True)
class SearchResult:
    document_id: int
    document_title: str
    chunk_id: int
    score: float
    text: str


class TfidfSearchEngine:
    def __init__(self, db: Database):
        self.db = db

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        rows = self.db.query_all(
            """
            SELECT c.id AS chunk_id,
                   c.document_id AS document_id,
                   c.text AS text,
                   d.title AS document_title
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            ORDER BY c.id ASC
            """
        )
        if not rows:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        doc_tokens = [tokenize(row["text"]) for row in rows]
        df: Counter[str] = Counter()
        for tokens in doc_tokens:
            for token in set(tokens):
                df[token] += 1
        n_docs = len(rows)

        def vector(tokens: list[str]) -> dict[str, float]:
            counts = Counter(tokens)
            total = sum(counts.values()) or 1
            vec: dict[str, float] = {}
            for token, count in counts.items():
                tf = count / total
                idf = math.log((1 + n_docs) / (1 + df.get(token, 0))) + 1
                vec[token] = tf * idf
            return vec

        q_vec = vector(query_tokens)
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        scored: list[tuple[float, dict[str, Any]]] = []
        for row, tokens in zip(rows, doc_tokens):
            c_vec = vector(tokens)
            c_norm = math.sqrt(sum(v * v for v in c_vec.values())) or 1.0
            dot = sum(q_vec.get(token, 0.0) * c_vec.get(token, 0.0) for token in q_vec)
            score = dot / (q_norm * c_norm)
            if query.lower() in row["text"].lower():
                score += 0.2
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            SearchResult(
                document_id=int(row["document_id"]),
                document_title=str(row["document_title"]),
                chunk_id=int(row["chunk_id"]),
                score=round(float(score), 4),
                text=str(row["text"]),
            )
            for score, row in scored[:top_k]
        ]
