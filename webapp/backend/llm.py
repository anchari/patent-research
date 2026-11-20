"""
All Anthropic API calls for the judgment steps of the pipeline. Prompts mirror
skills/patent-search/SKILL.md so the web app's output matches the CLI skill's
behavior (PRD FR-13 is about the scripts; this file is the web app's own
implementation of the skill's judgment steps, made necessary because this app
runs outside a Claude Code session and has no interactive model to call into).
"""

import asyncio
import os
from pathlib import Path

import anthropic
import markdown as md

from models import Categorization, CategorizationResponse, KeywordList, PatentJudgment, PatentRecord

MODEL = "claude-opus-5"
MAX_CONCURRENT_JUDGMENTS = 5

ANNOTATE_ASSETS_DIR = Path.home() / ".claude" / "skills" / "annotate-html" / "assets"


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _async_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def propose_keywords(company: str, subject: str) -> list[str]:
    prompt = (
        f"A user wants to search USPTO patent records for {company}'s patents in the "
        f'subject area "{subject}".\n\n'
        "Generate a set of search terms that cover this subject area, including:\n"
        "- The exact phrase given\n"
        "- Technical synonyms and related terms\n"
        "- Upstream/downstream concepts (e.g. \"mesh topology\" for \"wireless mesh\")\n"
        "- Alternative naming conventions used in academic or standards literature\n\n"
        "These terms are matched as a literal wildcard against patent invention titles (via "
        "USPTO's `inventionTitle:{term}*` query), so each term MUST be 1-2 words, lowercase, "
        "no punctuation or parenthetical acronyms (write \"mesh network\", not \"wireless mesh "
        "network topology (WMN)\") — a long, over-specific phrase is unlikely to appear verbatim "
        "in a real patent title and will silently zero out the search. Favor broad, common terms "
        "that over-include; a later step reads each patent's abstract to do the real relevance "
        "filtering.\n\n"
        "Return 4-10 terms."
    )
    response = _client().messages.parse(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        output_format=KeywordList,
    )
    if response.parsed_output is None:
        raise RuntimeError(
            f"Keyword generation response had no parsed output (stop_reason={response.stop_reason!r})."
        )
    return response.parsed_output.keywords


def judge_patent_sync(title: str, abstract: str, subject: str, company: str) -> PatentJudgment:
    return asyncio.run(_judge_patent(_async_client(), title, abstract, subject, company))


async def _judge_patent(
    client: anthropic.AsyncAnthropic, title: str, abstract: str, subject: str, company: str
) -> PatentJudgment:
    prompt = (
        f'Subject area: "{subject}"\nCompany: {company}\n\n'
        f"Patent title: {title}\nAbstract: {abstract}\n\n"
        "Base the relevance decision on the ABSTRACT, not the title — titles are broad and "
        "claim-covering and often match search terms that don't reflect the invention's actual "
        "subject. Watch for false positives: sensor/radar hardware vs. communications, a shared "
        "legal name belonging to an unrelated company, and polysemous keywords (\"mesh\", "
        "\"antenna\", \"radio\") that mean something different outside this subject area. "
        "If the abstract doesn't genuinely address this subject area, mark it not relevant.\n\n"
        "If relevant, write a 2-3 sentence plain-English summary for a technically literate "
        "non-lawyer reader: (1) what problem the invention addresses, (2) what it does or how it "
        "works at a high level, (3) optionally what's notable about the approach. Avoid patent "
        "jargon (\"claim\", \"embodiment\", \"wherein\", \"comprising\")."
    )
    response = await client.messages.parse(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        output_format=PatentJudgment,
    )
    if response.parsed_output is None:
        raise RuntimeError(
            f"Patent judgment response had no parsed output (stop_reason={response.stop_reason!r})."
        )
    return response.parsed_output


