# DESIGN — Patent Search Web App

## Architecture Overview

```
┌─────────────────────────┐        HTTP/JSON + SSE        ┌──────────────────────────────────┐
│  Browser (frontend/)     │ ─────────────────────────────▶ │  FastAPI backend (backend/)       │
│  index.html + app.js     │ ◀───────────────────────────── │  localhost:8000                   │
│  (vanilla JS, no build)  │        EventSource stream       │                                    │
└─────────────────────────┘                                 │  ┌──────────────────────────────┐  │
                                                              │  │ pipeline.py                    │  │
                                                              │  │ RunState + worker thread       │  │
                                                              │  │ per run_id (in-memory)         │  │
                                                              │  └──────────────┬─────────────────┘  │
                                                              │                 │                     │
                                                              │  ┌──────────────▼───────────┐         │
                                                              │  │ scripts_bridge.py         │         │
                                                              │  │ imports (unmodified):     │         │
                                                              │  │  fetch_patents.py         │─────────┼──▶ USPTO ODP API
                                                              │  │  fetch_metadata.py        │─────────┼──▶ USPTO ODP API
                                                              │  │  fetch_abstracts.py       │─────────┼──▶ Google Patents
                                                              │  └───────────────────────────┘         │
                                                              │                                        │
                                                              │  ┌───────────────────────────┐         │
                                                              │  │ llm.py                     │─────────┼──▶ Anthropic API
                                                              │  │ keywords / relevance+       │         │   (claude-opus-5,
                                                              │  │ summary / categorize /      │         │    web_search +
                                                              │  │ narrative report            │         │    web_fetch tools)
                                                              │  └───────────────────────────┘         │
                                                              └──────────────────────────────────┘
                                                                          │
                                                                          ▼
                                                          data/[company]-[subject]-{patents.csv,report.md,report.html}
                                                          (written to a run-scoped temp dir; downloaded via the browser)
```

The web app is a second interface onto the same underlying logic the CLI scripts and the `/patent-search` skill already use — it does not replace either (PRD FR-13). `scripts_bridge.py` imports the three root-level scripts as Python modules and calls their existing, already-decomposed functions (`fetch_applications`, `fetch_metadata`, `fetch_abstract`) directly. The web app needs no edits to them; all ODP requests go through the shared, rate-limited `odp_client.py`.

## Key Components

| Component | Path | Responsibility |
|---|---|---|
| FastAPI app | `webapp/backend/app.py` | Routes, static file serving, SSE endpoint, wires everything together |
| Pipeline orchestrator | `webapp/backend/pipeline.py` | `RunState` model, stage transitions, background worker thread per run, progress queue |
| Script bridge | `webapp/backend/scripts_bridge.py` | Adds the repo root to `sys.path` and re-exports `fetch_applications`, `fetch_metadata`, `fetch_abstract`, `MAX_RESULTS` from the root scripts; its own entity lookup calls ODP through `odp_client` |
| LLM layer | `webapp/backend/llm.py` | All Anthropic API calls: keyword generation, per-patent relevance+summary, categorization, narrative report (with web search/fetch) |
| Request/response & LLM schemas | `webapp/backend/models.py` | Pydantic models for API payloads and for structured LLM outputs (`KeywordList`, `PatentJudgment`, `Categorization`) |
| Frontend | `webapp/frontend/index.html`, `app.js`, `style.css` | Wizard UI: form → entity approval → keyword approval → progress view → categorization review → downloads. Plain JS, `fetch()` + `EventSource`, no build step |

## Data Model

In-memory only (`dict[run_id, RunState]` inside `pipeline.py`) — no database, matching the "ephemeral, no persisted history" requirement (PRD NFR).

