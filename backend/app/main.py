from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uvicorn
import argparse
import os
import sys
from pathlib import Path
from agents import Agent, Runner, function_tool, trace
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

load_dotenv(override=True)

@function_tool
def extract_webpage(url: str) -> str:
    """Extract text content from a webpage URL.

    Args:
        url: The URL of the webpage to extract content from

    Returns:
        JSON string with extracted content including title and text
    """
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        title = soup.title.string if soup.title else url
        text = soup.get_text(separator='\n', strip=True)

        return json.dumps({
            'success': True,
            'url': url,
            'title': title,
            'text_preview': text[:2000],
            'full_text': text[:8000]  # Limit to 8k chars
        })
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})


@function_tool
def extract_youtube(url: str) -> str:
    """Extract transcript from a YouTube video URL.

    Args:
        url: The YouTube video URL

    Returns:
        JSON string with extracted transcript
    """
    try:
        print(f"[EXTRACT_YOUTUBE] Processing URL: {url}")

        # Extract video ID
        video_id_match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11}).*', url)
        if not video_id_match:
            error_msg = 'Invalid YouTube URL format'
            print(f"[EXTRACT_YOUTUBE] ERROR: {error_msg}")
            return json.dumps({'success': False, 'error': error_msg})

        video_id = video_id_match.group(1)
        print(f"[EXTRACT_YOUTUBE] Extracted video ID: {video_id}")

        # Try to get transcript using the new API
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=['en'])
        print(f"[EXTRACT_YOUTUBE] Successfully retrieved transcript")

        # Combine transcript text - use .text attribute instead of dictionary access
        full_text = ' '.join([snippet.text for snippet in transcript])
        title = f"YouTube Video: {video_id}"

        print(f"[EXTRACT_YOUTUBE] Full text length: {len(full_text)} characters")

        return json.dumps({
            'success': True,
            'url': url,
            'video_id': video_id,
            'title': title,
            'text_preview': full_text[:2000],
            'full_text': full_text[:8000]
        })
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[EXTRACT_YOUTUBE] ERROR: {error_msg}")
        return json.dumps({'success': False, 'error': error_msg})

# ============================================================================
# 5. Define Agents
# ============================================================================

# Content Extraction Agent
extractor_agent = Agent(
    name="Content Extractor",
    instructions="""You MUST extract content from web pages and YouTube videos using the provided tools.

    For EVERY URL you receive:
    1. Check if the URL contains 'youtube.com' or 'youtu.be' - if YES, use extract_youtube tool
    2. For all other URLs - use extract_webpage tool
    3. ALWAYS call the appropriate tool - do not respond without calling a tool
    4. Return the exact JSON result from the tool

    You must call one of the extraction tools for every request.
    """,
    tools=[extract_webpage, extract_youtube],
    model="gpt-4o-mini"
)

# Synthesis Agent
synthesis_agent = Agent(
    name="Content Analyzer",
    instructions="""You analyze learning content and extract key insights.
    For each piece of content:
    1. Read the content text from the extraction result
    2. Extract 5-10 key points (important takeaways)
    3. Identify main concepts (technical terms, frameworks, ideas)
    4. Write a concise 2-3 sentence summary
    5. Return the analysis in a structured format
    """,
    tools=[],
    model="gpt-4o-mini"
)

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
async def ingest_url(visit: Visit):
    # Attach server-side timestamp if not provided
    if not visit.timestamp:
        visit.timestamp = datetime.utcnow().isoformat() + "Z"

    print(f"\n{'='*60}")
    print(f"[INGEST] Processing URL: {visit.url}")
    print(f"[INGEST] Tab ID: {visit.tab_id}, Timestamp: {visit.timestamp}")

    # Process with extractor agent
    try:
        print(f"[INGEST] Starting extractor agent...")
        extraction_result = await Runner.run(
            starting_agent=extractor_agent,
            input=f"Extract content from this URL: {visit.url}"
        )

        print(f"[INGEST] Extraction completed successfully")
        print(f"[INGEST] Extraction Result: {extraction_result.final_output}")

        # Parse the extraction result to get the content
        try:
            extraction_data = json.loads(extraction_result.final_output)
            content_text = extraction_data.get('full_text', extraction_data.get('text_preview', ''))
        except:
            content_text = str(extraction_result.final_output)

        # Run synthesis agent to analyze and summarize
        print(f"[INGEST] Starting synthesis agent...")
        synthesis_result = await Runner.run(
            starting_agent=synthesis_agent,
            input=f"Analyze this content and provide key points, concepts, and summary:\n\n{content_text}"
        )

        print(f"[INGEST] Synthesis completed successfully")
        print(f"[INGEST] Summary: {synthesis_result.final_output}")
        print(f"{'='*60}\n")

        return {
            "accepted": True,
            "url": visit.url,
            "tab_id": visit.tab_id,
            "timestamp": visit.timestamp,
            "extraction": extraction_result.final_output,
            "analysis": synthesis_result.final_output
        }
    except Exception as e:
        print(f"[INGEST] ERROR: {str(e)}")
        print(f"{'='*60}\n")
        return {
            "accepted": True,
            "url": visit.url,
            "tab_id": visit.tab_id,
            "timestamp": visit.timestamp,
            "error": f"processing_error: {str(e)}"
        }

@app.get("/records")
def list_records(limit: int = 20):
    """Return recent stored content records from JSONL storage.

    Params:
    - limit: number of most recent records to return (default 20).
    """
    if JSONLStorage is None or agent_settings is None:
        return {"error": "agents storage not available"}
    try:
        storage = JSONLStorage(agent_settings.storage_path)
        items = list(storage.read_all())
        if limit and limit > 0:
            items = items[-limit:]
        # Return newest first
        return [rec.model_dump(mode="json") for rec in reversed(items)]
    except Exception as e:
        return {"error": f"read_error: {e}"}

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
