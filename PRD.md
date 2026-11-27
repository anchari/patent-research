# PRD — Patent Portfolio Research

## Problem statement

Researching a company's patent portfolio is slow, manual work. You have to:

- find every legal entity the company files under, including acquired subsidiaries
- search USPTO by assignee
- discard the false positives that keyword searches drag in
- read abstracts written in legal language to work out what each invention does
- turn the result into something useful for competitive, technical or investment analysis

It's also easy to draw wrong conclusions. The public record misses most recent filings, mixing issued patents with applications overstates protection, and inferring strategy from a large company's filings is unreliable.

This project automates the mechanical steps (entity discovery, search, metadata and document retrieval) and uses an LLM for the steps that need judgment: relevance filtering, plain-English summaries, categorization, and a narrative analysis that is careful about what the public record can and can't show.

## Product vision

The product answers three questions about a company's patents, in increasing depth:

1. **Focus:** what is the company inventing, where isn't it, who are the inventors, and how is that changing? (Shipped.)
2. **Strength:** how much protection do its issued patents actually give? Claim breadth (shipped, experimental), and what the company had to give up during examination to get them (planned).
3. **Dynamics:** how contested and how live is the position? Which families are still being extended through pending continuations, and whose applications are examiners rejecting over the company's patents, or vice versa (planned)?

Each layer stays honest about what the public record can show, and none of it is a legal opinion.

## Target users

- **Primary:** the repo owner, an analyst or investor evaluating companies (often startups) for investment, partnership or competitive research. Comfortable running Claude Code and local Python scripts.
- **Secondary:** researchers and analysts who want a plain-English view of a company's IP strategy without reading dozens of patents.

## Interfaces

| Interface | Role | Spec |
|---|---|---|
| `/patent-search` Claude Code skill | Primary. Interactive, judgment-in-the-loop workflow | `skills/patent-search/SKILL.md` |
| Python scripts (`fetch_*.py`, `odp_client.py`) | Mechanical data-fetch layer used by both interfaces | `README.md`, `DESIGN.md` |
| Local web app | Secondary, **incomplete**. Runs an earlier version of the workflow through a browser UI; not functionally equivalent to the skill | `webapp/PRD.md`, `webapp/DESIGN.md` |

This PRD covers the product as a whole. The web app PRD covers that interface's own requirements.

## Use cases

- **UC-1 — Analyze a company's portfolio** in a subject area or across the full portfolio: what it is inventing, where it isn't, and who the key inventors are.
- **UC-2 — Confirm company identity** before searching: choose which legal entities (renames, subsidiaries, acquisitions) count as the company.
- **UC-3 — Understand coverage:** distinguish issued patents from published applications, and know what the public record can't show (unpublished applications, provisionals, foreign filings). Reconcile against 10-K/S-1 disclosures when they exist.
- **UC-4 — Infer strategic direction** for startups and small, focused portfolios: pivots, priorities and where the company is heading, from how its filings change over time.
- **UC-5 — See filing activity over time**, including new inventions vs. continuations, with the incomplete recent window marked.
- **UC-6 — Compare against competitors** in the same subject area: overlapping and unique areas of focus, timing and momentum.
- **UC-7 — Assess portfolio strength** (experimental): claim counts and claim breadth for issued patents, rolled up to cluster and portfolio level.
- **UC-9 — Spot live continuations** (planned): find families with an issued patent and a pending continuation or continuation-in-part, meaning the owner can still write new claims, possibly aimed at a competitor's product.
- **UC-10 — Weigh prosecution history** (planned): see which issued patents were allowed easily and which needed repeated rejections or heavy narrowing, to judge how much protection each really gives.
- **UC-11 — Map competitive blocking** (planned): see which of the company's patents USPTO examiners have used as primary prior art to reject competitors' claims, and the reverse. Also usable without naming competitors, to discover which companies are being blocked.
- **UC-8 — Keep research private:** run analyses on any company without publishing the results; only chosen example runs go in the public repo.

## Functional requirements

