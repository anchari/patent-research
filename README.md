# patents

Scripts and data for USPTO patent portfolio research.

## Scripts

These scripts pipeline together to produce a patent CSV and narrative report for any company. Each step writes its output to a file that the next step reads.

Intermediate files (`*.txt`, `*.json`) are gitignored — they're scratch files regenerated each run. Only the final outputs in `data/` are committed.

### Prerequisites

A free USPTO Open Data Portal (ODP) API key — get one at [data.uspto.gov](https://data.uspto.gov/apis/getting-started).

### Pipeline

```
fetch_patents.py  →  fetch_metadata.py  →  fetch_abstracts.py  →  (Claude summarizes)  →  CSV
```

**Step 1 — Get all application numbers for a company:**
```bash
# Small filer — fetch everything
python3 fetch_patents.py "Tropos Networks" $USPTO_API_KEY --output tropos_app_numbers.txt

# Large filer — narrow by subject area first (otherwise tens of thousands of results)
python3 fetch_patents.py "Apple Inc" $USPTO_API_KEY \
  --keywords "noise cancellation" "audio processing" "microphone" \
  --output apple_audio_app_numbers.txt
```

**Step 2 — Fetch structured metadata for each application:**
```bash
python3 fetch_metadata.py tropos_app_numbers.txt $USPTO_API_KEY --output tropos_metadata.json
```

**Step 3 — Fetch abstracts from Google Patents:**
```bash
python3 fetch_abstracts.py tropos_metadata.json --output tropos_abstracts.json
```

**Step 4 — Summarize, categorize, and export:**
Hand `tropos_metadata.json` and `tropos_abstracts.json` to Claude and ask it to write summaries, assign categories, produce the final CSV, and write the narrative report.

### Script details

| Script | Input | Output | Notes |
|---|---|---|---|
| `fetch_patents.py` | Assignee name, API key | App numbers (text) | Uses `assignmentBag` query — finds original filings and reassigned patents. Hard cap of 500 results — exits with an error if exceeded. Use `--keywords` to filter by invention title for large filers. |
| `fetch_metadata.py` | App numbers file, API key | JSON with title, inventors, grant date, status, patent number | Calls `/meta-data` endpoint per application |
| `fetch_abstracts.py` | Metadata JSON | JSON mapping patent number → abstract text | Fetches Google Patents pages; respects rate limits via configurable delay |

## Data files

Output files are stored in `data/`. Each run produces two files with the same base name:
- `[company-slug]-[subject-slug]-patents.csv` — structured data (number, title, category, summary, inventors, year, status)
- `[company-slug]-[subject-slug]-report.md` — narrative analysis (innovation areas, partner-reliance gaps, key inventor profiles)

| File | Description |
|---|---|
| `data/tropos-networks-inc-wireless-patents.csv` | 62 issued patents assigned to Tropos Networks, Inc. (wireless networking, 2005–2017) |
| `data/waymo-llc-wireless-communications-patents.csv` | 17 patents assigned to Waymo LLC (wireless communications, 2017–2025) |
| `data/waymo-llc-wireless-communications-report.md` | Narrative analysis of Waymo's wireless communications portfolio |
