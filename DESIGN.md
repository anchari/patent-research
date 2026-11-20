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
   Filter: discard off-topic patents based on abstract (not title).
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
9. Narrative report (Claude)
   Write [company-slug]-[subject-slug]-report.md and .html to the current directory.
   Sections: innovation areas, gaps/partner reliance, key inventor profiles.
   HTML is self-contained (inline styles, no external dependencies).
        │
        ▼
10. Report to user
    Filenames, patent count, category breakdown, headline finding.
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

### Distinguish issued patents from applications, and state what is invisible
Issued patents and published applications are counted and labelled separately everywhere (CSV `status`, report header, narrative). The USPTO public record cannot show unpublished nonprovisionals (inside the ~18-month publication window or filed with a non-publication request), provisionals (never published) or foreign filings. For a company with a recent filing program this hides most of its pipeline. Example: a company's S-1 might report 40 issued U.S. patents and 67 pending U.S. applications (32 nonprovisional, 35 provisional), while the search finds all 40 issued patents but only 7 published applications; the other 60 pending applications are unpublished nonprovisionals and provisionals. Each report therefore includes a coverage section, reconciles against 10-K/S-1 disclosures where they exist, and qualifies any conclusion drawn from absence as applying to the public record.

### Report order: findings first, caveats after
The report leads with what the company is doing (overview, where it innovates, where it doesn't) and puts the coverage caveats after those sections. Coverage still matters, but readers come for the findings; the header line and the qualified headline carry the essential caveat up front.

### Infer strategic direction for startups, not for large companies
For a startup, the patent record is a dated, inventor-attributed log of what the engineering team worked on. Vocabulary shifts, new inventor teams, areas that stop getting new inventions, continuation intensity and recent provisional titles reveal pivots and priorities (e.g., a startup whose early filings describe industrial IoT hardware and whose later filings shift to consumer devices and carrier services). For large companies, filing volume reflects legal budgets, acquisitions and many separate business units, so the skill limits inference to trends within the searched subject area.

### Competitor comparison is lighter than the primary analysis
Competitors (optional third argument) go through entity confirmation, search, metadata, abstract-based relevance filtering and categorization, but get no per-filing summaries, inventor profiles or appendix. They are mapped onto the primary company's categories (plus up to 3 competitor-only categories) so the comparison is like-for-like. There is a hard cap of 3 competitors and 100 filings per competitor, with no override, because each competitor multiplies USPTO and Google Patents calls.

### Filing-activity chart counts by U.S. filing date
The chart counts CSV rows by filing year, stacked by status, with the most recent ~18 months shaded as incomplete because most of those filings aren't published yet. Without the shading, every chart would show a misleading recent drop-off. Continuations are counted in the year they were filed.

### Exclude obvious false positives manually
Patent assignment records occasionally contain data errors — an application assigned to a company that clearly doesn't belong to them (e.g., US7566599, an IBM semiconductor transistor patent, appeared in Tropos's assignment history). The relevance filter step relies on Claude's judgment to identify and exclude these rather than trying to automate it with rules.

### Summaries and categories are Claude-generated, not templated
Patent abstracts are written in legal language that is deliberately opaque. Rule-based summarization produces poor results. The value of Claude-generated summaries is the translation from "A method is disclosed comprising..." into plain language that explains the actual problem being solved and why the approach is notable.

---

## Known limitations

### HTTP 404 from the ODP API means zero results, not an error
The USPTO ODP API returns HTTP 404 (not HTTP 200 with an empty array) when a search query matches no records. This is intentional API behavior, not a server error. Any code that calls the ODP API must catch `HTTPError` with code 404 and treat it as an empty result set. Unhandled, it will surface as a script failure and silently drop valid search terms from the results.

### Title-keyword searches produce systematic false positives
The ODP API does not expose abstract text as a searchable field, so Step 3 uses invention title keywords to identify candidate patents. Titles are written to be broad and claim-covering; they reliably include false positives in three recurring patterns:

- **Sensor hardware vs. communications** — Terms like "antenna", "radio", "transceiver", and "wireless" appear in sensing/radar patents that use RF for detection, not data communication. The title gives no reliable signal; the abstract does.
- **Polysemous keywords** — "Mesh" matches network topology and structural/material patents. "Antenna" matches communication antennas and physical mounting structures. Abstract review is required to resolve the ambiguity.
- **Same legal name, different company** — `assignmentBag` queries can return patents from an unrelated prior entity that used the same legal name before the target company was founded. These patents typically describe a completely different industry.

**The correct mitigation is to base the relevance filter in Step 4 on the abstract, not the title.** Title keywords are only used in Step 3 as a rough first pass to limit the candidate set to a practical size for large portfolios (>200 patents); they do not determine which patents are retained. Every candidate's abstract must be read before a retain/discard decision is made.

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
- [ ] Portfolio comparison: run two companies side-by-side and identify overlapping areas (patent landscape analysis)
- [ ] Trend analysis: group patents by filing year and category to visualize how a company's research focus shifted over time

### Patent value / importance scoring (future enhancement)

A composite value score per patent would let the report highlight the most important patents rather than treating all retained patents equally. Several signals are available; none is definitive on its own.

**Independent claim breadth** — the strongest signal and fully parseable from claim text on Google Patents. Two sub-metrics:
- *Word count per independent claim*: shorter = broader = harder to design around. A 12-word independent claim is more valuable than a 150-word one, all else equal.
- *Number of independent claims*: more independent claims means more angles of coverage, each requiring its own design-around. Many short independent claims is the strongest pattern.
- A long claim with many "wherein" clauses signals that the examiner repeatedly rejected broader versions — a proxy for a crowded prior art space.

**International filing depth** — expensive filing decisions are a revealed-preference signal of value. Tiers:
- US-only: baseline
- PCT filed: speculative signal; many PCT applications are abandoned in national phase
- Granted national phase entries (EPO, JPO, China, Korea, etc.): strong signal — each costs $5–20k+ in attorney fees; companies only do this for strategically important patents
- International family size is shown directly on Google Patents pages — no additional API needed.

**Maintenance fee status** — whether the patent is still in force. In the US, maintenance fees are due at 3.5, 7.5, and 11.5 years. Early lapse is a clear revealed-preference signal of low value; paying through expiry signals ongoing commercial relevance.

**Litigation and IPR history** — adversarial signals:
- Patent asserted in litigation: owner valued it enough to stake legal costs
- Survived IPR (inter partes review): an adversary paid ~$30k to kill it and failed — strong quality signal
- These are sparse (most patents are never litigated) but high-confidence when present

**Forward citations — use with caution** — the academic citation analogy is weaker here due to conflicting incentives. Companies are advised by counsel not to do extensive prior art searches (to avoid willful infringement exposure and treble damages), so citation counts are systematically suppressed in ways unrelated to patent importance. *Examiner-added* forward citations (where the USPTO examiner cited the patent during prosecution of a later application) are a somewhat cleaner signal than total forward citations, since examiners aren't subject to the same incentive distortion.

**Implemented: per-patent claim analysis.** The skill now does the first step of the strength analysis for each filing (Step 4 claim fetch, CSV claim columns, and a "Portfolio strength" report section):
- Total number of claims
- Number of independent claims
- Word count of each independent claim (shortest independent claim is the headline breadth figure)
- Count of limiting clauses ("wherein", "such that", "comprising") per independent claim
- A short plain-English note on how general the broadest claim is: what a competitor would have to do to infringe, and how easy it is to design around

Breadth is rated Broad / Moderate / Narrow by reading the broadest independent claim, with word count only as a starting guide. Pending applications are rated provisionally because claims change during examination. Claims are fetched for the primary company only, never for competitors, to keep call volume bounded. The remaining signals below (international filing depth, maintenance fees, litigation and IPR, citations) and a composite score are still future work.

**Implementation notes:**
- Claim text for pending applications: USPTO ODP `/applications/{n}/documents` lists a `CLM` (Claims) document with an XML download, the same mechanism used for abstracts not yet on Google Patents
- Claim text and international family data: both available from Google Patents pages — could be added to `fetch_abstracts.py` or a new `fetch_claims.py` script
- Maintenance status: available from USPTO ODP API (`applicationStatusDescriptionText`)
- Litigation/IPR history: requires a separate data source (Derwent, Lex Machina, or web search per patent)