### Discovery and retrieval
- **FR-1.** Discover candidate assignee entity names from USPTO ODP and require user confirmation before searching (all companies, including competitors, confirmed together).
- **FR-2.** Propose search terms for the subject area and require user approval before searching. For a full-portfolio analysis, search by assignee only.
- **FR-3.** Search by assignee across assignment history (`assignmentBag`), so acquired and reassigned patents are found.
- **FR-4.** Fetch per-filing metadata from ODP and abstracts from Google Patents, falling back to the ODP Documents API for filings Google Patents doesn't have yet.
- **FR-5.** Filter relevance by reading the abstract, not the title.

### Status and coverage
- **FR-6.** Label every filing as "Issued", "Published Application (Pending)" or "Published Application (Abandoned)". Abandoned applications are excluded unless requested. Never combine issued and application counts into a single "patents" number.
- **FR-7.** Report what the search can't see: unpublished nonprovisionals, provisionals not yet claimed by a published filing, and foreign filings. List visible provisional titles as hints of upcoming work.
- **FR-8.** For public companies or IPO filers, find the patent-count disclosure in the latest 10-K or S-1 and reconcile it against the search results.
- **FR-9.** Qualify any conclusion drawn from absence (e.g., "not patenting X") as applying to the public record.

### Analysis
- **FR-10.** Write a 2–3 sentence plain-English summary per retained filing, and group filings into 5–12 categories.
- **FR-11.** Identify 2–5 clusters of innovation (ordered from current priorities to abandoned areas) and 3–5 notable gaps.
- **FR-12.** Infer strategic direction for small, focused portfolios from vocabulary shifts, inventor-team changes, areas that stop receiving new inventions, how often families are continued, and recent provisional titles. For large companies, limit inference to trends within the subject area.
- **FR-13.** Profile inventors on 2+ filings, including a LinkedIn lookup, without fabricating details.
- **FR-14.** Chart filing activity by U.S. filing year, split by status, marking new invention families and shading the most recent ~18 months as incomplete.
- **FR-15.** Optional competitor comparison (up to 3 competitors): categorize competitor filings against the primary company's categories and contrast focus, timing and momentum.
- **FR-16.** Experimental portfolio-strength analysis for issued patents only: total and independent claims, shortest independent claim length, and a Broad / Moderate / Narrow breadth rating from reading the broadest independent claim.

### Outputs
- **FR-17.** Produce a CSV and a narrative report in Markdown and self-contained, annotatable HTML, with sections in this order: overview with filing chart; where the company innovates; where it doesn't; portfolio strength (experimental); coverage; competitive comparison (optional); key inventors; summary; patent-reference appendix.
- **FR-18.** If competitors were compared, produce a separate competitor CSV.

### Planned requirements (not yet implemented)

- **PR-1. Exact patent families and live continuations** (UC-9):
  - Build families from the continuity data ODP already returns with each search result (`parentContinuityBag`, `childContinuityBag`). This needs no extra API calls.
  - Replace the current title-based family grouping with these exact families, which also makes the new-vs-continuation split in FR-14 exact.
  - Flag families with at least one issued patent and a pending continuation or continuation-in-part.
  - Report pending children that aren't published, which the parent's continuity data reveals with their filing date and status but no claims. A test on cached data found 2 such unpublished continuations for one company, so FR-7 should reflect this.
  - Present flagged families as monitoring candidates for the reader. Don't recommend legal actions such as third-party preissuance submissions; the report may mention that the mechanism exists.
- **PR-2. Prosecution-history signals for issued patents** (UC-10), feeding the experimental strength analysis (FR-16):
  - **Phase 1, structured data:** from the Office Action Rejection data, count rejections by statute (§101, §102, §103, §112) and non-final vs. final actions, and flag first-action allowances.
  - **Phase 2, text:** from Office Action text retrieval, compare independent claims as filed with claims as issued, and check whether rejections were overcome by argument or by narrowing amendments.
  - Interpret signals alongside claim breadth, not on their own. For example, a first-action allowance can mean strong claims or claims that were narrow from the start.
  - Describe these as prosecution-history signals, not as a legal assessment of estoppel or enforceability.
- **PR-3. Competitive blocking matrix** (UC-11):
  - From enriched citation data, keep only examiner-cited references (form PTO-892) in categories X and Y (primary prior art under §102/§103). Leave out applicant-submitted (IDS) citations and self-citations.
  - For each of the company's issued patents, report which other applicants' claims it was used to reject, how many claims, and when, with the passage the examiner relied on where available.
  - With competitors named, show both directions. Without them, list the top blocked applicants as discovered competitors.