```python
class Stage(str, Enum):
    ENTITY_DISCOVERY = "entity_discovery"
    AWAITING_ENTITY_APPROVAL = "awaiting_entity_approval"
    KEYWORD_GENERATION = "keyword_generation"
    AWAITING_KEYWORD_APPROVAL = "awaiting_keyword_approval"
    FETCHING = "fetching"                    # patents -> metadata -> abstracts
    FILTERING_SUMMARIZING = "filtering_summarizing"
    AWAITING_CATEGORIZATION_APPROVAL = "awaiting_categorization_approval"
    GENERATING_REPORT = "generating_report"
    DONE = "done"
    ERROR = "error"

class PatentRecord(BaseModel):
    application_number: str
    patent_number: str | None
    title: str
    inventors: list[str]
    year: str
    status: str                # "Issued" | "Published Application"
    abstract: str | None
    relevant: bool | None      # set during FILTERING_SUMMARIZING
    summary: str | None
    categories: list[str] = []

class RunState(BaseModel):
    run_id: str
    company: str
    subject: str
    stage: Stage
    candidate_entities: list[str] = []
    approved_entities: list[str] = []
    candidate_keywords: list[str] = []
    approved_keywords: list[str] = []
    patents: list[PatentRecord] = []
    proposed_categories: list[str] = []
    output_dir: Path            # tempfile.mkdtemp(), one per run
    error: str | None = None
```

Progress ticks are pushed onto a `queue.Queue` per run (not stored on `RunState`) and drained by the SSE endpoint as `{"stage": ..., "current": N, "total": M, "message": "..."}` events.

## API / Interface Design

| Method & Path | Body | Response | Notes |
|---|---|---|---|
| `POST /api/runs` | `{company, subject}` | `{run_id, candidate_entities}` | Runs USPTO entity discovery synchronously (fast — a couple of small queries) |
| `POST /api/runs/{id}/entities` | `{approved: [str]}` | `{candidate_keywords}` | Calls `llm.propose_keywords` |
| `POST /api/runs/{id}/keywords` | `{approved: [str]}` | `{status: "started"}` | Starts the background worker thread (fetch → filter → summarize) |
| `GET /api/runs/{id}/events` | — | SSE stream | `progress` events during FETCHING/FILTERING_SUMMARIZING; ends in a `categorization_ready` event (proposed categories + per-patent assignment) or an `error` event |
| `POST /api/runs/{id}/categorization` | `{categories: [str], assignments: {app_number: [str]}}` | `{status: "generating_report"}` | User-edited categorization; triggers `llm.generate_report` in the same worker thread. SSE continues, ending in a `report_ready` event |
| `GET /api/runs/{id}/download/{kind}` | — | file | `kind` ∈ `csv`, `report_md`, `report_html` — served from the run's temp dir |

The wizard is entirely driven by SSE events after keyword approval — the frontend doesn't poll.

## External Dependencies

| Dependency | Purpose |
|---|---|
| `fastapi`, `uvicorn` | HTTP server, routing, SSE (`StreamingResponse`) |
| `anthropic` (Python SDK) | All LLM calls |
| `pydantic` | Request/response and structured-output schemas (ships with FastAPI) |
| `python-dotenv` | Loads `USPTO_API_KEY` / `ANTHROPIC_API_KEY` from the repo-root `.env` at startup — the same file the CLI scripts use (see root README) |
| Root `fetch_patents.py` / `fetch_metadata.py` / `fetch_abstracts.py` | Imported as-is — USPTO ODP API + Google Patents scraping (stdlib `urllib`, no new dependency) |
| Root `odp_client.py` | Shared rate-limited ODP access; all ODP calls from the scripts and the web app go through it (stdlib only) |
| `~/.claude/skills/annotate-html/assets/{annotate.css,annotate.js}` | Read at report-generation time and inlined into `report.html`, same as the CLI skill does, to keep the HTML report annotatable |

No frontend build tooling (no npm, no bundler) — the frontend is three static files served directly by FastAPI's `StaticFiles`.

## Key Design Decisions

**Reuse by direct import, zero script edits (FR-13).** All three root scripts already separate their core logic (`fetch_applications`, `fetch_metadata`, `fetch_abstract`) from their `argparse`-based `main()`. `scripts_bridge.py` inserts the repo root onto `sys.path` and imports those functions directly — no refactor of the scripts for the web app's sake. (The scripts were later changed to route ODP requests through the shared `odp_client.py` for rate-limit compliance; their flags and output formats are unchanged.) Alternative considered: turning the repo root into an installable package (`pyproject.toml`, `src/` layout). Rejected as unnecessary restructuring for a single local tool, and it would touch files the CLI depends on.

**One exception to "the scripts print progress":** `fetch_applications()` calls `sys.exit()` when a query exceeds the 500-result cap — correct for a CLI process, but fatal if left uncaught inside a long-running server. The pipeline worker wraps the call in `try/except SystemExit` and turns it into a normal `error` SSE event. This is a caller-side catch, not a script edit — the script's own behavior when run from the terminal is untouched.

