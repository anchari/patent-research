# PRD — Patent Search Web App

> **Status: incomplete.** This app implements an earlier version of the `/patent-search` workflow and is not functionally equivalent to the skill in Claude Code. See "Future direction" below and the root `PRD.md` roadmap.

## Problem Statement

The patent portfolio research workflow in this repo (`skills/patent-search/` + the `fetch_*.py` scripts) today only runs inside an interactive Claude Code session: the user has to open Claude Code, invoke `/patent-search`, and drive a chat-based back-and-forth through company disambiguation, keyword approval, and result review. There's no way to kick off or monitor a run from a plain browser tab without a Claude Code session open.

This project wraps the existing workflow in a local web app so the same interactive, judgment-in-the-loop process — confirm company entity names, approve search keywords, review categorization — happens through a UI instead of a chat transcript.

## Target Users

A single user (the repo owner): technical enough to run a local Python app and set environment variables, but wants a form-and-progress-bar UI rather than a conversational skill for routine runs.

## Use Cases

- **UC-1 — Start a run.** User enters a company name and a subject area in a web form and starts the pipeline.
- **UC-2 — Confirm company identity.** App proposes the legal entity name(s) it found for the company via USPTO assignee search (including acquired subsidiaries); user reviews and approves/edits the list before search proceeds.
- **UC-3 — Approve search keywords.** App proposes keyword synonyms for the subject area; user reviews and edits the list before the patent fetch runs.
- **UC-4 — Watch the pipeline run.** App fetches patents, metadata, and abstracts, then filters, summarizes, and categorizes; user sees live per-stage progress (e.g. "Fetching abstracts... 34/62").
- **UC-5 — Review categorization.** App proposes 5–12 categories and a plain-English summary per retained patent; user reviews the result before the final report is generated.
- **UC-6 — Export results.** User downloads the finished CSV, narrative report (Markdown), and self-contained HTML report for the run.

## Functional Requirements

- **FR-1.** Web form to start a run: company name + subject area. No API key entry in the UI (see FR-11).
- **FR-2.** Backend queries USPTO for candidate legal entity names for the company (assignee search) and presents them for user approval/edits before proceeding — mirrors the existing skill's disambiguation step.
- **FR-3.** Backend calls the Anthropic API to propose keyword synonyms for the subject area; UI shows an editable list requiring explicit user approval before search.
- **FR-4.** Backend runs the fetch pipeline (patents → metadata → abstracts) by reusing the existing `fetch_patents.py` / `fetch_metadata.py` / `fetch_abstracts.py` logic rather than reimplementing it.
- **FR-5.** Backend calls the Anthropic API to filter each candidate patent for genuine relevance using its abstract, discarding false positives (title-keyword matches alone are not sufficient, per existing design).
- **FR-6.** Backend calls the Anthropic API to write a 2–3 sentence plain-English summary per retained patent.
- **FR-7.** Backend calls the Anthropic API to propose 5–12 logical categories and assign each retained patent to 1–2 of them; UI presents this for user review before finalizing.
- **FR-8.** Backend generates the narrative report (Markdown + self-contained HTML, including the patent-reference appendix) matching the structure defined in `skills/patent-search/SKILL.md`.
- **FR-9.** UI shows live status/progress through each pipeline stage so the user isn't staring at a blank screen during multi-minute runs.
- **FR-10.** On completion, user can download the CSV, `report.md`, and `report.html` for the run directly from the browser.
- **FR-11.** USPTO and Anthropic API keys are read from local environment variables (`.env`, gitignored) on backend startup — never entered or stored via the UI.
- **FR-12.** The app enforces the same hard, non-overridable 500-result cap on bulk USPTO queries as the existing scripts. This is a safety invariant, not a configurable limit — no UI control, flag, or override raises it.
- **FR-13.** The existing command-line invocation is fully preserved: `fetch_patents.py`, `fetch_metadata.py`, and `fetch_abstracts.py` remain runnable standalone from the terminal with their current arguments and output exactly as documented in the root `README.md`, and the `/patent-search` Claude Code skill continues to work unchanged. The web app is a second interface onto shared logic, not a replacement for the first — any refactor needed to share code between the CLI scripts and the web backend must not change existing CLI behavior, flags, or output formats.