async def judge_patents_batch(
    patents: list[tuple[str, str, str]], subject: str, company: str
) -> dict[str, PatentJudgment]:
    """patents: list of (application_number, title, abstract). Returns app_number -> judgment."""
    client = _async_client()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_JUDGMENTS)

    async def bound_judge(app_number: str, title: str, abstract: str) -> tuple[str, PatentJudgment | None]:
        async with semaphore:
            try:
                judgment = await _judge_patent(client, title, abstract, subject, company)
            except Exception:
                # One malformed/failed judgment (e.g. truncated or invalid JSON output)
                # shouldn't abort the whole batch — treat this patent as unjudged and move on,
                # matching the partial-failure tolerance the CLI scripts have for abstract fetches.
                return app_number, None
            return app_number, judgment

    results = await asyncio.gather(
        *(bound_judge(app_number, title, abstract) for app_number, title, abstract in patents)
    )
    return {app_number: judgment for app_number, judgment in results if judgment is not None}


def categorize(patents: list[PatentRecord], subject: str) -> Categorization:
    listing = "\n".join(
        f"- id={p.application_number} | {p.title} | {p.summary}" for p in patents if p.relevant
    )
    prompt = (
        f'Review this patent portfolio in the subject area "{subject}" holistically.\n\n'
        f"{listing}\n\n"
        "Create 5-12 logical categories that capture the main themes across the portfolio. "
        "Categories should be distinct and non-overlapping, with short descriptive names "
        '(e.g. "Signal Processing", "Hardware Integration", "Power Optimization"). '
        "Assign each patent to 1-2 categories. `assignments` must have exactly one entry per "
        "patent, each with `patent_id` copied verbatim from its `id=` value above (not the "
        "patent title, not any other number) and `categories` listing its 1-2 assigned "
        "category names — if a patent clearly spans two themes, list both; do not force more "
        "than 2."
    )
    response = _client().messages.parse(
        model=MODEL,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
        output_format=CategorizationResponse,
    )
    if response.parsed_output is None:
        raise RuntimeError(
            f"Categorization response had no parsed output (stop_reason={response.stop_reason!r}) — "
            "likely truncated before the JSON completed."
        )
    parsed = response.parsed_output
    return Categorization(
        categories=parsed.categories,
        assignments={a.patent_id: a.categories for a in parsed.assignments},
    )


