import asyncio
import json
import os
import queue
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import pipeline
from models import (
    ApproveCategorizationRequest,
    ApproveEntitiesRequest,
    ApproveKeywordsRequest,
    StartRunRequest,
)

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

USPTO_API_KEY = os.environ.get("USPTO_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

app = FastAPI(title="Patent Search")


def _require_keys() -> None:
    missing = [
        name for name, value in [("USPTO_API_KEY", USPTO_API_KEY), ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)]
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing environment variable(s): {', '.join(missing)}. Set them in webapp/.env.",
        )


@app.post("/api/runs")
def start_run(body: StartRunRequest):
    _require_keys()
    run = pipeline.create_run(body.company, body.subject, USPTO_API_KEY)
    return {"run_id": run.run_id, "candidate_entities": run.candidate_entities}


@app.post("/api/runs/{run_id}/entities")
def approve_entities(run_id: str, body: ApproveEntitiesRequest):
    _require_keys()
    run = pipeline.approve_entities(run_id, body.approved)
    return {"candidate_keywords": run.candidate_keywords}


@app.post("/api/runs/{run_id}/keywords")
def approve_keywords(run_id: str, body: ApproveKeywordsRequest):
    _require_keys()
    pipeline.approve_keywords(run_id, body.approved, USPTO_API_KEY)
    return {"status": "started"}


@app.post("/api/runs/{run_id}/categorization")
def approve_categorization(run_id: str, body: ApproveCategorizationRequest):
    pipeline.approve_categorization(run_id, body.categories, body.assignments)
    return {"status": "generating_report"}


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str):
    q = pipeline.get_events(run_id)

    async def stream():
        while True:
            try:
                event = await asyncio.to_thread(q.get, True, 15)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue
            yield f"data: {json.dumps(event)}\n\n"
            if event["type"] in ("report_ready", "error"):
                break

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/runs/{run_id}/download/{kind}")
def download(run_id: str, kind: str):
    run = pipeline.get_run(run_id)
    filenames = {
        "csv": f"{_slug_base(run)}-patents.csv",
        "report_md": f"{_slug_base(run)}-report.md",
        "report_html": f"{_slug_base(run)}-report.html",
    }
    if kind not in filenames:
        raise HTTPException(status_code=404, detail="Unknown file kind")
    path = run.output_dir / filenames[kind]
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not ready")
    return FileResponse(path, filename=path.name)


def _slug_base(run) -> str:
    return f"{pipeline.slug(run.company)}-{pipeline.slug(run.subject)}"


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
