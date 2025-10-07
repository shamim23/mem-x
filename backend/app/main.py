from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uvicorn
import argparse


class Visit(BaseModel):
    url: str
    tab_id: Optional[int] = None
    timestamp: Optional[str] = None
    source: Optional[str] = "extension"


app = FastAPI(title="URL Ingestion Service", version="0.1.0")


# CORS: keep permissive for development; tighten as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def healthcheck():
    return {"status": "ok", "service": "url-ingestion"}


@app.post("/ingest")
def ingest_url(visit: Visit):
    # Attach server-side timestamp if not provided
    if not visit.timestamp:
        visit.timestamp = datetime.utcnow().isoformat() + "Z"

    # Minimal acceptance; in real use, enqueue/process/store
    # For now, just acknowledge receipt
    print(visit.url)
    return {"accepted": True, "url": visit.url, "tab_id": visit.tab_id, "timestamp": visit.timestamp}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run URL Ingestion FastAPI app")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (requires import string)")
    args = parser.parse_args()

    if args.reload:
        # Reload requires an import string; run from repo root for this to work
        try:
            uvicorn.run(
                "backend.app.main:app",
                host=args.host,
                port=args.port,
                reload=True,
            )
        except Exception as e:
            print("[url-ingestion] Reload failed; starting without reload. Reason:", e)
            uvicorn.run(app, host=args.host, port=args.port, reload=False)
    else:
        uvicorn.run(app, host=args.host, port=args.port, reload=False)
