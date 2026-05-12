# patents

Scripts and data for USPTO patent portfolio research.

## Scripts

These scripts pipeline together to produce a patent CSV for any company. Each step writes its output to a file that the next step reads.

### Prerequisites

A free USPTO Open Data Portal (ODP) API key — get one at [data.uspto.gov](https://data.uspto.gov/apis/getting-started).

### Pipeline

```
fetch_patents.py  →  fetch_metadata.py  →  fetch_abstracts.py  →  (Claude summarizes)  →  CSV
```

**Step 1 — Get all application numbers for a company:**
```bash
python3 fetch_patents.py "Tropos Networks" $USPTO_API_KEY --output tropos_app_numbers.txt
```

**Step 2 — Fetch structured metadata for each application:**
```bash
python3 fetch_metadata.py tropos_app_numbers.txt $USPTO_API_KEY --output tropos_metadata.json
```

**Step 3 — Fetch abstracts from Google Patents:**
```bash
python3 fetch_abstracts.py tropos_metadata.json --output tropos_abstracts.json
```

**Step 4 — Summarize and export to CSV:**
Hand `tropos_metadata.json` and `tropos_abstracts.json` to Claude and ask it to write summaries, assign categories, and produce the final CSV.

### Script details

| Script | Input | Output | Notes |
|---|---|---|---|
| `fetch_patents.py` | Assignee name, API key | App numbers (text) | Uses `assignmentBag` query — finds original filings and reassigned patents |
| `fetch_metadata.py` | App numbers file, API key | JSON with title, inventors, grant date, status, patent number | Calls `/meta-data` endpoint per application |
| `fetch_abstracts.py` | Metadata JSON | JSON mapping patent number → abstract text | Fetches Google Patents pages; respects rate limits via configurable delay |

## Data files

Output CSVs are stored in `data/`. Each file is named `[company-slug]-[subject-slug]-patents.csv`.

| File | Description |
|---|---|
| `data/tropos-networks-inc-wireless-patents.csv` | 62 issued patents assigned to Tropos Networks, Inc. (wireless networking, 2005–2017) |
