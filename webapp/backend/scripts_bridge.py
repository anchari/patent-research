"""
Bridges the web backend to the existing root-level CLI scripts.

Adds the repo root to sys.path and re-exports the scripts' already-decomposed
core functions unmodified. The scripts themselves are never edited, so their
command-line behavior (`python3 fetch_patents.py ...`) is unaffected — see
PRD FR-13 / DESIGN.md "Reuse by direct import, zero script edits".
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fetch_patents import fetch_applications, MAX_RESULTS  # noqa: E402
from fetch_metadata import fetch_metadata  # noqa: E402
from fetch_abstracts import fetch_abstract  # noqa: E402

__all__ = [
    "fetch_applications",
    "fetch_metadata",
    "fetch_abstract",
    "MAX_RESULTS",
    "discover_entities",
]


def discover_entities(company_name: str, api_key: str) -> list[str]:
    """
    Query USPTO for candidate assignee entity names related to company_name.

    Mirrors skills/patent-search/SKILL.md Step 1 (exact-name + first-word-variant
    queries), but this lookup has no equivalent function in the CLI scripts to
    import, so it's implemented directly against the same USPTO ODP endpoint
    fetch_patents.py uses.
    """
    base_url = "https://api.uspto.gov/api/v1/patent/applications/search"
    headers = {"X-Api-Key": api_key}
    names: list[str] = []

    queries = [f'assignmentBag.assigneeBag.assigneeNameText:"{company_name}"']
    first_word = company_name.split()[0] if company_name.split() else company_name
    if first_word.lower() != company_name.lower():
        queries.append(f"assignmentBag.assigneeBag.assigneeNameText:{first_word}*")

    for query in queries:
        params = urllib.parse.urlencode({"q": query, "limit": 10})
        url = f"{base_url}?{params}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise

        for item in data.get("patentFileWrapperDataBag", []):
            for ab in item.get("assignmentBag", []):
                if not isinstance(ab, dict):
                    continue
                for a in ab.get("assigneeBag", []):
                    if not isinstance(a, dict):
                        continue
                    name = a.get("assigneeNameText", "")
                    if name and name not in names:
                        names.append(name)

    return names