- **PR-4. Data constraints for PR-2 and PR-3:**
  - Respect each source's date coverage. Office-action-derived data starts around 2017–2018 and lags by up to about 180 days, so say so in the report.
  - Route all calls through `odp_client.py` within the existing caps.
  - Confirm current endpoints, field names and rate limits before building (see Open questions).

## Non-functional requirements

- **Hard safety caps, no overrides:** 500 results per search query, 100 filings per company, at most 3 competitors. Exceeding a cap stops cleanly with guidance to narrow the search.
- **USPTO ODP compliance:**
  - one request in flight per API key, machine-wide
  - at least 0.3s between requests
  - HTTP 429 retried with backoff
  - download redirects followed immediately

  Enforced in `odp_client.py`, and in the skill's rules for ad hoc calls.
- **Polite Google Patents scraping:** sequential, with a delay between requests.
- **Privacy:** research outputs are gitignored by default, and only the designated example runs (Tropos, Waymo) are published. Public docs use generic examples, never the companies the owner has researched. API keys live only in the gitignored `.env`.
- **Honesty about uncertainty:** reports state their data date, label inferences as inferences, and mark experimental analyses as experimental.
- **Partial-failure tolerance:** one failed fetch doesn't abort a run.
- **CLI stability:** script flags and output formats stay backward compatible.

## Out of scope

- Legal opinions on validity, infringement or freedom to operate.
- Non-U.S. patent offices (EPO, WIPO, national offices), except noting U.S.-filed PCT applications that appear in ODP. Tracked in the backlog.
- Litigation databases and paid patent data sources.
- Multi-user accounts, hosting or persisted run history (see `webapp/PRD.md`).

## Open questions

- **Office Action and Enriched Citation APIs (PR-2, PR-3):** these moved from developer.uspto.gov to the Open Data Portal in 2026. Confirm the current ODP endpoints, field names (e.g., examiner-cited indicator, citation category, passage location), date coverage and any separate rate limits in the ODP Swagger docs before building.

- **Role of the web app:** is it a personal browser front end for the owner, or the foundation of a multi-user product? The answer decides the web app strategy (see "Web app" in the backlog), and for a multi-user product it raises questions about per-run LLM costs, pricing, accounts and hosting that are out of scope today.

## Roadmap

### Shipped

| Item | Shipped | Notes |
|---|---|---|
| Status labels and coverage section (issued vs. published, provisional, confidential, foreign) | Nov 2026 | FR-6 to FR-9 |
| 10-K/S-1 patent-count reconciliation | Nov 2026 | FR-8 |
| Report section reorder (findings first, coverage after) | Nov 2026 | FR-17 |
| Strategic-direction inference for startups | Nov 2026 | FR-12 |
| Filing-activity chart with new families vs. continuations | Nov 2026 | FR-14; replaces the earlier "trend analysis" idea |
| Competitor comparison | Nov 2026 | FR-15; replaces the earlier "portfolio comparison" idea |
| Claim-breadth analysis, issued patents only (experimental) | Nov 2026 | FR-16; not yet validated on a real run |
| Rate-limited ODP client | Nov 2026 | Non-functional requirements |
| Research outputs private by default | Nov 2026 | Non-functional requirements |

### Next

- **N-1. Validate the claim-breadth analysis** on a real run, tune the Broad / Moderate / Narrow rubric, then decide whether to drop the "experimental" label.
- **N-3. `fetch_claims.py` script:** move claim fetching (Google Patents first, ODP Documents API fallback) out of ad hoc code into a script, like the other fetch steps.
- **N-4. Chart and report-rendering helper:** a script that builds the filing-activity SVG and the HTML report, instead of generating them ad hoc on each run.
- **N-5. Refresh the published examples** (Tropos, Waymo) to the current report format.
- **N-6. Exact families and live continuations (PR-1):** the cheapest of the new capabilities, since the data is already fetched.

### Backlog

Near-term:
- `--since` date filter on `fetch_patents.py` for incremental updates
- Retry with backoff in `fetch_abstracts.py` for Google Patents 503s
- `--include-abandoned` flag on `fetch_metadata.py`
- Surface abstracts from ODP metadata if ODP ever adds them

