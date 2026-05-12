"""
Fetch patent abstracts from Google Patents for a list of US patent numbers.

Usage:
    python3 fetch_abstracts.py metadata.json
    python3 fetch_abstracts.py metadata.json --output abstracts.json

Reads a metadata JSON file (output of fetch_metadata.py) and fetches the abstract
for each entry that has a patentNumber. Writes a JSON object mapping patent number
to abstract text.
"""

import sys
import json
import re
import time
import urllib.request
import argparse


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def fetch_abstract(patent_number: str) -> str | None:
    url = f"https://patents.google.com/patent/US{patent_number}/en"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"ERROR:{e}"

    # Try several patterns Google Patents uses for the abstract
    patterns = [
        r'<section[^>]*itemprop="content"[^>]*>.*?<div[^>]*class="abstract[^"]*"[^>]*>(.*?)</div>',
        r'<abstract[^>]*>(.*?)</abstract>',
        r'"description">\s*<p>(.*?)</p>',
        r'<meta name="description" content="([^"]{50,})"',
    ]
    for pattern in patterns:
        m = re.search(pattern, html, re.DOTALL)
        if m:
            text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if len(text) > 50:
                return text[:1000]
    return None


def main():
    parser = argparse.ArgumentParser(description="Fetch patent abstracts from Google Patents")
    parser.add_argument("metadata", help="metadata.json file from fetch_metadata.py")
    parser.add_argument("--output", help="Write abstracts JSON to this file (default: stdout)")
    parser.add_argument("--delay", type=float, default=0.8, help="Seconds between requests (default: 0.8)")
    args = parser.parse_args()

    with open(args.metadata) as f:
        records = json.load(f)

    patent_numbers = [r["patentNumber"] for r in records if r.get("patentNumber")]
    print(f"Fetching abstracts for {len(patent_numbers)} patents...", file=sys.stderr)

    abstracts = {}
    for i, pnum in enumerate(patent_numbers):
        abstract = fetch_abstract(pnum)
        abstracts[pnum] = abstract
        ok = "OK" if abstract and not str(abstract).startswith("ERROR") else abstract
        print(f"  [{i+1}/{len(patent_numbers)}] US{pnum}: {str(ok)[:60]}", file=sys.stderr)
        if args.delay:
            time.sleep(args.delay)

    ok_count = sum(1 for v in abstracts.values() if v and not str(v).startswith("ERROR"))
    print(f"\nGot {ok_count}/{len(patent_numbers)} abstracts", file=sys.stderr)

    output = json.dumps(abstracts, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
