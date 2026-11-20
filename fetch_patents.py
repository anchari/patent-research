"""
Fetch patent applications for a company from the USPTO Open Data Portal API.

Usage:
    python3 fetch_patents.py "Tropos Networks" YOUR_API_KEY
    python3 fetch_patents.py "Apple Inc" YOUR_API_KEY --keywords "noise cancellation" "audio processing"
    python3 fetch_patents.py "Tropos Networks" YOUR_API_KEY --output app_numbers.txt

Hard cap: retrieves at most 500 results. If the query matches more, the script exits
with an error and instructions to narrow the search using --keywords.

Returns a list of application numbers (one per line) to stdout or a file.
"""

import sys
import urllib.error
import argparse

from odp_client import odp_get_json

MAX_RESULTS = 500


def build_query(assignee_name: str, keywords: list[str]) -> str:
    assignee_clause = f'assignmentBag.assigneeBag.assigneeNameText:"{assignee_name}"'
    if not keywords:
        return assignee_clause
    title_clauses = " OR ".join(
        f"applicationMetaData.inventionTitle:{kw}*" for kw in keywords
    )
    return f"{assignee_clause} AND ({title_clauses})"


def fetch_applications(assignee_name: str, api_key: str, keywords: list[str]) -> list[dict]:
    """
    Fetch applications where the given name appears as an assignee, optionally filtered
    by invention title keywords. Uses assignmentBag query for maximum coverage (includes
    patents reassigned after filing).

    Raises SystemExit if total results exceed MAX_RESULTS.
    """
    base_url = "https://api.uspto.gov/api/v1/patent/applications/search"
    query = build_query(assignee_name, keywords)
    limit = 100
    offset = 0
    all_items = []

    while True:
        try:
            data = odp_get_json(base_url, api_key, {"q": query, "limit": limit, "offset": offset})
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break  # zero results — not an error
            raise

        total = data.get("count", 0)

        if total > MAX_RESULTS:
            kw_hint = (
                f" Try narrowing with --keywords, e.g.:\n"
                f"  --keywords \"[subject area]\" \"[synonym]\""
            )
            sys.exit(
                f"Error: query matches {total} results, which exceeds the {MAX_RESULTS}-patent "
                f"limit. Fetching aborted to avoid excessive API usage.{kw_hint}"
            )

        items = data.get("patentFileWrapperDataBag", [])
        all_items.extend(items)

        print(f"  Fetched {len(all_items)}/{total}...", file=sys.stderr)

        if len(all_items) >= total or not items:
            break
        offset += limit

    return all_items


def main():
    parser = argparse.ArgumentParser(
        description="Fetch USPTO patent applications by assignee name",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("assignee", help='Assignee name (e.g. "Apple Inc")')
    parser.add_argument("api_key", help="USPTO ODP API key")
    parser.add_argument(
        "--keywords",
        nargs="+",
        metavar="TERM",
        help="Filter by invention title keywords (required for large filers)",
    )
    parser.add_argument("--output", help="Write application numbers to this file (default: stdout)")
    args = parser.parse_args()

    keywords = args.keywords or []
    if keywords:
        print(f"Searching: assignee={args.assignee!r}, title keywords={keywords}", file=sys.stderr)
    else:
        print(f"Searching for all applications assigned to: {args.assignee!r}", file=sys.stderr)

    items = fetch_applications(args.assignee, args.api_key, keywords)
    app_numbers = [item["applicationNumberText"] for item in items if item.get("applicationNumberText")]

    lines = "\n".join(app_numbers)
    if args.output:
        with open(args.output, "w") as f:
            f.write(lines + "\n")
        print(f"Wrote {len(app_numbers)} application numbers to {args.output}", file=sys.stderr)
    else:
        print(lines)


if __name__ == "__main__":
    main()
