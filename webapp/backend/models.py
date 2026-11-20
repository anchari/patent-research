from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Stage(str, Enum):
    ENTITY_DISCOVERY = "entity_discovery"
    AWAITING_ENTITY_APPROVAL = "awaiting_entity_approval"
    KEYWORD_GENERATION = "keyword_generation"
    AWAITING_KEYWORD_APPROVAL = "awaiting_keyword_approval"
    FETCHING = "fetching"
    FILTERING_SUMMARIZING = "filtering_summarizing"
    AWAITING_CATEGORIZATION_APPROVAL = "awaiting_categorization_approval"
    GENERATING_REPORT = "generating_report"
    DONE = "done"
    ERROR = "error"


class PatentRecord(BaseModel):
    application_number: str
    patent_number: str | None = None
    title: str = ""
    inventors: list[str] = []
    year: str = ""
    status: str = ""
    abstract: str | None = None
    relevant: bool | None = None
    summary: str | None = None
    categories: list[str] = []


class RunState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str
    company: str
    subject: str
    stage: Stage
    candidate_entities: list[str] = []
    approved_entities: list[str] = []
    candidate_keywords: list[str] = []
    approved_keywords: list[str] = []
    patents: list[PatentRecord] = []
    proposed_categories: list[str] = []
    output_dir: Path
    error: str | None = None


# --- LLM structured-output schemas (used with client.messages.parse) ---


class KeywordList(BaseModel):
    keywords: list[str]


class PatentJudgment(BaseModel):
    relevant: bool
    summary: str = ""


class PatentCategoryAssignment(BaseModel):
    patent_id: str
    categories: list[str]


class CategorizationResponse(BaseModel):
    """Raw structured-output schema for the categorize() LLM call. A list of explicit
    {patent_id, categories} objects, not a generic dict[str, list[str]] — a loosely typed
    dict left the model free to key by category name instead of patent id (i.e. invert
    the intended patent -> categories mapping into categories -> patents), which is
    exactly what happened in testing. Explicit field names remove that ambiguity."""
    categories: list[str]
    assignments: list[PatentCategoryAssignment]


class Categorization(BaseModel):
    """What categorize() returns to callers — assignments normalized into a plain dict."""
    categories: list[str]
    assignments: dict[str, list[str]]  # application_number -> 1-2 category names


# --- API request bodies ---


class StartRunRequest(BaseModel):
    company: str
    subject: str


class ApproveEntitiesRequest(BaseModel):
    approved: list[str]


class ApproveKeywordsRequest(BaseModel):
    approved: list[str]


class ApproveCategorizationRequest(BaseModel):
    categories: list[str]
    assignments: dict[str, list[str]]