def generate_report(company: str, subject: str, patents: list[PatentRecord]) -> str:
    """Runs an agentic loop (web_search + web_fetch) and returns the narrative report as Markdown."""
    listing = "\n".join(
        f"- {p.patent_number or p.application_number} | {p.title} | {p.status} | {p.year} | "
        f"categories: {', '.join(p.categories)} | inventors: {', '.join(p.inventors)}\n"
        f"  summary: {p.summary}"
        for p in patents
        if p.relevant
    )
    prompt = f"""Write a narrative patent portfolio analysis for {company} in the subject area "{subject}",
based on the following {sum(1 for p in patents if p.relevant)} patents:

{listing}

Structure the report in Markdown exactly as follows:

# {company} — {subject} Patent Portfolio
> Analysis based on N issued patents and published applications, YYYY-YYYY

## Where {company} is innovating
Identify 2-5 meaningful clusters of patents representing distinct areas of active investment. For
each: a short heading, the technical challenge addressed, the approach(es) taken (cite patent
numbers and inventors), how the approach evolved over time if it spans years, and why the area is
strategically interesting. Do not just restate the categories — find narrative threads that connect
patents across categories.

## Where {company} is not innovating
Identify 3-5 notable gaps: subject areas adjacent to the portfolio with zero or near-zero patents.
For each: name the area, state there are no patents in it, and offer a plausible explanation
(commodity input, standards-body-defined protocol, deliberate reliance on infrastructure, etc.).

## Key inventors and their areas of specialization
For each inventor appearing on 2+ patents: a subheading with their name and a one-line focus-area
characterization, their patent count and which categories they span, what their cross-category
presence implies about their role, and any temporal pattern (foundational vs. current-frontier work).

Before writing each inventor's entry, use the web_search tool to look up "[Inventor Full Name]"
"[Company Name]" linkedin, and web_fetch to read the profile if a LinkedIn URL is found. If found,
link their name to the profile and incorporate 1-2 sentences on their background (current title,
employer, relevant career history) into the narrative. If no profile is found, note "No LinkedIn
profile found" rather than skipping the search. Do not fabricate profile details.

## Closing summary
2-4 sentences characterizing the portfolio as a whole: what it reveals about the company's theory of
where their engineering creates proprietary value vs. what they buy from the ecosystem.

## Appendix — Patent Reference
A full listing grouped by category (same categories as above), sorted chronologically within each
group. For each patent: the patent number as a Markdown link to
https://patents.google.com/patent/[number]/en, the title, status, year, comma-separated inventors,
and the summary.

Write the full report now as Markdown only (no commentary outside the report)."""

    tools = [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": 30},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 30},
    ]
    # A full report (deep narrative + inventor bios + a per-patent appendix for every
    # retained patent) can easily exceed 16K output tokens for a mid-size portfolio —
    # 16K silently truncated mid-appendix in testing. 64K gives real headroom; streaming
    # is required at this size to avoid HTTP timeouts (per Anthropic's SDK guidance).
    messages = [{"role": "user", "content": prompt}]
    accumulated_text = ""
    max_continuations = 5
    for _ in range(max_continuations):
        with _client().messages.stream(
            model=MODEL, max_tokens=64000, tools=tools, messages=messages
        ) as stream:
            response = stream.get_final_message()

        if response.stop_reason == "pause_turn":
            # Server tools (web_search/web_fetch) execute automatically within a turn;
            # pause_turn means the server-side tool loop hit an iteration limit mid-research,
            # not that any text is ready yet — resume the tool loop without touching the
            # accumulated report text, per Anthropic's server-tool pattern.
            messages = [{"role": "user", "content": prompt}, {"role": "assistant", "content": response.content}]
            continue

        # Claude sometimes writes a short lead-in ("I'll start by researching...") before its
        # first tool call. Drop only that leading pre-tool-call text — everything from the
        # first tool-related block onward (including prose interleaved between tool calls) is
        # genuine report content and must be kept, or later sections silently go missing.
        first_tool_idx = next((i for i, b in enumerate(response.content) if b.type != "text"), None)
        turn_blocks = response.content if first_tool_idx is None else response.content[first_tool_idx:]
        accumulated_text += "".join(b.text for b in turn_blocks if b.type == "text")

        if response.stop_reason == "max_tokens":
            # Ran out of output budget (this truncated mid-appendix in testing at 16K) —
            # continue from exactly where it left off rather than losing the rest of the report.
            messages = messages + [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": "Continue the report exactly where you left off. "
                                             "Do not repeat anything already written and do not add commentary."},
            ]
            continue
        break

    return accumulated_text


def render_html(company: str, subject: str, markdown_text: str) -> str:
    body = md.markdown(markdown_text, extensions=["extra"])
    annotate_css = ""
    annotate_js = ""
    annotations_block = ""
    css_path = ANNOTATE_ASSETS_DIR / "annotate.css"
    js_path = ANNOTATE_ASSETS_DIR / "annotate.js"
    if css_path.exists() and js_path.exists():
        annotate_css = f"<style>{css_path.read_text()}</style>"
        annotate_js = f"<script>{js_path.read_text()}</script>"
        annotations_block = '<div id="annotations-data" style="display:none">[]</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{company} — {subject} Patent Portfolio</title>
  <style>
    body {{ max-width: 860px; margin: 40px auto; padding: 0 24px; font-family: Georgia, serif; font-size: 17px; line-height: 1.7; color: #1a1a1a; }}
    h1 {{ font-size: 1.6em; border-bottom: 2px solid #333; padding-bottom: 0.3em; }}
    h2 {{ font-size: 1.3em; margin-top: 2em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }}
    h3 {{ font-size: 1.05em; margin-top: 1.5em; color: #333; }}
    blockquote {{ margin: 0; padding: 0.2em 1em; border-left: 3px solid #ccc; color: #555; font-style: italic; }}
    strong {{ color: #000; }}
    a {{ color: #1a56db; }}
  </style>
  {annotate_css}
</head>
<body>
{body}
{annotations_block}
{annotate_js}
</body>
</html>"""