Medium-term:
- Filing trends by category over time (extends the filing chart)
- Parallel summarization for large portfolios
- Fixed category schemes the user specifies up front, for consistent comparisons across runs
- International coverage via EPO (ops.epo.org) and WIPO (patentscope.wipo.int)

Cost and efficiency (design notes in `DESIGN.md`, "Cost-efficiency design notes"). Ranked by expected impact; measure first (CE-0), and don't ship a cheaper model for a step until it matches the current output on that step:
- **CE-0. Baseline and test set:** record token usage for a typical ~70-filing run, and keep that run's relevance decisions, summaries and categories as the reference to compare cheaper configurations against.
- **CE-1. Keep per-patent reading out of the main conversation** (highest impact): hand relevance filtering, summaries and claim reading to subagents in batches, so the main Opus session sees compact results and never the raw abstracts or claims. This cuts the context that every later turn re-sends.
- **CE-2. Reusable Python for deterministic steps** (high): move work that's currently written ad hoc on each run into scripts: claim fetch and counting, families from continuity data, status and coverage counts, inventor statistics, CSV writing, filing chart and report rendering. Also improves consistency, and the web app could share them. Overlaps N-3, N-4 and PR-1.
- **CE-3. Output hygiene** (high, free): write bulk API responses and abstracts to files and print only compact summaries, so large dumps never enter the conversation.
- **CE-4. Model routing by task** (high, once CE-1 exists): Haiku 5.5 for per-patent extraction (relevance, summaries, later office-action summaries) and inventor lookups; Sonnet 5.5 for per-patent judgment (claim breadth); Opus 5.5 for synthesis (clusters, gaps, strategic direction, comparison, report).
- **CE-5. Effort settings** (medium): low effort for extraction subagents, default or higher for synthesis.
- **CE-6. Caching-friendly structure** (low for the skill, medium for the web app): Claude Code caches the conversation automatically, so the skill's lever is keeping its shared instructions stable and avoiding needless context churn. The web app should add explicit prompt caching to its repeated per-patent instructions.
- **CE-7. Web app quick wins** (only if the web app is kept): switch `claude-opus-5` to Opus 5.5 (newer and cheaper), apply CE-4 and CE-5 to its calls, and consider the Batch API (50% cheaper, asynchronous) for unattended runs.

Web app (on hold until its role is decided; see Open questions). The web app runs an earlier snapshot of the workflow: no competitor field or comparison, status labels, coverage section, current section order, filing chart or claim analysis. It shows an "incomplete" notice. Its judgment steps re-implement the skill's instructions as separate Anthropic API calls, so every skill change has to be ported by hand. Candidate strategies, detailed in `webapp/PRD.md` ("Future direction"):
- **A. Run the skill itself** through the Claude Agent SDK, with the web UI handling the confirmation checkpoints. One source of truth and a thin web app, but likely several times the per-run cost of the current web app (roughly a terminal skill run), and possibly billed differently.
- **B. Shared deterministic scripts plus shared judgment instructions.** Move status labels, coverage counts, CSV format, chart and report rendering into scripts both interfaces use (overlaps N-3 and N-4), and load the judgment prompts from files shared with the skill. Keeps runs cheap; the web app still needs some code for new steps.
- **C. Measure first:** run the same company through both interfaces and compare token usage and cost, to ground the choice.

Portfolio dynamics and prosecution history (after the open questions are resolved):
- Prosecution-history signals, phase 1 structured data then phase 2 text (PR-2)
- Competitive blocking matrix, including competitor discovery (PR-3)

Portfolio strength, beyond claims (design notes in `DESIGN.md`, "Patent value / importance scoring"):
- International filing depth (PCT, granted national-phase entries)
- Maintenance-fee status
- Litigation and IPR history
- Examiner-added forward citations (largely covered by PR-3's examiner-cited X/Y filter)
- A composite strength score

### Ideas (not committed)

- **Essential-element count:** record how many separate requirements a claim imposes while reading it, as a better breadth figure than counting "wherein" clauses. This would capture nested requirements (e.g., "wherein the apparatus contains X and Y" adds two), which word-matching can't do reliably because "and", "or" and descriptive phrases behave differently.
