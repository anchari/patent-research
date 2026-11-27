---
name: patent-search
description: Look up US patents and patent applications assigned to a company in a subject area, generate readable summaries, create logical categories, and export to a CSV.
argument-hint: [company name] | [subject area] | [optional: competitor 1, competitor 2, competitor 3]
---

The user wants to research the patent portfolio for a specific company and subject area:

$ARGUMENTS

If the line above is empty or still reads literally as a `$ARGUMENTS` placeholder (agents that don't substitute arguments), take the request from the user's message instead. Accept either the `company | subject | competitors` form or plain language ("Waymo's wireless patents, compared with Tesla"). If the company or subject is missing, ask before doing anything else.

**Paths.** This skill lives in `skills/patent-search/` inside the patent-research repo, usually symlinked into the agent's skills folder. Resolve the symlink to find the repo root (two levels above this file). The scripts and `odp_client.py` live there: run them from the repo root, or by absolute path, regardless of the current working directory. `assets/` (next to this file) holds the report annotation layer.

Parse the request to identify:
- **Company name**: the exact legal name or common name used in USPTO records (e.g., "Apple Inc", "3M Company", "International Business Machines")
- **Subject area**: the technology or topic to search within (e.g., "noise cancellation", "battery technology", "large language models")
- **Competitors** (optional, third `|`-separated field, comma-separated): companies whose portfolios to compare against in the same subject area.

**Hard cap: at most 3 competitors.** If more are given, stop before any searching and ask the user to choose 3. There is no override. Each competitor multiplies the API and Google Patents calls.

---

## Patent status terminology (use consistently in every output)

Never use "patents" loosely to mean "everything found". Every count, CSV row and report statement must say which of these stages it refers to:

| Stage | Public? | Visible to this skill? | Meaning |
|---|---|---|---|
| **Issued patent** | Yes | Yes | Granted and enforceable. |
| **Published application (pending)** | Yes | Yes | Nonprovisional published by the USPTO (normally ~18 months after earliest priority date), still under examination. Not enforceable. |
| **Published application (abandoned)** | Yes | Yes, excluded by default | Published, then dropped. |
| **Unpublished (confidential) nonprovisional** | No | No | Pending but not yet published (inside the 18-month window, or filed with a non-publication request). |
| **Provisional application** | No | Title only, once claimed | Placeholder that secures a filing date for 12 months. Never examined or published. ODP lists a provisional (type `PROVSNL`, usually "Provisional Application Expired") once a published filing claims priority to it; the titles hint at upcoming work. Unclaimed provisionals are invisible. |
| **Foreign patents and applications** | Varies | Partly | EPO and national offices are outside this USPTO-based search. PCT applications filed through the U.S. receiving office do appear in ODP (type `PCT`). |

Provisional and PCT records found in ODP are never CSV rows. Count them, and use the most recent provisional titles, in the coverage section.

Consequences:
- The search sees issued patents and published applications only. It can never give a company's total filings.
- Recent activity is systematically under-counted: anything filed in roughly the last 18 months is mostly invisible, and provisionals are invisible until a published filing claims them.
- Absence of published filings in an area means "no public patents", not "no filings".

---

## USPTO ODP access rules (apply to every ODP call)

ODP allows **one request in flight per API key** (concurrent calls with the same key are blocked with HTTP 429) and 4–15 requests per second depending on call type. The Documents API (`/applications/{n}/documents` and its downloads) has a weekly cap of 1.2 million calls; no run comes close.

- **Never send ODP calls in parallel.** No parallel tool calls that hit `api.uspto.gov`, no backgrounded `curl`s, no thread pools.
- **Route every call through the repo's rate-limited client.** Use the scripts (`fetch_patents.py`, `fetch_metadata.py`), or, for ad hoc calls (entity discovery, claim and document downloads), Python that imports `odp_get` / `odp_get_json` from `odp_client.py` in the repo root. The client holds a machine-wide lock, so it also serializes against the web app and other scripts. It enforces at least 0.3s between requests and retries 429s with backoff. The `curl` examples below show query syntax only; don't use raw `curl` loops for bulk calls.
- **Follow download redirects immediately.** Signed download URLs expire within seconds, so never collect download links to fetch later. `odp_get` follows redirects within the same call.
- **Prefer Google Patents for document text** (abstracts, claims). Use the ODP Documents API only for filings Google Patents doesn't have yet.

## Step 1 — Discover and confirm assignee entity names

Patent records use precise legal entity names that may differ from the company name the user provided, and a company may appear under multiple names (historical renames, subsidiaries, acquired entities).

Use Bash to query the USPTO Open Data Portal API. This requires the user's ODP API key passed as `X-Api-Key`:

```bash
# Search by assignee name text (covers all historical assignees including reassigned patents)
curl -s --get \
  --data-urlencode 'q=assignmentBag.assigneeBag.assigneeNameText:"[Company Name]"' \
  --data-urlencode "limit=5" \
  "https://api.uspto.gov/api/v1/patent/applications/search" \
  -H "X-Api-Key: [API_KEY]"

# Also try first-word variants to surface related entity names
curl -s --get \
  --data-urlencode 'q=assignmentBag.assigneeBag.assigneeNameText:[first word]*' \
  --data-urlencode "limit=5" \
  "https://api.uspto.gov/api/v1/patent/applications/search" \
  -H "X-Api-Key: [API_KEY]"
```

From the results, inspect the `assignmentBag[].assigneeBag[].assigneeNameText` fields to find all unique entity names related to the target company. Exclude obvious false matches.

**Ask the user for their ODP API key** if not already provided. The key is passed as the `X-Api-Key` header on every request to `api.uspto.gov`.

Present the list to the user:

> I found the following legal entity names in USPTO records that appear to be related to **[Company Name]**. Which should I include in the patent search?
>
> - [ ] Entity Name A
> - [ ] Entity Name B (possibly a subsidiary or acquired company)
> - [ ] Entity Name C (historical name before [year] rename)
>
> I've pre-selected the ones that look most likely — let me know if you'd like to add or remove any.

Pre-select the most obvious matches. Wait for the user's confirmation before continuing. Use all confirmed entity names in all subsequent searches.

**Competitors:** run the same entity discovery for each competitor and present all companies' entity lists in one confirmation, so the user approves everything at once.

---

## Step 2 — Generate and confirm search terms

Before searching, generate a comprehensive set of search terms that cover the stated subject area. Patent terminology often differs from common usage, so include:
- The exact phrase the user gave
- Technical synonyms and related terms
- Upstream/downstream concepts (e.g., "mesh topology" if the topic is "wireless mesh")
- Alternative naming conventions used in academic or standards literature

Present the terms to the user in a compact list:

> Here are the search terms I'll use to find patents related to **[subject area]** for **[Company Name]**:
> - [term 1]
> - [term 2]
> - [term 3]
> ...
>
> Should I proceed with these, or would you like to add, remove, or change any terms?

Wait for the user's response before continuing. Incorporate any edits they request, then confirm the final term list before moving to Step 3.

---

## Step 3 — Search for patents

Use the USPTO Open Data Portal API to retrieve all applications for each confirmed assignee entity. This is the most comprehensive approach — it finds all issued patents and pending/abandoned applications by assignee name.

**Primary approach — USPTO ODP API:**

```bash
# Get all applications for each confirmed entity (use assignmentBag for maximum coverage)
curl -s --get \
  --data-urlencode 'q=assignmentBag.assigneeBag.assigneeNameText:"[Entity Name]"' \
  --data-urlencode "limit=100" \
  --data-urlencode "offset=0" \
  "https://api.uspto.gov/api/v1/patent/applications/search" \
  -H "X-Api-Key: [API_KEY]"
```

The response contains a `count` field with total matches and `patentFileWrapperDataBag` array. Each item includes `applicationNumberText` and `applicationMetaData`. Paginate with `offset=100`, `offset=200`, etc. if count exceeds 100.

Collect all `applicationNumberText` values. **Deduplicate** across queries.

**For large portfolios (total count > 200):** Fetching abstracts for hundreds of unrelated patents in Step 4 is impractical. Use title keywords to narrow to a manageable candidate set first:

```bash
# Narrow by title keywords — treat this as approximate, not as a relevance filter
curl -s --get \
  --data-urlencode 'q=assignmentBag.assigneeBag.assigneeNameText:"[Entity Name]" AND (applicationMetaData.inventionTitle:[search term] OR applicationMetaData.inventionTitle:[synonym])' \
  --data-urlencode "limit=100" \
  "https://api.uspto.gov/api/v1/patent/applications/search" \
  -H "X-Api-Key: [API_KEY]"
```

Use broad keywords that over-include rather than under-include — the abstract review in Step 4 is the real relevance gate. Title keywords only determine which patents get evaluated; they do not determine which patents are retained.

**Important: HTTP 404 means zero results, not an error.** The USPTO ODP API returns a 404 response (with body `{"code":"404","message":"Not Found"}`) when a query matches no records. This is normal — treat it as an empty result set and continue. Do not abort the search or report it as a failure.

**Supplemental — Google Patents web search (for very small or niche portfolios):**

If the API returns no results for all terms (e.g., very old company predating ODP coverage), fall back to:
- `site:patents.google.com "[Entity Name]" [search term]`
- `[Entity Name] patent [search term] US issued OR published`

Build a working list of up to 100 unique application numbers.

**Competitors:** repeat this step for each competitor with the same confirmed search terms (title keywords included if the subject area is narrower than the full portfolio). Apply the same 100-filing hard cap per competitor. If a competitor exceeds it, narrow with title keywords; don't raise the cap. Then run Step 4 (metadata, abstracts, relevance filter, status classification) on competitor filings too.

---

## Step 4 — Fetch patent details

For each application number in your list, use the USPTO ODP metadata endpoint via Bash to retrieve structured details:

```bash
curl -s \
  "https://api.uspto.gov/api/v1/patent/applications/[applicationNumberText]/meta-data" \
  -H "X-Api-Key: [API_KEY]"
```

From the `applicationMetaData` object, extract:
- `patentNumber` — if present, the patent was issued (format it as `US{patentNumber}B2`)
- `inventionTitle` — official title
- `inventorBag[].inventorNameText` — full inventor names
- `grantDate` — for issued patents (year is the first 4 chars)
- `filingDate` / `earliestPublicationDate` — for published applications
- `applicationStatusDescriptionText` — "Patented Case", "Abandoned", "Pending", etc.

**For abstracts:** The metadata endpoint does not return abstracts. Fetch abstracts from Google Patents:
```
https://patents.google.com/patent/US[patentNumber]/en
```
Extract the abstract text from the page. Fetch in batches with a short delay (0.5–1s between requests) to avoid rate limiting.

**Assignee verification:** Check `assignmentBag[].assigneeBag[].assigneeNameText` and confirm at least one entry matches the confirmed entities. Discard if it doesn't.

**Relevance filter:** Base the relevance decision on the **abstract**, not the title. Titles are written to be broad and claim-covering; they often match search terms that don't reflect the invention's actual subject. The abstract describes what the invention actually does and is the correct basis for inclusion or exclusion.

Read each abstract and ask: does this patent address a problem or technique within the stated subject area? If not, discard it regardless of what the title says.

Watch for these common false positive patterns that title-based searches cannot distinguish:

- **Sensor hardware vs. communications** — Terms like "antenna", "radio", "transceiver", and "signal" appear in both wireless communications patents and sensing/radar patents. An abstract describing phased-array radar returns or LIDAR signal processing is not a wireless communications patent. Check whether the abstract describes communicating data between systems (relevant) or measuring/detecting physical phenomena (not relevant, unless sensing is the subject area).
- **Same legal name, different company** — A company recently founded or rebranded may share a legal name with an older unrelated entity whose patents remain in assignment records. If the abstract describes a completely different industry (e.g., consumer goods, medical devices), discard the patent.
- **Polysemous keywords** — "Mesh" matches network topology patents and structural/material patents. "Antenna" matches communication antennas and physical mounting structures. "Radio" matches wireless RF communication and RF sensing. The abstract resolves the ambiguity; the title does not.

**Status classification** (use these exact labels):
- `applicationStatusDescriptionText` contains "Patented Case" or "Patent Expired" → Status = "Issued"
- Has a publication number (`earliestPublicationNumber`), no `patentNumber`, and status is not abandoned → Status = "Published Application (Pending)"
- Status contains "Abandoned" → Status = "Published Application (Abandoned)"; exclude unless the user specifically requested abandoned applications
- No `patentNumber` and no publication number → unpublished; exclude it from the CSV, but count it in the coverage section

**Claims (issued patents of the primary company only):** for every retained issued patent, fetch the claim text. Skip published applications, because their claims are likely to change during examination. Skip competitor filings too.
- **Issued patents on Google Patents:** from the same Google Patents page as the abstract. Claims sit in `<section itemprop="claims">`, one `<div class="claim">` per claim. A claim containing a `<claim-ref>` is dependent; one without is independent.
- **Recent grants not yet on Google Patents:** from the USPTO file wrapper. Call `GET /api/v1/patent/applications/{applicationNumberText}/documents`, take the latest `CLM` (Claims) document (the claims as issued, not as originally filed), and download its XML option with `odp_get` (it arrives as a tar archive containing the XML). Fetch one patent at a time; never in parallel.

Record per patent: total claims, independent claims, the full text and word count of each independent claim, and the number of limiting clauses ("wherein", "such that", "configured to") in each. Stay within the existing 100-filing cap.

**Public-disclosure check:** if the company is public or has filed for an IPO, search its latest 10-K or S-1 for a patent count disclosure (typically phrased "we held N issued U.S. patents ... N patent applications pending ... including N provisional"). If found, record the figures and the as-of date for the coverage section in Step 8.

---

## Step 5 — Generate readable summaries

For each retained patent, write a 2–3 sentence plain-English summary drawing on the title and abstract:
- **Sentence 1:** What problem or need does this invention address?
- **Sentence 2:** What is the invention — what does it do or how does it work at a high level?
- **Sentence 3 (if needed):** What is notable or distinctive about the approach?

Write for a technically literate reader who is not a lawyer. Avoid patent jargon ("claim", "embodiment", "wherein", "comprising"). Use plain, direct language.

---

## Step 6 — Categorize the portfolio

Review all retained patents holistically. Create between 5 and 12 logical categories that capture the main themes across the portfolio:
- Categories should be distinct and non-overlapping
- Each should have a short descriptive name (e.g., "Signal Processing", "Hardware Integration", "User Interface", "Power Optimization")
- Choose categories that would help someone quickly understand the shape of the portfolio

Assign each patent to 1–2 categories. If a patent clearly spans two themes, list both separated by a semicolon. Do not force patents into more than 2 categories.

---

## Step 7 — Write the CSV

Save a CSV file to the **current working directory** named:
```
[company-slug]-[subject-slug]-patents.csv
```
Where slugs are lowercase, hyphen-separated (e.g., `apple-inc-noise-cancellation-patents.csv`).

The CSV must have exactly these columns in this order:
| Column | Description |
|---|---|
| `number` | Patent or application number (e.g., US10123456B2) |
| `title` | Official patent title |
| `category` | 1–2 categories, semicolon-separated if 2 |
| `summary` | 2–3 sentence readable summary |
| `inventors` | Inventor full names, comma-separated |
| `year` | 4-digit year (grant year for issued; publication year for applications) |
| `status` | "Issued", "Published Application (Pending)", or "Published Application (Abandoned)" (abandoned only if requested) |
| `filed` | U.S. filing date, YYYY-MM-DD (`filingDate`); used for the filing-activity chart |
| `total_claims` | Number of claims as issued (blank for published applications) |
| `independent_claims` | Number of independent claims (blank for published applications) |
| `shortest_independent_words` | Word count of the shortest independent claim (blank for published applications) |
| `claim_breadth` | "Broad", "Moderate" or "Narrow" (see Section 3 of Step 8); blank for published applications |

Properly escape any commas or quotes within field values (standard CSV quoting).

**Competitors** (only if competitors were given): write one more CSV, `[company-slug]-[subject-slug]-competitors-patents.csv`, with columns `company`, `number`, `title`, `category`, `inventors`, `year`, `status`, `filed`. Assign competitor filings to the primary company's Step 6 categories where they fit. Add at most 3 extra categories for competitor work that fits none, so the comparison can show areas where only competitors are active. Competitor filings don't get Step 5 summaries; read their abstracts only to filter for relevance and to categorize.

---

## Step 8 — Write the narrative report

Save a Markdown report to the **current working directory** named:
```
[company-slug]-[subject-slug]-report.md
```
(e.g., `waymo-llc-wireless-communications-report.md`)

The report sections, in this order:

1. Header and overview
2. Where [Company] is innovating
3. Where [Company] is not innovating
4. Portfolio strength (experimental)
5. Coverage: issued patents vs. pending applications
6. Competitive comparison (only if competitors were given)
7. Key inventors and their areas of specialization
8. Summary
9. Appendix: patent reference

**Header and overview**
```
# [Company] — [Subject Area] Patent Portfolio
> Analysis based on N issued U.S. patents and M published, pending U.S. applications, YYYY–YYYY, as visible in USPTO records on [date]. Not included: unpublished applications, provisionals, and foreign filings.
```

Always give issued and published-application counts separately; never combine them into one "patents" number. In the narrative, call an application an application, not a patent.

Follow with 2–3 intro paragraphs: the headline finding, the portfolio's origin (home-grown vs. acquired, from assignment records), and what it says about the company's direction (see "Inferring strategic direction" below). End the overview with the filing-activity chart.

Qualify any headline or summary claim that depends on absence (e.g., "no invention originated at X", "X is not patenting Y") as applying to the public record.

**Filing-activity chart** (end of overview)

Count CSV rows by year of the `filed` date, stacked by status (Issued / Published Application (Pending)). Mark the most recent ~18 months, from the run date, as incomplete: most filings from that window are not public yet, so an apparent drop-off there is an artifact, not a slowdown. Say so in a caption. The caption should also note that continuations are counted in the year they were filed, so heavy continuation activity inflates later years. If invention families were identified (same title or continuation chain), also mark new families per year (first filing in each family) as a line or dots over the bars, and add a `New families` column to the table. The split separates new invention from continuations that widen claim coverage, which is often the more telling trend. Then add one or two sentences reading the trend: ramp-up, plateau, or bursts tied to funding rounds, product launches or acquisitions where known.
- **Markdown:** a compact table, `Year | Issued | Published (pending) | Total`.
- **HTML:** an inline SVG bar chart generated by a short script (no external libraries, so the file stays self-contained), with the incomplete window shaded and labelled. Follow the `dataviz` skill for colors, axes and labels if it's available.
- **With competitors:** add a second chart with one line per company (total filings per year) on shared axes, and the same incomplete-window shading.

**Inferring strategic direction**

For startups and other small, focused portfolios (one company, a few inventor teams, roughly under 150 filings), the patents are a strong signal of business direction, and the report should draw that out. Look for:
- **Vocabulary shifts** over filing years (e.g., "hub" and "data source" giving way to "user equipment" and "carrier"), which signal a change of product or customer.
- **New inventor teams** appearing and old ones disappearing: new hires, acquisitions, or abandoned efforts.
- **Areas that stop receiving new inventions** and get only continuations.
- **Continuation intensity:** families continued repeatedly are ones the company is defending.
- **Recent provisional titles** (Step 3) as the earliest hint of what comes next.

Tie each inference to specific filings and dates, and state it as an inference.

For large companies (many business units, hundreds or thousands of filings), don't infer corporate strategy from patents. Filing volume reflects legal budgets, acquisitions and many separate teams. Limit observations to trends within the searched subject area, and say why the inference is weaker.

**Section 1 — Where [Company] is innovating**

Identify 2–5 meaningful clusters of patents that represent distinct areas of active investment. For each cluster:
- Give it a short descriptive heading
- Explain the underlying technical challenge the patents address
- Describe the technical approach(es) taken, citing specific patent numbers and inventor names
- If multiple patents in the cluster span several years, note the progression — how the approach evolved over time
- Explain why this area is strategically interesting or distinctive

Do not just restate the categories from Step 6. Look for narrative threads that connect patents across categories: a problem that multiple teams are attacking from different angles, a progression from early exploratory work to mature production-ready solutions, or a set of patents that together constitute a complete sub-system. Order clusters so the evolution of the company's focus is visible (e.g., current priorities first, abandoned areas last).

**Section 2 — Where [Company] is not innovating**

Identify 3–5 notable gaps — subject areas adjacent to the portfolio where the company has zero or near-zero patents. For each gap:
- Name the area (e.g., "5G/Cellular connectivity", "WiFi mesh networking", "Satellite uplink")
- State clearly that there are no issued patents or published applications in this area (unpublished filings may still exist)
- Offer a plausible explanation: is this a commodity input purchased from a supplier? A standards-body-defined protocol with nothing proprietary to invent? A strategic choice to rely on infrastructure rather than own it? An area the company has simply deprioritized?

This section requires inference and judgment. Gaps in a patent portfolio are as informative as what's present — they reveal which problems the company treats as solved-by-others and where their differentiation strategy does not extend.

**Section 3 — Portfolio strength (experimental)**

Heading: `## Portfolio strength (experimental)`. Open the section with this note, in italics: *This section is experimental. It rates issued patents only, from a reading of their claims; the method is still being refined, and the results are not a legal opinion on validity or infringement.*

Issued patents only. Published applications are excluded because their claims are likely to change during examination, so conclusions about them would be premature; state how many were excluded.

Assess claim strength patent by patent, then roll up. Breadth here means how much a competitor would have to do to infringe: the fewer and more generic the required elements in the broadest independent claim, the broader the filing.

Rate each filing's broadest independent claim:
- **Broad:** a few essential elements in generic terms; hard to design around. Often under ~100 words.
- **Moderate:** a recognizable technique with some specific limitations; a competitor could design around it with real engineering effort. Often ~100–200 words.
- **Narrow:** many specific limitations (particular parameters, sequences, structures or "wherein" chains); easy to avoid by changing one detail. Often over ~200 words.

Word counts are only a starting point. Base the rating on reading the claim, and note when the two disagree (e.g., a short claim full of unusual terms).

Section contents:
- **Summary table** (issued patents): median total claims, median independent claims, median shortest-independent-claim length, and the count rated Broad / Moderate / Narrow.
- **Broadest patents:** 3–5 issued patents, each with a one-sentence plain-English paraphrase of the broadest independent claim (what doing it would look like) and why it's hard to avoid.
- **By cluster and family:** which Section 1 clusters have the strongest issued claims, and whether issued continuations broaden or narrow the original family's claims. Continuations with broader claims than the parent signal a family the company is actively expanding.
- **Caveats:** international filing depth, maintenance fees and litigation history are not yet included.

For a large portfolio, give full detail for the subject-area patents and keep the summary table for all issued patents.

**Section 4 — Coverage: issued patents vs. pending applications**

Heading: `## Coverage: issued patents vs. pending applications`. Include:
- A short list of the filing stages from the terminology table above, noting which are visible and how many of each were found.
- If a 10-K/S-1 disclosure was found in Step 4, a table reconciling it against this report: category | disclosed count | found | why the difference. Include the disclosure's as-of date.
- What the invisible portion implies: e.g., provisionals are at most 12 months old, unpublished nonprovisionals are mostly under ~18 months old, so a large invisible pipeline signals recent filing activity that the public record doesn't yet show.
- If any provisionals are visible, a table of the most recent ones (filed, title, published follow-on?) as a hint of upcoming work.
- If no disclosure was found, say so and state that recent filings are under-counted by construction.

**Section 5 — Competitive comparison** (only if competitors were given)

- A table: category (rows) × company (columns), with issued / published-application counts in each cell, plus totals and first filing year.
- The multi-company filing-activity chart.
- 3–5 short paragraphs contrasting focus: where they overlap, which areas only one company patents, who filed first in shared areas, relative scale and momentum (recent filing rate), and what the differences suggest about each company's strategy (with the same small-vs-large-company caution as above).
- Cite specific competitor patent numbers when making a point. Competitors get no inventor section and no appendix entries.

**Section 6 — Key inventors and their areas of specialization**

For each inventor who appears on 2 or more patents in the portfolio:
- List their name as a subheading, followed by a one-line characterization of their focus area
- State their filing count (issued and published applications separately) and which categories/clusters they span
- Explain what their cross-category presence (or lack of it) implies about their role — broad systems architect, narrow specialist, team lead on a single problem, etc.
- Note any temporal patterns: are they active on the oldest patents (foundational work), the newest (current frontier), or both?

**LinkedIn profile lookup:** Before writing each inventor's entry, run a web search for their LinkedIn profile:

```
"[Inventor Full Name]" "[Company Name]" linkedin
```

If a LinkedIn URL is found, include it as a link in the inventor's subheading, e.g.:

```
### Pierre-Yves Droz — Sensor architecture and V2P ([LinkedIn](https://linkedin.com/in/...))
```

If the profile page is accessible, extract their current title, employer, and any career history relevant to their patent focus (e.g., prior employers, academic background). Incorporate this into the narrative — 1–2 sentences on their background and how it connects to their patent work.

If no LinkedIn profile is found, note it briefly ("No LinkedIn profile found") rather than omitting the search attempt entirely. Do not fabricate profile details.

**Summary**

2–4 sentences characterizing the portfolio as a whole: what does it reveal about the company's theory of where their engineering creates proprietary value, versus what they buy from the ecosystem? For startups, close with where the company appears to be heading.

**Appendix — Patent Reference**

After the summary, append a full patent listing grouped by category (same categories from Step 6), sorted chronologically within each group. For each patent:

```
[Patent number as a link to patents.google.com/patent/[number]/en] — [Title]
[Status] [Year] · [Inventors, comma-separated]
Claims: [total] total, [independent] independent · Breadth: [Broad/Moderate/Narrow]   (issued patents only; omit this line for applications)

[Summary paragraph from Step 5]
```

This gives the reader a scannable reference for every patent in the portfolio without leaving the document.

**Output format**

Write the report twice — once as Markdown, once as a self-contained HTML file — both to the current working directory:
- `[company-slug]-[subject-slug]-report.md`
- `[company-slug]-[subject-slug]-report.html`

The HTML file must be fully self-contained (no external stylesheets or scripts). Use a minimal inline `<style>` block for readability. Suggested styles:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Company] — [Subject Area] Patent Portfolio</title>
  <style>
    body { max-width: 860px; margin: 40px auto; padding: 0 24px; font-family: Georgia, serif; font-size: 17px; line-height: 1.7; color: #1a1a1a; }
    h1 { font-size: 1.6em; border-bottom: 2px solid #333; padding-bottom: 0.3em; }
    h2 { font-size: 1.3em; margin-top: 2em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }
    h3 { font-size: 1.05em; margin-top: 1.5em; color: #333; }
    blockquote { margin: 0; padding: 0.2em 1em; border-left: 3px solid #ccc; color: #555; font-style: italic; }
    strong { color: #000; }
    a { color: #1a56db; }
  </style>
</head>
<body>
  <!-- report content here -->
</body>
</html>
```

Render all Markdown formatting as equivalent HTML elements (`#` → `<h1>`, `**text**` → `<strong>`, `> text` → `<blockquote>`, etc.).

**Annotation layer:** make the HTML report annotatable by inserting, just before `</body>`:
1. a `<style>` block with the contents of `assets/annotate.css` (in this skill's folder)
2. an empty store, where `{basename}` is the HTML filename without its extension: `<script type="application/json" id="annotations-data">{"version":1,"doc":"{basename}","annotations":[],"deleted":[]}</script>`
3. a `<script>` block with the contents of `assets/annotate.js`, after any other scripts

Inline the file contents so the report stays self-contained, and don't modify the asset files. The reader can then highlight passages and leave comments, which save to a sidecar `{basename}.annotations.json` next to the HTML.

**Responding to comments (later, when asked):** read the sidecar. For each annotation whose latest turn is the user's, answer it properly and append `{"id":"r-<unique>","author":"claude","text":"...","createdAt":"<ISO timestamp>"}` to its `replies`. Never edit or delete the user's entries, and respect the `deleted` list. Write the JSON back to the sidecar and into the HTML's `annotations-data` block. If a comment shows the report is wrong, fix both the HTML and the Markdown report and say so in the reply.

---

## Step 9 — Report to user

After writing the CSV and both report files, tell the user:
1. All output filenames (three, or four with a competitors CSV), the number of issued patents and the number of published applications (stated separately), and what the search cannot see (unpublished applications, provisionals, foreign filings), with any 10-K/S-1 figures for comparison
2. A list of the categories from the CSV, each with a count of patents assigned to it
3. Filing counts by year (from the chart), noting the incomplete recent window
4. The claim-breadth split (Broad / Moderate / Narrow) for issued patents and the broadest patent, noting that the analysis is experimental
5. 1–2 sentences pointing to the most notable finding in the narrative report, and, if competitors were compared, the sharpest contrast
