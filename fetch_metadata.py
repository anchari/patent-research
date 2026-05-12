"""
Fetch patent metadata for a list of USPTO application numbers.

Usage:
    python3 fetch_metadata.py app_numbers.txt YOUR_API_KEY
    python3 fetch_metadata.py app_numbers.txt YOUR_API_KEY --output metadata.json

Reads application numbers from a file (one per line) or stdin ("-").
Writes a JSON array to stdout or a file.
"""

import sys
import json
import time
import urllib.request
import argparse


def fetch_metadata(app_number: str, api_key: str) -> dict:
    url = f"https://api.uspto.gov/api/v1/patent/applications/{app_number}/meta-data"
    req = urllib.request.Request(url, headers={"X-Api-Key": api_key})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    items = data.get("patentFileWrapperDataBag", [])
    if not items:
        return {"applicationNumberText": app_number, "error": "no data"}
    item = items[0]
    meta = item.get("applicationMetaData", {})

    inventors = [
        inv.get("inventorNameText", "")
        for inv in meta.get("inventorBag", [])
    ]
    assignees = []
    for ab in item.get("assignmentBag", []):
        if isinstance(ab, dict):
            for a in ab.get("assigneeBag", []):
                if isinstance(a, dict):
                    name = a.get("assigneeNameText", "")
                    if name and name not in assignees:
                        assignees.append(name)

    return {
        "applicationNumberText": app_number,
        "patentNumber": meta.get("patentNumber", ""),
        "title": meta.get("inventionTitle", ""),
        "status": meta.get("applicationStatusDescriptionText", ""),
        "grantDate": meta.get("grantDate", ""),
        "filingDate": meta.get("filingDate", ""),
        "pubNumber": meta.get("earliestPublicationNumber", ""),
        "inventors": inventors,
        "assignees": assignees,
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch USPTO patent metadata by application number")
    parser.add_argument("input", help="File of application numbers (one per line), or - for stdin")
    parser.add_argument("api_key", help="USPTO ODP API key")
    parser.add_argument("--output", help="Write JSON results to this file (default: stdout)")
    parser.add_argument("--delay", type=float, default=0.1, help="Seconds between requests (default: 0.1)")
    args = parser.parse_args()

    if args.input == "-":
        app_numbers = [line.strip() for line in sys.stdin if line.strip()]
    else:
        with open(args.input) as f:
            app_numbers = [line.strip() for line in f if line.strip()]

    results = []
    for i, app_num in enumerate(app_numbers):
        try:
            result = fetch_metadata(app_num, args.api_key)
        except Exception as e:
            result = {"applicationNumberText": app_num, "error": str(e)}
        results.append(result)

        patent_num = result.get("patentNumber", "")
        label = f"US{patent_num}" if patent_num else "(no patent)"
        print(f"  [{i+1}/{len(app_numbers)}] {app_num} → {label}  {result.get('status','')[:30]}", file=sys.stderr)

        if args.delay:
            time.sleep(args.delay)

    output = json.dumps(results, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        errors = sum(1 for r in results if "error" in r)
        patented = sum(1 for r in results if r.get("patentNumber"))
        print(f"\n{patented} issued patents, {errors} errors. Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
