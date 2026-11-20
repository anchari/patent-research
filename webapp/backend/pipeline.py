import asyncio
import csv
import queue
import re
import tempfile
import threading
import uuid
from pathlib import Path

import llm
import scripts_bridge
from models import PatentRecord, RunState, Stage

RUNS: dict[str, RunState] = {}
EVENTS: dict[str, "queue.Queue[dict]"] = {}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _fetch_metadata_with_retry(app_number: str, api_key: str) -> dict:
    """
    Wraps the bare fetch_metadata() with a per-item error fallback, so one failed
    application doesn't abort the whole run (mirrors fetch_metadata.py's CLI tolerance
    for per-item failures). Pacing, the one-request-at-a-time rule and 429 backoff are
    handled inside odp_client, which every ODP call goes through.
    """
    try:
        return scripts_bridge.fetch_metadata(app_number, api_key)
    except Exception as e:  # noqa: BLE001 - one bad item shouldn't abort the run
        return {"applicationNumberText": app_number, "error": str(e)}


def _lookup_categories(record: PatentRecord, assignments: dict[str, list[str]]) -> list[str]:
    """categorize()'s prompt asks the LLM to key `assignments` by application_number, but model
    output isn't guaranteed to honor that — fall back to patent_number (and a digits-only
    normalization of either) rather than silently dropping every assignment on a key mismatch."""
    for key in (record.application_number, record.patent_number):
        if key and key in assignments:
            return assignments[key]
    normalized = {re.sub(r"\D", "", k): v for k, v in assignments.items()}
    for key in (record.application_number, record.patent_number):
        digits = re.sub(r"\D", "", key) if key else ""
        if digits and digits in normalized:
            return normalized[digits]
    return []


def _fetch_applications_with_retry(entity: str, api_key: str, keywords: list[str]) -> list[dict]:
    """Thin wrapper kept for call-site stability: 429 backoff now lives in odp_client.
    SystemExit (the intentional 500-result cap signal) and other errors propagate."""
    return scripts_bridge.fetch_applications(entity, api_key, keywords)


def _emit(run_id: str, event: dict) -> None:
    EVENTS[run_id].put(event)


def create_run(company: str, subject: str, uspto_api_key: str) -> RunState:
    run_id = uuid.uuid4().hex
    output_dir = Path(tempfile.mkdtemp(prefix=f"patent-search-{run_id}-"))
    run = RunState(
        run_id=run_id,
        company=company,
        subject=subject,
        stage=Stage.ENTITY_DISCOVERY,
        output_dir=output_dir,
    )
    RUNS[run_id] = run
    EVENTS[run_id] = queue.Queue()

    run.candidate_entities = scripts_bridge.discover_entities(company, uspto_api_key)
    run.stage = Stage.AWAITING_ENTITY_APPROVAL
    return run


def approve_entities(run_id: str, approved: list[str]) -> RunState:
    run = RUNS[run_id]
    run.approved_entities = approved
    run.stage = Stage.KEYWORD_GENERATION
    run.candidate_keywords = llm.propose_keywords(run.company, run.subject)
    run.stage = Stage.AWAITING_KEYWORD_APPROVAL
    return run


def approve_keywords(run_id: str, approved: list[str], uspto_api_key: str) -> RunState:
    run = RUNS[run_id]
    run.approved_keywords = approved
    run.stage = Stage.FETCHING
    thread = threading.Thread(target=_run_fetch_and_judge, args=(run_id, uspto_api_key), daemon=True)
    thread.start()
    return run


