# Patent Search Workflow — Design Document

## Purpose

This document describes the design of the patent portfolio research workflow: an interactive, multi-step process that takes a company name and a subject area, retrieves the complete set of US patents assigned to that company in that area, and produces a structured CSV with plain-English summaries and logical categories.

It is intended to evolve as the workflow is tested, extended, and improved.

---

## Workflow overview

The workflow is multi-step and interactive. Two confirmation checkpoints happen before any bulk processing — company disambiguation and search term approval — so the user can course-correct before work is done that's hard to undo or slow to redo.

```
[User: company name + subject area]
        │
        ▼
1. Company disambiguation
   Query USPTO for all assignee entity names matching the company.
   Present candidates. User confirms which to include.
        │
        ▼
2. Search term generation
   Propose synonyms and related terms for the subject area.
   User approves / edits the list.
        │
        ▼
3. Patent discovery
   Query USPTO ODP API by confirmed entity names (+ optional title keywords).
   Returns full list of application numbers — both issued and pending/abandoned.
        │
        ▼
4. Metadata fetch (fetch_metadata.py)
   Per-application: title, inventors, patent number, grant date, status.
   Filter: keep issued patents (and optionally published applications).
   Filter: discard off-topic patents (title doesn't match any search term).
        │
        ▼
5. Abstract fetch (fetch_abstracts.py)
   For each retained patent, fetch abstract text from Google Patents.
        │
        ▼
6. Summarization (Claude)
   Write a 2–3 sentence plain-English summary per patent from the abstract.
        │
        ▼
7. Categorization (Claude)
   Review all retained patents holistically.
   Create 5–12 logical categories and assign each patent to 1–2.
        │
        ▼
8. CSV export
   Write [company-slug]-[subject-slug]-patents.csv to the current directory.
        │
        ▼
9. Report
   Summary: file name, patent count, category breakdown, observations.
```

---

## Components

### Scripts (this repo)

| File | Role | Interface |
|---|---|---|
| `fetch_patents.py` | Query USPTO ODP API by assignee name; return all application numbers | CLI: assignee name + API key → text file of app numbers |
| `fetch_metadata.py` | Fetch per-application structured metadata from ODP API | CLI: app numbers file + API key → `metadata.json` |
| `fetch_abstracts.py` | Fetch abstract text for each issued patent from Google Patents | CLI: `metadata.json` → `abstracts.json` |

### Claude skill (`~/.claude/skills/patent-search/`)

The skill (`SKILL.md`) drives the interactive workflow. It orchestrates the steps above, calls the scripts via Bash, handles the two confirmation checkpoints, generates summaries and categories, and writes the final CSV. The scripts are the mechanical data-fetch layer; Claude handles all judgment — entity disambiguation, search term quality, relevance filtering, summarization, and categorization.

---

## Data sources

