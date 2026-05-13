---
name: patent-search
description: Look up US patents and patent applications assigned to a company in a subject area, generate readable summaries, create logical categories, and export to a CSV.
argument-hint: [company name] | [subject area]
---

The user wants to research the patent portfolio for a specific company and subject area:

$ARGUMENTS

Parse the arguments to identify:
- **Company name** — the exact legal name or common name used in USPTO records (e.g., "Apple Inc", "3M Company", "International Business Machines")
- **Subject area** — the technology or topic to search within (e.g., "noise cancellation", "battery technology", "large language models")

---

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

**Status classification:**
- `applicationStatusDescriptionText` contains "Patented Case" or "Patent Expired" → Status = "Issued"
- Application has a publication number but no `patentNumber` → Status = "Published Application"
- "Abandoned" → exclude unless the user specifically requested abandoned applications

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
| `status` | "Issued" or "Published Application" |

Properly escape any commas or quotes within field values (standard CSV quoting).

---

## Step 8 — Write the narrative report

Save a Markdown report to the **current working directory** named:
```
[company-slug]-[subject-slug]-report.md
```
(e.g., `waymo-llc-wireless-communications-report.md`)

The report has four sections:

**Header**
```
# [Company] — [Subject Area] Patent Portfolio
> Analysis based on N issued patents and published applications, YYYY–YYYY
```

**Section 1 — Where [Company] is innovating**

Identify 2–5 meaningful clusters of patents that represent distinct areas of active investment. For each cluster:
- Give it a short descriptive heading
- Explain the underlying technical challenge the patents address
- Describe the technical approach(es) taken, citing specific patent numbers and inventor names
- If multiple patents in the cluster span several years, note the progression — how the approach evolved over time
- Explain why this area is strategically interesting or distinctive

Do not just restate the categories from Step 6. Look for narrative threads that connect patents across categories: a problem that multiple teams are attacking from different angles, a progression from early exploratory work to mature production-ready solutions, or a set of patents that together constitute a complete sub-system.

**Section 2 — Where [Company] is not innovating**

Identify 3–5 notable gaps — subject areas adjacent to the portfolio where the company has zero or near-zero patents. For each gap:
- Name the area (e.g., "5G/Cellular connectivity", "WiFi mesh networking", "Satellite uplink")
- State clearly that there are no patents in this area
- Offer a plausible explanation: is this a commodity input purchased from a supplier? A standards-body-defined protocol with nothing proprietary to invent? A strategic choice to rely on infrastructure rather than own it? An area the company has simply deprioritized?

This section requires inference and judgment. Gaps in a patent portfolio are as informative as what's present — they reveal which problems the company treats as solved-by-others and where their differentiation strategy does not extend.

**Section 3 — Key inventors and their areas of specialization**

For each inventor who appears on 2 or more patents in the portfolio:
- List their name as a subheading, followed by a one-line characterization of their focus area
- State their patent count and which categories/clusters they span
- Explain what their cross-category presence (or lack of it) implies about their role — broad systems architect, narrow specialist, team lead on a single problem, etc.
- Note any temporal patterns: are they active on the oldest patents (foundational work), the newest (current frontier), or both?

If you have any reliable background knowledge about the inventor's career history (e.g., they were a founding team member, joined from a known institution, or have a public profile consistent with their patent focus), include a one-sentence note. Mark speculative inferences clearly.

**Closing summary paragraph**

2–4 sentences characterizing the portfolio as a whole: what does it reveal about the company's theory of where their engineering creates proprietary value, versus what they buy from the ecosystem?

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

---

## Step 9 — Report to user

After writing the CSV and both report files, tell the user:
1. All three filenames and the total number of patents included
2. A list of the categories from the CSV, each with a count of patents assigned to it
3. 1–2 sentences pointing to the most notable finding in the narrative report
