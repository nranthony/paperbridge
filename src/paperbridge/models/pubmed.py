"""Pydantic models for PubMed E-utilities API.

API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from enum import Enum


class DateType(str, Enum):
    """PubMed date field types for filtering."""

    MODIFICATION = "mdat"
    PUBLICATION = "pdat"
    ENTREZ = "edat"


class SortOrder(str, Enum):
    """Sort order options for PubMed searches."""

    RELEVANCE = "relevance"
    PUB_DATE = "pub_date"
    AUTHOR = "author"
    JOURNAL = "journal"


class PubMedSearchCriteria(BaseModel):
    """Search criteria for PubMed publications."""

    term: str = Field(
        ...,
        description="Search query using PubMed syntax. Supports field tags and Boolean operators.",
    )
    datetype: Optional[DateType] = None
    mindate: Optional[str] = Field(None, description="Minimum date in YYYY/MM/DD format")
    maxdate: Optional[str] = Field(None, description="Maximum date in YYYY/MM/DD format")
    reldate: Optional[int] = Field(None, description="Return results from the last N days")
    sort: Optional[SortOrder] = Field(SortOrder.RELEVANCE)
    retstart: int = Field(0, ge=0)
    retmax: int = Field(100, ge=1, le=10000)

    class Config:
        use_enum_values = True


class SimplifiedCitation(BaseModel):
    """Simplified citation model for parsing raw/unstructured citation text."""

    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[str] = None
    date: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    pmid: Optional[str] = None
    pmc_id: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    raw_citation: Optional[str] = None

    class Config:
        extra = "forbid"


class ArticleId(BaseModel):
    """Article identifier in various databases."""

    idtype: str = Field(..., description="Type of identifier (pubmed, pmc, doi, pii, etc.)")
    value: str


class Author(BaseModel):
    """Publication author information."""

    name: str
    authtype: str
    clusterid: Optional[str] = None


class HistoryDate(BaseModel):
    """Publication history date entry."""

    pubstatus: str
    date: str


class PubMedPublication(BaseModel):
    """PubMed publication summary data from ESummary."""

    uid: str
    pmid: str
    title: str
    source: str
    fulljournalname: str
    authors: List[Author] = Field(default_factory=list)
    sortfirstauthor: Optional[str] = None
    volume: str = ""
    issue: str = ""
    pages: str = ""
    pubdate: str
    epubdate: Optional[str] = None
    sortpubdate: str
    pubtype: List[str] = Field(default_factory=list)
    lang: List[str] = Field(default_factory=list)
    recordstatus: str
    articleids: List[ArticleId] = Field(default_factory=list)
    history: List[HistoryDate] = Field(default_factory=list)
    attributes: List[str] = Field(default_factory=list)
    elocationid: Optional[str] = None
    doctype: Optional[str] = None

    class Config:
        extra = "allow"


class PubMedSearchResponse(BaseModel):
    """Response from PubMed ESearch endpoint."""

    count: int
    retmax: int
    retstart: int
    idlist: List[str] = Field(default_factory=list)
    translationstack: Optional[List[Any]] = None
    querytranslation: Optional[str] = None

    class Config:
        extra = "allow"


class PubMedSummaryResponse(BaseModel):
    """Response from PubMed ESummary endpoint."""

    result: Dict[str, Any]

    def get_publications(self) -> List[PubMedPublication]:
        publications = []
        uids = self.result.get("uids", [])
        for uid in uids:
            pub_data = self.result.get(str(uid))
            if pub_data:
                pub_data["pmid"] = pub_data.get("uid", str(uid))
                try:
                    publications.append(PubMedPublication(**pub_data))
                except Exception:
                    pass
        return publications

    class Config:
        extra = "allow"
