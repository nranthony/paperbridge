"""BASE (Bielefeld Academic Search Engine) data models."""

from typing import List, Optional

from pydantic import BaseModel, Field


class BASEWork(BaseModel):
    """Document from BASE search results."""

    title: Optional[str] = None
    link: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    year: Optional[str] = None
    date: Optional[str] = None
    source: Optional[str] = None
    type: Optional[str] = None
    doi: Optional[str] = None
    identifier: Optional[str] = None
    language: Optional[str] = None
    collection: Optional[str] = None

    class Config:
        extra = "allow"

    @property
    def author_names(self) -> List[str]:
        return self.authors

    def to_simplified_citation(self):
        from paperbridge.models.pubmed import SimplifiedCitation

        return SimplifiedCitation(
            title=self.title,
            authors=self.authors,
            year=self.year,
            date=self.date,
            doi=self.doi,
            url=self.link,
            raw_citation=(
                f"{', '.join(self.authors[:3]) if self.authors else 'Unknown'} "
                f"({self.year}). {self.title}. {self.source}."
            ),
        )


class BASESearchResponse(BaseModel):
    results: List[BASEWork]
    total_hits: int = 0
    query: str
    page: int = 1

    class Config:
        extra = "allow"