## Non-Functional Requirements

- **Single local user.** No authentication, no multi-tenancy. The server binds to localhost only.
- **Ephemeral runs.** Each run lives for the duration of the browser session; the app does not maintain a searchable history of past runs. Output files are available as downloads at the end of a run — the user decides whether to save them into the repo's `data/` folder following the existing project convention.
- **Latency.** A typical run (15–60 patents, based on the two committed examples) involves one Anthropic API call per pipeline stage plus one relevance-filter and one summary call per candidate patent, and can take a few minutes end-to-end. Progress feedback (FR-9) is required so this doesn't read as a hang.
- **Partial-failure tolerance.** If a single patent's abstract fetch fails, the pipeline skips it and continues, matching the existing script behavior — one bad fetch shouldn't abort the run.
- **USPTO ODP rate limits.** All ODP calls must respect the published limits: one request in flight per API key, and no more than ODP's per-second rate. Concurrent runs (or a run alongside the CLI scripts) must not send parallel requests with the same key. Transient HTTP 429 responses are retried with backoff rather than failing the run.
- **No mid-run resume.** If the browser is refreshed or closed mid-run, the run is lost and must be restarted; the app does not persist in-progress pipeline state.

## Out of Scope (v1)

- Multi-user accounts, authentication, or access control.
- Persisted, browsable history of past runs within the app.
- Resuming a run after a browser refresh or server restart.
- Patent value/importance scoring (tracked in the root `PRD.md` roadmap; independent of this app).
- Hosting or deployment beyond a local machine.
- Changing or removing the existing Claude Code skill or `fetch_*.py` scripts, or altering their CLI behavior — this app is additive and reuses their logic rather than replacing them (see FR-13).

## Future direction (not yet decided)

The app re-implements the skill's judgment steps as its own Anthropic API calls (`backend/llm.py`, `backend/pipeline.py`), following a snapshot of `skills/patent-search/SKILL.md`. Since then the skill has gained competitor comparison, issued-vs-application status labels, a coverage section, a new section order, a filing-activity chart and an experimental claim analysis, none of which the app has. Every future skill change would also have to be ported by hand.

Which strategy to adopt depends on the app's role, still undecided: a personal browser front end for the repo owner, or the foundation of a multi-user product. A multi-user product would also need decisions on per-run LLM cost, pricing, accounts and hosting.

- **A. Run the skill itself via the Claude Agent SDK.**
  - **How:** the backend runs `SKILL.md` without a terminal. Checkpoint questions (entity confirmation, keyword approval) come back through the SDK and are shown as forms, tool calls and messages stream to the progress view, and finished files are served for download.
  - **Pros:** a single source of truth, so skill changes appear automatically, and the backend shrinks to a thin layer.
  - **Cons:**
    - an agent session's context grows over many turns, so a run likely costs several times the current app's (about the same as a terminal skill run)
    - SDK usage may be billed as API tokens rather than under a Claude plan
    - progress is less precisely structured
    - output varies run to run, as in the terminal
- **B. Shared deterministic scripts plus shared judgment instructions.**
  - **How:** move status classification, coverage counts, CSV format, chart drawing and report rendering into scripts both interfaces call. Move each judgment step's instructions into files that both `SKILL.md` and the app's prompts load.
  - **Pros:** keeps the app's cheap, single-purpose calls, and instruction changes reach both interfaces.
  - **Cons:** the app keeps its own orchestration, so new workflow steps (like competitors) still need some app code.
- **C. Measure first.** Run the same company through the current app and the skill, and compare token usage and cost before choosing.

A and B aren't exclusive: B's shared scripts would also make terminal runs more consistent.

