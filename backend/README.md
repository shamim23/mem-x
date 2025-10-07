URL Ingestion Backend (FastAPI)

Quick start

- Create a virtualenv and install deps:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r backend/requirements.txt`
- Run the server:
  - Easiest (no reload): `python backend/app/main.py`
  - With reload (from repo root): `python backend/app/main.py --reload`
  - Alternatively (CLI): `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`
- Test endpoints:
  - Health: `curl http://localhost:8000/` -> `{ "status": "ok" }`
  - Ingest: `curl -X POST http://localhost:8000/ingest -H 'Content-Type: application/json' -d '{"url": "https://example.com"}'`

Notes

- CORS is open for local development. Restrict origins in production.
- The `/ingest` endpoint accepts `{ url, tab_id?, timestamp?, source? }` and echoes back an acknowledgement.
- Extend this service later to queue/process/store URLs per your pipeline.
