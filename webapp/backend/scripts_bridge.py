"""
Bridges the web backend to the existing root-level CLI scripts.

Adds the repo root to sys.path and re-exports the scripts' already-decomposed
core functions unmodified. The scripts themselves are never edited, so their
command-line behavior (`python3 fetch_patents.py ...`) is unaffected — see
PRD FR-13 / DESIGN.md "Reuse by direct import, zero script edits". All ODP
requests, including discover_entities below, go through the shared, rate-limited
odp_client (PRD NFR "USPTO ODP rate limits").
"""

import sys
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fetch_patents import fetch_applications, MAX_RESULTS  # noqa: E402
from fetch_metadata import fetch_metadata  # noqa: E402
from fetch_abstracts import fetch_abstract  # noqa: E402
from odp_client import odp_get_json  # noqa: E402

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
    names: list[str] = []

    queries = [f'assignmentBag.assigneeBag.assigneeNameText:"{company_name}"']
    first_word = company_name.split()[0] if company_name.split() else company_name
    if first_word.lower() != company_name.lower():
        queries.append(f"assignmentBag.assigneeBag.assigneeNameText:{first_word}*")

    for query in queries:
        try:
            data = odp_get_json(base_url, api_key, {"q": query, "limit": 10})
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
