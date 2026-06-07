.PHONY: run test seed clean

run:
	PYTHONPATH=src uvicorn pares_ai.main:app --reload --host 0.0.0.0 --port 8000

test:
	PYTHONPATH=src pytest -q

seed:
	PYTHONPATH=src python scripts/seed_demo.py

clean:
	rm -f runtime/*.sqlite3 runtime/pdf/*.pdf
