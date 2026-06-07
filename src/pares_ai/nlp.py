from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


YEAR_RE = re.compile(r"\b(15\d{2}|1600)\b")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+")

KNOWN_PLACES = [
    "San Miguel",
    "Isla Terceira",
    "Azores",
    "Lisboa",
    "Sevilla",
    "Cadiz",
    "Madrid",
    "PARES",
    "Archivo General de Indias",
]

SHIP_HINTS = ["nao", "nave", "galeon", "galeón", "urca", "carabela", "patache", "capitana", "almiranta"]

STOPWORDS = {
    "a",
    "al",
    "ante",
    "bajo",
    "con",
    "contra",
    "de",
    "del",
    "desde",
    "durante",
    "e",
    "el",
    "ella",
    "en",
    "entre",
    "es",
    "esa",
    "ese",
    "esta",
    "este",
    "fue",
    "ha",
    "la",
    "las",
    "lo",
    "los",
    "mas",
    "más",
    "no",
    "o",
    "para",
    "por",
    "que",
    "se",
    "si",
    "sin",
    "sobre",
    "son",
    "su",
    "sus",
    "un",
    "una",
    "unas",
    "unos",
    "y",
}


@dataclass(frozen=True)
class FactCandidate:
    event_name: str
    date_text: str
    summary: str
    people: list[str]
    places: list[str]
    ships: list[str]
    confidence: float


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in WORD_RE.findall(text) if t.lower() not in STOPWORDS and len(t) > 1]


def years_in_text(text: str) -> list[int]:
    return sorted({int(match.group(1)) for match in YEAR_RE.finditer(text)})


def split_sentences(text: str) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    sentences = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        sentences.extend([s.strip() for s in SENTENCE_RE.split(paragraph) if s.strip()])
    return sentences


def first_sentences(text: str, max_sentences: int = 3) -> str:
    sentences = split_sentences(text)
    return " ".join(sentences[:max_sentences]) if sentences else text[:500]


def extract_title(source_name: str, text: str) -> str:
    for line in normalize_text(text).split("\n"):
        candidate = line.strip(" #:-")
        if 5 <= len(candidate) <= 120:
            return candidate
    return source_name.rsplit(".", 1)[0]


def extract_places(text: str) -> list[str]:
    found = []
    lowered = text.lower()
    for place in KNOWN_PLACES:
        if place.lower() in lowered:
            found.append(place)
    return sorted(set(found))


def extract_people(text: str) -> list[str]:
    patterns = [
        r"(?:capit[aá]n(?: de mar| de guerra)?|maestre de campo|almirante|general)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s+(?:de|del|y|[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)){1,5})",
        r"Don\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s+(?:de|del|y|[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)){1,5})",
    ]
    people: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = re.sub(r"\s+", " ", match.group(1)).strip(" .,;:")
            if 3 < len(value) < 80:
                people.add(value)
    return sorted(people)


def extract_ships(text: str) -> list[str]:
    ships: set[str] = set()
    for hint in SHIP_HINTS:
        pattern = rf"{hint}\s+(?:llamada\s+|nombrada\s+|de\s+)?([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s+(?:de|del|la|las|los|y|Santa|San|Nuestra|Señora|[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)){{0,6}})"
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = re.sub(r"\s+", " ", match.group(1)).strip(" .,;:")
            value = re.sub(r"\bcon\b.*$", "", value, flags=re.IGNORECASE).strip(" .,;:")
            if 2 < len(value) < 90:
                ships.add(value)
    quoted = re.findall(r"[\"“”']([^\"“”']{3,80})[\"“”']", text)
    for value in quoted:
        if any(word in value.lower() for word in ["santa", "san", "trinidad", "mar", "victoria"]):
            ships.add(value.strip())
    return sorted(ships)


def chunk_text(text: str, max_chars: int = 950, overlap: int = 120) -> list[str]:
    clean = normalize_text(text)
    if len(clean) <= max_chars:
        return [clean] if clean else []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        if end < len(clean):
            pivot = clean.rfind(". ", start, end)
            if pivot > start + 300:
                end = pivot + 1
        chunks.append(clean[start:end].strip())
        if end >= len(clean):
            break
        start = max(0, end - overlap)
    return [chunk for chunk in chunks if chunk]


def infer_event_name(title: str, text: str) -> str:
    title = title.strip()
    if title:
        return title[:120]
    sentences = split_sentences(text)
    if sentences:
        return sentences[0][:120]
    return "Hecho documental sin titulo"


def extract_fact_candidates(title: str, text: str) -> list[FactCandidate]:
    clean = normalize_text(text)
    years = years_in_text(clean)
    date_text = ", ".join(str(year) for year in years) if years else "Fecha no identificada"
    places = extract_places(clean)
    people = extract_people(clean)
    ships = extract_ships(clean)
    summary = first_sentences(clean, max_sentences=3)
    confidence = 0.5
    confidence += 0.1 if years else 0
    confidence += 0.1 if places else 0
    confidence += 0.1 if people else 0
    confidence += 0.1 if ships else 0
    confidence = min(confidence, 0.9)
    return [
        FactCandidate(
            event_name=infer_event_name(title, clean),
            date_text=date_text,
            summary=summary,
            people=people,
            places=places,
            ships=ships,
            confidence=round(confidence, 2),
        )
    ]


def select_relevant_sentences(question: str, texts: Iterable[str], max_sentences: int = 6) -> list[str]:
    question_tokens = set(tokenize(question))
    scored: list[tuple[float, str]] = []
    for text in texts:
        for sentence in split_sentences(text):
            tokens = set(tokenize(sentence))
            if not tokens:
                continue
            overlap = question_tokens.intersection(tokens)
            score = len(overlap) / (len(question_tokens) or 1)
            if any(word in sentence.lower() for word in ["capitana", "almiranta", "capitan", "capitán", "nave", "galeon", "galeón"]):
                score += 0.1
            if score > 0:
                scored.append((score, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected: list[str] = []
    seen = set()
    for _, sentence in scored:
        key = sentence.lower()
        if key in seen:
            continue
        selected.append(sentence)
        seen.add(key)
        if len(selected) >= max_sentences:
            break
    return selected
