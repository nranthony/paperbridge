"""Citation workflow data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from paperbridge.models.pubmed import SimplifiedCitation


class SearchTier(str, Enum):
    TIER_1_PEER_REVIEWED = "peer_reviewed"
    TIER_2_PREPRINTS = "preprints"
    TIER_3_GREY_LITERATURE = "grey_literature"


class SupportType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"
    PARTIAL_SUPPORT = "partial_support"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    MISATTRIBUTED = "misattributed"
    CITATION_NOT_FOUND = "not_found"


class CitationVerificationResult(BaseModel):
    citation: SimplifiedCitation
    verification_status: VerificationStatus
    relevance_score: int = Field(..., ge=0, le=100)
    support_type: SupportType
    full_text_excerpt: Optional[str] = Field(None, max_length=500)
    section_found: Optional[str] = None
    full_text_available: bool
    download_source: Optional[str] = None
    verification_notes: Optional[str] = None
    addressed_bullet_point: Optional[int] = None
    verification_timestamp: Optional[str] = None

    class Config:
        extra = "forbid"

    def summary(self) -> str:
        return (
            f"[{self.verification_status.value}] "
            f"[{self.support_type.value}] "
            f"Score: {self.relevance_score}/100 | "
            f"{self.citation.title or self.citation.doi or 'Unknown'}"
        )


class SearchResult(BaseModel):
    tier: SearchTier
    source: str
    query: str
    articles: List[SimplifiedCitation]
    total_found: int
    search_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    filters_applied: Optional[Dict[str, Any]] = None
    page: int = 1
    per_page: int = 25

    class Config:
        extra = "allow"


class WorkflowInput(BaseModel):
    statement: str = Field(..., min_length=10)
    bullet_points: List[str] = Field(default_factory=list)
    max_results_per_tier: int = Field(default=50, ge=1, le=200)
    min_results_tier1: int = Field(default=10, ge=1)
    min_results_tier2: int = Field(default=5, ge=1)
    require_full_text: bool = True
    require_full_text_verification: bool = True
    find_contrary: bool = True
    contrary_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    min_relevance_score: int = Field(default=50, ge=0, le=100)
    min_publication_year: Optional[int] = None
    citation_style: str = "numbered"
    include_abstracts: bool = False

    class Config:
        extra = "forbid"


class WorkflowOutput(BaseModel):
    input: WorkflowInput
    search_results: List[SearchResult]
    verified_citations: List[CitationVerificationResult]
    total_articles_searched: int = 0
    total_articles_found: int = 0
    total_full_text_downloaded: int = 0
    total_verified: int = 0
    supporting_count: int = 0
    contradicting_count: int = 0
    neutral_count: int = 0
    partial_support_count: int = 0
    summary_markdown: str
    bibliography_markdown: str
    workflow_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_execution_time_seconds: float = 0.0
    highest_tier_reached: SearchTier = SearchTier.TIER_1_PEER_REVIEWED
    llm_calls_made: int = 0
    llm_tokens_used: Optional[int] = None

    class Config:
        extra = "allow"


class ContraryQuery(BaseModel):
    original_statement: str
    negation_query: str
    query_type: str
    rationale: Optional[str] = None

    class Config:
        extra = "forbid"


class VerificationAssessment(BaseModel):
    support_type: SupportType
    relevance_score: int = Field(..., ge=0, le=100)
    relevant_quote: str = Field(..., max_length=500)
    addressed_bullet_point: Optional[int] = None
    reasoning: str

    class Config:
        extra = "forbid"
