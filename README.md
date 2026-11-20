# patent-research

## Overview

This workflow generates a plain-English portfolio analysis for any company's patents in a given subject area — it discovers all matching US patents (including ones acquired via M&A), filters out false positives, and produces a categorized summary of what the company is actually inventing in the form of a narrative analysis doc. It's valuable for researchers, analysts, and investors who need to evaluate a company's IP strategy and technical focus areas without reading through dozens of patents written in dense legal language themselves.

## Problem it solves

Researching a company's patent portfolio in a given technology area is slow, manual work: you have to find every legal entity name the company has filed under (including acquired subsidiaries), search USPTO by assignee, weed out irrelevant results that title-keyword searches inevitably drag in, read dense legal-language abstracts to figure out what each patent actually does, and then synthesize all of that into something a human can use for competitive/technical analysis. This repo automates the mechanical/slow parts and pairs them with an LLM for the parts that need judgment.

It's a hybrid Python scripts + Claude Code skill workflow (`/patent-search [company] | [subject]`) — see the full step-by-step breakdown below. Two example runs are committed: Tropos Networks (62 wireless-networking patents, 2005–2017) and Waymo LLC (17 wireless-communications patents, 2017–2025, with full narrative report).

See `PRD.md` for use cases, requirements and the roadmap (including backlog and future ideas), and `DESIGN.md` for the full system design, data sources and known limitations (e.g., the 404-as-empty-result quirk in the USPTO API, fragility of Google Patents scraping).

## How it works

The workflow is driven by a **Claude Code skill** (`/patent-search`) that handles all the judgment-intensive steps interactively. The Python scripts in this repo handle the slow data-fetch steps that the skill orchestrates. Neither the scripts alone nor the skill alone is the complete workflow — they work together.

### Full workflow

```
1. Company disambiguation    [Claude]   Query USPTO to find all legal entity names for the
                                        company. Confirm with user which to include.

2. Keyword generation        [Claude]   Propose technical synonyms and related terms for
                                        the subject area. Confirm with user before searching.

3. Patent discovery          [Script]   fetch_patents.py queries USPTO ODP API by assignee
                                        name (+ optional title keywords for large filers).
                                        Returns candidate application numbers.

4. Metadata fetch            [Script]   fetch_metadata.py retrieves title, inventors, patent
                                        number, grant date, and status for each application.

5. Abstract fetch            [Script]   fetch_abstracts.py scrapes Google Patents for the
                                        abstract of each candidate patent.

6. Relevance filter          [Claude]   Read each abstract. Discard patents that don't
                                        genuinely relate to the subject area. Title keywords
                                        produce false positives — the abstract is the
                                        authoritative relevance gate.

7. Summarization             [Claude]   Write a 2–3 sentence plain-English summary per
                                        retained patent.

8. Categorization            [Claude]   Review all patents holistically. Create 5–12 logical
                                        categories and assign each patent to 1–2.

9. CSV export                [Claude]   Write [company]-[subject]-patents.csv to the current
                                        working directory.

10. Narrative report         [Claude]   Write [company]-[subject]-report.md covering:
                                        innovation areas, partner-reliance gaps, key
                                        inventor profiles, and a patent-reference appendix.
```

### Prerequisites

- **Claude Code** with the `patent-search` skill. The skill lives in `skills/patent-search/` in this repo — symlink it into place on first clone:
  ```bash
  ln -s "$(pwd)/skills/patent-search" ~/.claude/skills/patent-search
  ```
