"""ArXiv family preprint models (arXiv, bioRxiv, medRxiv, chemRxiv)."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ArXivPreprint(BaseModel):
    """Generic preprint model for arXiv family platforms."""

    doi: str
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: str = ""
    published_date: datetime
    updated_date: Optional[datetime] = None
    pdf_url: Optional[str] = None
    html_url: Optional[str] = None
    platform: Literal["arxiv", "biorxiv", "medrxiv", "chemarxiv"]
    categories: List[str] = Field(default_factory=list)
    version: Optional[str] = None
    arxiv_id: Optional[str] = None
    journal_ref: Optional[str] = None
    comments: Optional[str] = None


class ArXivSearchResult(BaseModel):
    """Search results from arXiv family platforms."""

    query: str
    total_results: int = 0
    returned_results: int = 0
    start_index: int = 0
    preprints: List[ArXivPreprint] = Field(default_factory=list)
    platform: str
    search_date: datetime = Field(default_factory=datetime.now)