### USPTO Open Data Portal API (`api.uspto.gov`)
- **What it provides:** Structured patent file wrapper data — application numbers, titles, inventors, filing dates, grant dates, status, assignee history.
- **Authentication:** `X-Api-Key` header. Free API key from [data.uspto.gov](https://data.uspto.gov/apis/getting-started).
- **Key endpoints used:**
  - `GET /api/v1/patent/applications/search?q=...&limit=100&offset=0` — search by assignee name or title keywords
  - `GET /api/v1/patent/applications/{applicationNumberText}/meta-data` — per-application details
- **Query field used for assignee search:** `assignmentBag.assigneeBag.assigneeNameText:"Company Name"` — this covers both original filers and patents reassigned after filing, which is essential for acquired companies (see Design Decisions below).
- **Does not provide:** Abstracts. Full text is not in the file wrapper data.
- **Coverage:** Good back to ~2000. Earlier patents may be incomplete.

### Google Patents (`patents.google.com`)
- **What it provides:** Patent abstracts scraped from HTML pages.
- **Authentication:** None (public web scraping).
- **Rate limiting:** Undocumented. The current script uses a 0.8s inter-request delay, which has worked reliably in practice. Aggressive fetching triggers 503s.
- **Fragility:** HTML structure changes without notice. The abstract extraction uses several regex fallback patterns, but this will break eventually and need updating.
- **Better alternative:** Google Patents has an unofficial XHR endpoint (`/xhr/query`) but it returns similarity-based results, not strict assignee matches — not useful for enumerating a complete portfolio.

### USPTO EFTS (`efts.uspto.gov`) — retired
The legacy full-text search endpoint. **DNS no longer resolves** as of early 2025 after USPTO migrated to the Open Data Portal. Do not use.

### PatentsView (`search.patentsview.org`) — inaccessible
Formerly an excellent structured API. Required a free API key since October 2024. As of the time of writing, connections from the Claude Code environment are refused. May be worth retrying in future as network policies change.

---

## Design decisions

### Use `assignmentBag` not `firstApplicantName` for searches
`applicationMetaData.firstApplicantName` only captures the original applicant at filing time. When a company's patents get reassigned — through acquisition, merger, or corporate restructuring — the `firstApplicantName` doesn't update. Using `assignmentBag.assigneeBag.assigneeNameText` finds all applications where the entity ever appeared as an assignee, giving ~20% more results for companies with assignment history.

**Example:** Tropos Networks was acquired by ABB, then by Hitachi. Searching `firstApplicantName:"Tropos Networks"` returns only 13 results. Searching the assignment bag returns 76 — all applications ever associated with Tropos Networks, regardless of who holds them now.

### Two confirmation steps before bulk fetching
The interactive checkpoints (entity disambiguation + search term approval) happen before any slow work. Fixing a wrong entity name or a missing synonym after fetching 60 patents is much more expensive than catching it upfront. This is the key structural difference from a fully automated pipeline.

### Filter abandoned applications out by default
The USPTO returns all application statuses. For most use cases (understanding a company's IP portfolio), only issued patents matter — abandoned applications represent ideas that were dropped, often for strategic reasons unrelated to the invention's merit. Published-but-abandoned applications can be included on request.

### Exclude obvious false positives manually
Patent assignment records occasionally contain data errors — an application assigned to a company that clearly doesn't belong to them (e.g., US7566599, an IBM semiconductor transistor patent, appeared in Tropos's assignment history). The relevance filter step relies on Claude's judgment to identify and exclude these rather than trying to automate it with rules.

### Summaries and categories are Claude-generated, not templated
Patent abstracts are written in legal language that is deliberately opaque. Rule-based summarization produces poor results. The value of Claude-generated summaries is the translation from "A method is disclosed comprising..." into plain language that explains the actual problem being solved and why the approach is notable.

---

## Known limitations

### HTTP 404 from the ODP API means zero results, not an error
The USPTO ODP API returns HTTP 404 (not HTTP 200 with an empty array) when a search query matches no records. This is intentional API behavior, not a server error. Any code that calls the ODP API must catch `HTTPError` with code 404 and treat it as an empty result set. Unhandled, it will surface as a script failure and silently drop valid search terms from the results.

### Title-keyword searches produce systematic false positives
Filtering by invention title (rather than full-text abstract search) causes several categories of false positives:

- **Sensor hardware vs. communications** — Terms like "antenna", "radio", "transceiver", and "wireless" appear in both wireless communications patents and in sensing/radar patents that use RF for detection rather than communication. For a wireless communications search, a patent describing a phased-array radar return is a false positive; the title gives no reliable signal.
- **Polysemous keywords** — "Mesh" matches both network topology patents and structural/material patents (e.g., "Waterproofing 3D Printed Meshes"). "Antenna" matches communication antennas and physical mounting structures. Abstract review is required to resolve the ambiguity.
- **Same legal name, different company** — Corporate name coincidences can cause the `assignmentBag` query to return patents from an unrelated entity that happened to use the same legal name before the target company was founded. These patents typically describe a completely different industry and are caught only by abstract review.

The correct mitigation for all three is the manual relevance filter in Step 4 — reading title + abstract before retaining. There is no automated fix as long as the ODP API does not expose abstract text as a searchable field.

### Abstract fetching is fragile
Google Patents HTML structure changes without notice. The regex patterns in `fetch_abstracts.py` have multiple fallbacks, but the script will eventually need maintenance when Google updates its page structure. A more robust approach would use the Google Patents API if one becomes publicly available.

### No full-text search across abstracts
The current workflow filters patents by matching search terms against invention titles only. A title like "Method and apparatus for routing" gives no signal about whether it's relevant to "mesh networking." Ideally, step 3 would filter on abstract text too — but the ODP API's search index doesn't appear to include abstract content in queryable fields (as of the time of writing). Worth re-testing as the ODP API evolves.

### Summarization is not parallelized
Summaries are generated sequentially in context. For portfolios over ~50 patents, this is a significant in-context operation. A future improvement would batch summarization across parallel agent calls.

### Categorization is holistic and non-deterministic
Categories are created after reviewing the full portfolio, which means they differ between runs even for the same input. For longitudinal analysis (e.g., comparing portfolios across years), fixed category schemes would be more useful. This would require a separate category-design step before the categorization pass.

### No caching between runs
If you re-run the workflow for the same company, all fetches repeat from scratch. The scripts write to files, so partial results can be reused manually, but there's no automatic incremental update (e.g., "only fetch patents filed after the last run's date").

---

## Future improvements

### Near-term
- [ ] Add `--since` date filter to `fetch_patents.py` to support incremental updates
- [ ] Add retry logic with exponential backoff to `fetch_abstracts.py` for 503 responses
- [ ] Surface the abstract in the `fetch_metadata.py` output if the ODP API adds it (check periodically)
- [ ] Add a `--include-abandoned` flag to `fetch_metadata.py`

### Medium-term
- [ ] Parallel summarization: split the patent list into batches and run summaries across multiple Claude calls
- [ ] Fixed category schemes: allow the user to specify a category list upfront, then have Claude assign patents to those fixed categories rather than generating them dynamically
- [ ] International coverage: extend to EPO (via [ops.epo.org](https://ops.epo.org)) and WIPO (via [patentscope.wipo.int](https://patentscope.wipo.int)) for non-US filings

### Longer-term
- [ ] **Inventor analysis**: for each inventor in the portfolio, compute a patent count per category and identify their primary focus area(s). Surface the top inventors overall and the leading inventor per category. Useful for understanding who the key technical contributors are and what they specialize in — relevant for due diligence, competitive intelligence, and identifying potential expert witnesses or hires.
  - *Profile enrichment:* LinkedIn has no usable public API. Primary fallback is web search (`"[inventor name]" [company] site:linkedin.com`) to pull publicly indexed profile data — current employer, title, career trajectory. If a people-data API key is available (Clearbit, Apollo, PeopleDataLabs), that should be used instead for structured and bulk lookups.
- [ ] Portfolio comparison: run two companies side-by-side and identify overlapping areas (patent landscape analysis)
- [ ] Citation analysis: for each patent, fetch forward citations to identify which inventions were most influential
- [ ] Trend analysis: group patents by filing year and category to visualize how a company's research focus shifted over time
