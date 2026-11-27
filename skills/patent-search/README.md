# patent-search

An agent skill (built for Claude Code; adaptable to Codex, Gemini CLI and other agents that read `SKILL.md`) that researches US patents and patent applications for a company in a given subject area, summarizes each one in plain English, groups them into logical categories, and exports the results to a CSV.

## Usage

```
/patent-search [company name] | [subject area]
```

**Examples:**
```
/patent-search Meta Platforms | augmented reality
/patent-search 3M Company | noise cancellation
/patent-search International Business Machines | quantum computing
```

In agents without slash-command arguments, ask in plain language, e.g. "Use the patent-search skill to analyze Meta Platforms' augmented reality patents". Install steps for each agent are in the repo's main `README.md`.

## Prerequisites

You need a **USPTO Open Data Portal (ODP) API key**. Get one free at [data.uspto.gov](https://data.uspto.gov/apis/getting-started). The skill will ask for it at the start of Step 1.

## What it does

1. **Finds the right legal entities** — queries the USPTO ODP API to surface all assignee names matching the company (e.g., both "Facebook Inc" and "Meta Platforms Inc"), then asks you to confirm which to include
2. **Generates search terms** — proposes synonyms and related technical terms for the subject area and asks for your approval before searching
3. **Retrieves the full patent list** — uses the USPTO ODP API to enumerate every application ever assigned to the confirmed entities, then filters by subject area — no sampling, no web scraping
4. **Fetches metadata and abstracts** — pulls structured data (patent number, inventors, grant date, status) from the ODP API and abstracts from Google Patents
5. **Summarizes each patent** — writes a 2–3 sentence plain-English description of what the invention is and why it matters
6. **Categorizes the portfolio** — groups patents into 5–12 logical themes
7. **Exports a CSV** — saved to the current working directory as `[company]-[subject]-patents.csv`

## CSV columns

| Column | Description |
|---|---|
| `number` | Patent or application number (e.g., US10123456B2) |
| `title` | Official patent title |
| `category` | 1–2 category labels, semicolon-separated |
| `summary` | 2–3 sentence plain-English summary |
| `inventors` | Inventor names, comma-separated |
| `year` | Year granted (issued patents) or published (applications) |
| `status` | "Issued" or "Published Application" |

## Tips

- **Use the legal name, not the brand**: Search for "Meta Platforms Inc" not just "Meta" — the USPTO uses precise legal entity names. The skill's assignee discovery step will help surface the right ones.
- **Be specific with the subject area**: "wireless mesh networking" will give better results than "networking". The skill will suggest synonyms, but a focused starting point helps.
- **Historical patents**: Companies that rebranded (e.g., Google → Alphabet, Facebook → Meta) will have patents under older names — the assignee confirmation step is where you include those.
- **Acquired companies**: Patents originally filed by an acquired company stay under the original assignee name in USPTO records even after the acquisition. Include both the acquired and acquiring entity names to get the full picture.
- **Cap**: The skill retrieves up to 100 patents per run. For very prolific filers in a broad area, consider narrowing the subject area or running multiple focused searches.