**Background execution on a worker thread, not `async`.** The reused functions do blocking I/O (`urllib.request`, `time.sleep`) synchronously. Running them inside an `async def` route would stall the FastAPI event loop for the whole multi-minute pipeline. Each run gets a dedicated `threading.Thread`; progress crosses the thread boundary via a `queue.Queue` that the SSE route drains.

**Progress granularity follows what the scripts already expose.** `fetch_metadata()` and `fetch_abstract()` are single-item functions — the pipeline calls them in an explicit loop (mirroring what each script's own `main()` does, including the same inter-request delays) and emits one progress tick per item. `fetch_applications()` is a single bulk call with no per-page hook, so the patent-discovery stage is reported as one coarse step rather than granular progress. Getting finer-grained progress there would require editing `fetch_patents.py`, which FR-13 rules out.

**ODP rate limits are enforced in the shared client, not the pipeline (PRD NFR).** ODP blocks concurrent requests with the same API key, and each run executes in its own worker thread, so two overlapping runs would otherwise send parallel requests. Every ODP call (via the root scripts and `scripts_bridge.discover_entities`) goes through root `odp_client.py`, which holds a machine-wide lock per request, spaces requests at least 0.3s apart and retries 429s with backoff. Overlapping runs, and runs alongside the CLI, therefore take turns automatically. The pipeline's earlier per-call 429 retry loops were removed to avoid double backoff; the per-item error fallback remains. The root scripts were changed only to route requests through the client, so their flags and output formats are unchanged (FR-13), though requests are now paced.

**Model: `claude-opus-5` for every judgment step.** Volume is modest — dozens of short calls per run (a few hundred tokens each for relevance/summary; one larger call for the narrative report) — so even at Opus pricing ($5/$25 per MTok) a full run costs well under $1. No reason to trade quality for savings at this scale. The relevance-filter and summary steps are combined into a single structured call per patent (`{relevant: bool, summary: str}`) to halve the per-patent call count, issued concurrently through `AsyncAnthropic` with a bounded semaphore (5 in flight) to keep wall-clock time reasonable without hammering rate limits. The Message Batches API (50% cheaper) was considered and rejected — it's asynchronous on Anthropic's own schedule, which conflicts with the live-progress requirement (PRD NFR).

**Structured outputs for anything the pipeline needs to parse.** Keyword generation and categorization use `client.messages.parse()` with Pydantic models (`KeywordList`, `Categorization`) so the backend never regex-parses free text. The per-patent relevance+summary call uses the same pattern (`PatentJudgment`). The narrative report itself is prose/Markdown, not JSON, so it's a plain `messages.create()` call.

**`web_search` + `web_fetch` server tools for inventor enrichment.** The narrative report's "Key inventors" section (SKILL.md Step 8, Section 3) requires looking up each multi-patent inventor's LinkedIn profile — open-ended, variable-length research that's a good fit for the Tool Runner (`client.beta.messages.tool_runner`) rather than backend-orchestrated search calls: Claude runs its own search → fetch → summarize loop per inventor within one agentic call, using `web_search_20260209` and `web_fetch_20260209` (current tool versions, no beta header). This is the one step in the pipeline expected to take noticeably longer than the others; the UI's progress event for `GENERATING_REPORT` says so explicitly rather than showing a fixed count.

**SSE, not WebSockets.** Progress only flows server → client, and there's at most one in-flight pipeline per run. A `StreamingResponse` with `text/event-stream` is simpler than a WebSocket for a one-directional stream and needs no extra dependency.

## Development Setup

```bash
cd webapp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# .env lives at the repo root (../.env from here) — shared with the CLI scripts,
# see the root README's "Web app" section. Fill in USPTO_API_KEY and ANTHROPIC_API_KEY there.

uvicorn app:app --app-dir backend --reload --port 8000
# open http://localhost:8000
```

`requirements.txt`: `fastapi`, `uvicorn[standard]`, `anthropic`, `python-dotenv`, `markdown`.

The existing CLI workflow (`python3 fetch_patents.py ...`, `/patent-search` in Claude Code) continues to work exactly as before — nothing in this setup touches the repo root.
