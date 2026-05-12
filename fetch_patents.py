"""
Fetch all patent applications for a company from the USPTO Open Data Portal API.

Usage:
    python3 fetch_patents.py "Tropos Networks" YOUR_API_KEY
    python3 fetch_patents.py "Tropos Networks" YOUR_API_KEY --output app_numbers.txt

Returns a list of application numbers (one per line) to stdout or a file.
"""

import sys
import json
import urllib.request
import urllib.parse
import argparse


def fetch_applications(assignee_name: str, api_key: str) -> list[dict]:
    """
    Fetch all applications where the given name appears as an assignee.
    Uses assignmentBag.assigneeBag.assigneeNameText which covers original filers
    and patents reassigned after filing.
    """
    base_url = "https://api.uspto.gov/api/v1/patent/applications/search"
    headers = {"X-Api-Key": api_key}
    limit = 100
    offset = 0
    all_items = []

    while True:
        params = urllib.parse.urlencode({
            "q": f'assignmentBag.assigneeBag.assigneeNameText:"{assignee_name}"',
            "limit": limit,
            "offset": offset,
        })
        url = f"{base_url}?{params}"
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        total = data.get("count", 0)
        items = data.get("patentFileWrapperDataBag", [])
        all_items.extend(items)

        print(f"  Fetched {len(all_items)}/{total}...", file=sys.stderr)

        if len(all_items) >= total or not items:
            break
        offset += limit

    return all_items


def main():
    parser = argparse.ArgumentParser(description="Fetch USPTO patent applications by assignee name")
    parser.add_argument("assignee", help='Assignee name to search (e.g. "Tropos Networks, Inc.")')
    parser.add_argument("api_key", help="USPTO ODP API key")
    parser.add_argument("--output", help="Write application numbers to this file (default: stdout)")
    args = parser.parse_args()

    print(f"Searching for applications assigned to: {args.assignee}", file=sys.stderr)
    items = fetch_applications(args.assignee, args.api_key)

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