def _run_fetch_and_judge(run_id: str, uspto_api_key: str) -> None:
    run = RUNS[run_id]
    try:
        app_numbers: list[str] = []
        for entity in run.approved_entities:
            # Mirror SKILL.md Step 3: fetch everything for the entity first, and only
            # narrow by title keywords if the unfiltered portfolio exceeds the hard cap.
            # Keywords are an approximate narrowing tool, not a relevance filter (that's
            # the abstract-based judgment step below) — applying them unconditionally
            # can zero out a query when the LLM's terms don't appear verbatim in titles.
            _emit(run_id, {"type": "progress", "stage": "fetching", "message": f"Searching patents for {entity}..."})
            try:
                items = _fetch_applications_with_retry(entity, uspto_api_key, [])
            except SystemExit:
                _emit(run_id, {"type": "progress", "stage": "fetching",
                                "message": f"{entity} has too many patents to fetch in full — narrowing by keywords..."})
                try:
                    items = _fetch_applications_with_retry(entity, uspto_api_key, run.approved_keywords)
                except SystemExit as e:
                    _emit(run_id, {"type": "error", "message": str(e)})
                    run.stage = Stage.ERROR
                    run.error = str(e)
                    return
            for item in items:
                num = item.get("applicationNumberText")
                if num and num not in app_numbers:
                    app_numbers.append(num)

        metadata_by_app: dict[str, dict] = {}
        for i, app_number in enumerate(app_numbers):
            _emit(run_id, {
                "type": "progress", "stage": "fetching",
                "message": f"Fetching metadata {i + 1}/{len(app_numbers)}",
                "current": i + 1, "total": len(app_numbers),
            })
            metadata_by_app[app_number] = _fetch_metadata_with_retry(app_number, uspto_api_key)

        records: list[PatentRecord] = []
        for app_number, meta in metadata_by_app.items():
            if meta.get("error") or meta.get("status", "").lower() == "abandoned":
                continue
            year = (meta.get("grantDate") or meta.get("filingDate") or "")[:4]
            status = "Issued" if meta.get("patentNumber") else "Published Application"
            records.append(PatentRecord(
                application_number=app_number,
                patent_number=meta.get("patentNumber") or None,
                title=meta.get("title", ""),
                inventors=meta.get("inventors", []),
                year=year,
                status=status,
            ))

        for i, record in enumerate(records):
            _emit(run_id, {
                "type": "progress", "stage": "fetching",
                "message": f"Fetching abstracts {i + 1}/{len(records)}",
                "current": i + 1, "total": len(records),
            })
            if record.patent_number:
                abstract = scripts_bridge.fetch_abstract(record.patent_number)
                record.abstract = None if not abstract or str(abstract).startswith("ERROR") else abstract

        judgeable = [(r.application_number, r.title, r.abstract) for r in records if r.abstract]
        run.stage = Stage.FILTERING_SUMMARIZING
        _emit(run_id, {"type": "progress", "stage": "filtering_summarizing",
                        "message": f"Evaluating relevance and summarizing {len(judgeable)} patents..."})
        judgments = asyncio.run(llm.judge_patents_batch(judgeable, run.subject, run.company))

        for record in records:
            judgment = judgments.get(record.application_number)
            if judgment:
                record.relevant = judgment.relevant
                record.summary = judgment.summary

        run.patents = [r for r in records if r.relevant]

        if not run.patents:
            run.stage = Stage.ERROR
            run.error = "No relevant patents found after filtering."
            _emit(run_id, {"type": "error", "message": run.error})
            return

        categorization = llm.categorize(run.patents, run.subject)
        run.proposed_categories = categorization.categories
        for record in run.patents:
            record.categories = _lookup_categories(record, categorization.assignments)

        run.stage = Stage.AWAITING_CATEGORIZATION_APPROVAL
        _emit(run_id, {
            "type": "categorization_ready",
            "categories": run.proposed_categories,
            "patents": [p.model_dump() for p in run.patents],
        })
    except Exception as e:  # noqa: BLE001 - surface any pipeline failure to the SSE stream
        run.stage = Stage.ERROR
        run.error = str(e)
        _emit(run_id, {"type": "error", "message": str(e)})


def approve_categorization(run_id: str, categories: list[str], assignments: dict[str, list[str]]) -> RunState:
    run = RUNS[run_id]
    run.proposed_categories = categories
    for record in run.patents:
        record.categories = assignments.get(record.application_number, record.categories)
    run.stage = Stage.GENERATING_REPORT
    thread = threading.Thread(target=_generate_report, args=(run_id,), daemon=True)
    thread.start()
    return run


def _generate_report(run_id: str) -> None:
    run = RUNS[run_id]
    try:
        _emit(run_id, {"type": "progress", "stage": "generating_report",
                        "message": "Writing narrative report (this includes live inventor research and can take a few minutes)..."})
        markdown_text = llm.generate_report(run.company, run.subject, run.patents)
        html_text = llm.render_html(run.company, run.subject, markdown_text)

        base = f"{slug(run.company)}-{slug(run.subject)}"
        csv_path = run.output_dir / f"{base}-patents.csv"
        md_path = run.output_dir / f"{base}-report.md"
        html_path = run.output_dir / f"{base}-report.html"

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["number", "title", "category", "summary", "inventors", "year", "status"])
            for p in run.patents:
                writer.writerow([
                    p.patent_number or p.application_number,
                    p.title,
                    "; ".join(p.categories),
                    p.summary or "",
                    ", ".join(p.inventors),
                    p.year,
                    p.status,
                ])
        md_path.write_text(markdown_text)
        html_path.write_text(html_text)

        run.stage = Stage.DONE
        _emit(run_id, {
            "type": "report_ready",
            "files": {"csv": csv_path.name, "report_md": md_path.name, "report_html": html_path.name},
        })
    except Exception as e:  # noqa: BLE001
        run.stage = Stage.ERROR
        run.error = str(e)
        _emit(run_id, {"type": "error", "message": str(e)})


def get_run(run_id: str) -> RunState:
    return RUNS[run_id]


def get_events(run_id: str) -> "queue.Queue[dict]":
    return EVENTS[run_id]
