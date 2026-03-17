"""OpenAlex API data models.

API documentation: https://docs.openalex.org/
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OpenAlexAuthor(BaseModel):
    id: Optional[str] = None
    display_name: str
    orcid: Optional[str] = None

    class Config:
        extra = "allow"


class OpenAlexTopic(BaseModel):
    id: str
    display_name: str
    subfield: Optional[Dict[str, Any]] = None
    field: Optional[Dict[str, Any]] = None
    domain: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class OpenAlexLocation(BaseModel):
    is_oa: bool = False
    landing_page_url: Optional[str] = None
    pdf_url: Optional[str] = None
    source: Optional[Dict[str, Any]] = None
    version: Optional[str] = None

    class Config:
        extra = "allow"


class OpenAlexWork(BaseModel):
    """Scholarly work from OpenAlex."""

    id: str
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    title: Optional[str] = None
    display_name: Optional[str] = None
    publication_year: Optional[int] = None
    publication_date: Optional[str] = None
    authors: List[OpenAlexAuthor] = Field(default_factory=list)
    abstract: Optional[str] = None
    abstract_inverted_index: Optional[Dict[str, List[int]]] = None
    is_oa: bool = False
    open_access: Optional[Dict[str, Any]] = None
    primary_location: Optional[OpenAlexLocation] = None
    locations: List[OpenAlexLocation] = Field(default_factory=list)
    best_oa_location: Optional[OpenAlexLocation] = None
    cited_by_count: int = 0
    counts_by_year: List[Dict[str, int]] = Field(default_factory=list)
    topics: List[OpenAlexTopic] = Field(default_factory=list)
    primary_topic: Optional[OpenAlexTopic] = None
    keywords: List[Dict[str, Any]] = Field(default_factory=list)
    type: Optional[str] = None
    type_crossref: Optional[str] = None
    biblio: Optional[Dict[str, Any]] = None
    referenced_works: List[str] = Field(default_factory=list)
    related_works: List[str] = Field(default_factory=list)
    created_date: Optional[str] = None
    updated_date: Optional[str] = None

    class Config:
        extra = "allow"

    @property
    def pdf_url(self) -> Optional[str]:
        if self.best_oa_location and self.best_oa_location.pdf_url:
            return self.best_oa_location.pdf_url
        if self.primary_location and self.primary_location.pdf_url:
            return self.primary_location.pdf_url
        for location in self.locations:
            if location.pdf_url:
                return location.pdf_url
        return None

    @property
    def landing_page_url(self) -> Optional[str]:
        if self.primary_location and self.primary_location.landing_page_url:
            return self.primary_location.landing_page_url
        if self.doi:
            return f"https://doi.org/{self.doi}"
        return None

    @property
    def author_names(self) -> List[str]:
        return [author.display_name for author in self.authors]

    def get_abstract_text(self) -> Optional[str]:
        if self.abstract:
            return self.abstract
        if not self.abstract_inverted_index:
            return None
        word_positions = []
        for word, positions in self.abstract_inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort(key=lambda x: x[0])
        return " ".join(word for _, word in word_positions)


class OpenAlexSearchResponse(BaseModel):
    results: List[OpenAlexWork]
    meta: Dict[str, Any]

    @property
    def count(self) -> int:
        return self.meta.get("count", 0)

    @property
    def per_page(self) -> int:
        return self.meta.get("per_page", 25)

    @property
    def page(self) -> int:
        return self.meta.get("page", 1)


class OpenAlexFilter(BaseModel):
    """Filter options for OpenAlex searches."""

    publication_year: Optional[str] = None
    from_publication_date: Optional[str] = None
    to_publication_date: Optional[str] = None
    is_oa: Optional[bool] = None
    type: Optional[str] = None
    cited_by_count: Optional[str] = None
    topics_id: Optional[str] = None
    institutions_id: Optional[str] = None
    authors_id: Optional[str] = None

    class Config:
        extra = "allow"

    def to_query_string(self) -> str:
        filters = []
        if self.publication_year:
            filters.append(f"publication_year:{self.publication_year}")
        if self.from_publication_date:
            filters.append(f"from_publication_date:{self.from_publication_date}")
        if self.to_publication_date:
            filters.append(f"to_publication_date:{self.to_publication_date}")
        if self.is_oa is not None:
            filters.append(f"is_oa:{str(self.is_oa).lower()}")
        if self.type:
            filters.append(f"type:{self.type}")
        if self.cited_by_count:
            filters.append(f"cited_by_count:{self.cited_by_count}")
        if self.topics_id:
            filters.append(f"topics.id:{self.topics_id}")
        if self.institutions_id:
            filters.append(f"institutions.id:{self.institutions_id}")
        if self.authors_id:
            filters.append(f"authors.id:{self.authors_id}")
        return ",".join(filters)
