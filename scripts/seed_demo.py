from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pares_ai.config import get_settings
from pares_ai.db import Database
from pares_ai.ingestion import seed_samples


if __name__ == "__main__":
    settings = get_settings()
    db = Database(settings.database_path)
    db.init_schema()
    results = seed_samples(db, settings.data_dir / "samples")
    for result in results:
        print(f"Documento {result.document_id}: {result.title} ({result.facts_created} hechos, {result.chunks_created} chunks)")
