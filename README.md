# patent-research

Tools and data for USPTO patent portfolio research. Given a company name and subject area, produces a structured CSV and a narrative analysis of the company's patent portfolio.

See `DESIGN.md` for the full system design, data sources, and known limitations.

---

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
                                        innovation areas, partner-reliance gaps, and key
                                        inventor profiles.
```

### Prerequisites

- **Claude Code** with the `patent-search` skill installed at `~/.claude/skills/patent-search/`
- **USPTO ODP API key** — free, get one at [data.uspto.gov](https://data.uspto.gov/apis/getting-started)
- **Python 3.9+** for the fetch scripts

### Running the workflow

In Claude Code, run:
```
/patent-search [company name] | [subject area]
```

Examples:
```
/patent-search Waymo LLC | wireless communications
/patent-search Apple Inc | noise cancellation
/patent-search 3M Company | battery technology
```

The skill will ask for your ODP API key on first use, then walk through company disambiguation and keyword confirmation before invoking the scripts.

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

---

## Data files

Output files are stored in `data/`. Each run produces two files with the same base name:
- `[company-slug]-[subject-slug]-patents.csv` — structured data (number, title, category, summary, inventors, year, status)
- `[company-slug]-[subject-slug]-report.md` — narrative analysis (innovation areas, partner-reliance gaps, key inventor profiles)

| File | Description |
|---|---|
| `data/tropos-networks-inc-wireless-patents.csv` | 62 issued patents assigned to Tropos Networks, Inc. (wireless networking, 2005–2017) |
| `data/waymo-llc-wireless-communications-patents.csv` | 17 patents assigned to Waymo LLC (wireless communications, 2017–2025) |
| `data/waymo-llc-wireless-communications-report.md` | Narrative analysis of Waymo's wireless communications portfolio |