- **USPTO ODP API key** — free, get one at [data.uspto.gov](https://data.uspto.gov/apis/getting-started)
- **Python 3.9+** for the fetch scripts
- A `.env` file at the repo root holding `USPTO_API_KEY=...` (and, if you're using the web app below, `ANTHROPIC_API_KEY=...` too). Copy `.env.example` to `.env` and fill it in — it's gitignored. To use the key on the command line, `set -a && source .env && set +a`, then reference it as `$USPTO_API_KEY` in the examples below.

### Running the workflow

In Claude Code, run:
```
/patent-search [company name] | [subject area] | [optional competitors, comma-separated]
```

Examples:
```
/patent-search Waymo LLC | wireless communications
/patent-search Apple Inc | noise cancellation
/patent-search 3M Company | battery technology
/patent-search Example Robotics Inc | full portfolio | Rival Robotics Inc, Other Robotics Corp
```

The skill will ask for your ODP API key on first use, then walk through company disambiguation and keyword confirmation before invoking the scripts.

### Web app (alternative to Claude Code) — incomplete

> The web app runs an earlier version of the workflow and is **not functionally equivalent** to the `/patent-search` skill (no competitor comparison, status labels, coverage section, filing chart or claim analysis). Use the skill for complete reports. See `webapp/PRD.md` ("Future direction").

An earlier version of the interactive workflow — company/keyword approval, live progress, categorization review — is also available as a local web app in `webapp/`, for running it without a Claude Code session open. It's a second interface on top of the same scripts and USPTO/Anthropic APIs; the CLI scripts and `/patent-search` skill above are unaffected either way. See `webapp/PRD.md` and `webapp/DESIGN.md` for what it does and how it's built, or jump straight to setup:

```bash
cd webapp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --app-dir backend --reload --port 8000
# open http://localhost:8000
```

Uses the same repo-root `.env` as the CLI scripts (see Prerequisites above) — set `USPTO_API_KEY` and `ANTHROPIC_API_KEY` there once, for both interfaces.

---

## Scripts

The three fetch scripts are the data-fetch layer. They are called by the skill but can also be run manually to re-fetch data without re-running the full interactive workflow.

Intermediate files (`*.txt`, `*.json`) are gitignored — they're scratch files regenerated each run. Only the final outputs in `data/` are committed.

### fetch_patents.py

Queries the USPTO ODP API for all applications where the given name appears as an assignee. Uses the `assignmentBag` field, which covers original filings and patents reassigned after filing (e.g., through acquisition).

```bash
# Small filer — fetch everything (hard cap: 500 results)
python3 fetch_patents.py "Tropos Networks, Inc." $USPTO_API_KEY --output tropos_app_numbers.txt

# Large filer — filter by title keywords to stay under the cap
python3 fetch_patents.py "Apple Inc" $USPTO_API_KEY \
  --keywords "noise cancellation" "audio processing" "microphone" \
  --output apple_audio_app_numbers.txt
```

**Hard cap:** exits with an error if the query matches more than 500 results. Use `--keywords` to narrow by invention title for large filers.

### fetch_metadata.py

Fetches structured metadata for each application number from the USPTO `/meta-data` endpoint.

```bash
python3 fetch_metadata.py tropos_app_numbers.txt $USPTO_API_KEY --output tropos_metadata.json
```

Output fields per application: `patentNumber`, `inventionTitle`, `applicationStatusDescriptionText`, `grantDate`, `filingDate`, `inventorBag`, `assignmentBag`.

### fetch_abstracts.py

Scrapes Google Patents for the abstract of each issued patent in the metadata file.

```bash
python3 fetch_abstracts.py tropos_metadata.json --output tropos_abstracts.json
```

Uses a 0.8s delay between requests to avoid rate limiting. Tries both `B2` and `B1` URL suffixes on 404.

### odp_client.py

Shared helper that every USPTO ODP request goes through (both scripts above and the web app). It enforces ODP's rate limits machine-wide: one request in flight at a time, at least 0.3s between requests, and automatic retry with backoff on HTTP 429. The limits are fixed and can't be overridden. `fetch_metadata.py --delay` adds extra time on top. For ad hoc ODP calls in Python, use `from odp_client import odp_get_json`.

---

## Data files

Output files are stored in `data/`. Each run produces three files with the same base name:
- `[company-slug]-[subject-slug]-patents.csv` — structured data (number, title, category, summary, inventors, year, status, filed, total_claims, independent_claims, shortest_independent_words, claim_breadth; claim columns are filled for issued patents only). `status` is "Issued" or "Published Application (Pending)" ("Published Application (Abandoned)" only on request)
- `[company-slug]-[subject-slug]-report.md` — narrative analysis (overview with filing-activity chart, innovation areas, gaps, experimental portfolio strength from issued-patent claims, coverage of issued patents vs. pending applications, optional competitive comparison, key inventor profiles, patent-reference appendix)
- `[company-slug]-[subject-slug]-competitors-patents.csv` — only when competitors are given: competitor filings mapped to the same categories (at most 3 competitors, 100 filings each)

Coverage limits: the USPTO data only shows issued patents and published applications. Unpublished nonprovisionals (roughly the last 18 months of filings), provisional applications and foreign filings are not visible, so each report includes a coverage section and, where available, reconciles counts against the company's 10-K or S-1 disclosure.
- `[company-slug]-[subject-slug]-report.html` — same report as a self-contained HTML file

| File | Description |
|---|---|
| `data/tropos-networks-inc-wireless-patents.csv` | 62 issued patents assigned to Tropos Networks, Inc. (wireless networking, 2005–2017) |
| `data/waymo-llc-wireless-communications-patents.csv` | 17 patents assigned to Waymo LLC (wireless communications, 2017–2025) |
| `data/waymo-llc-wireless-communications-report.md` | Narrative analysis of Waymo's wireless communications portfolio |
