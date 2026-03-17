"""Pydantic models for CrossRef API responses.

Extracted from mygentic's inline client models.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CrossRefAuthor(BaseModel):
    """Author information from CrossRef."""

    given: Optional[str] = None
    family: Optional[str] = None
    sequence: Optional[str] = None
    affiliation: List[Dict[str, str]] = Field(default_factory=list)
    orcid: Optional[str] = None


class CrossRefWork(BaseModel):
    """Publication metadata from CrossRef."""

    doi: Optional[str] = None
    title: Optional[List[str]] = None
    subtitle: Optional[List[str]] = None
    short_title: Optional[List[str]] = None
    author: List[CrossRefAuthor] = Field(default_factory=list)
    container_title: Optional[List[str]] = None
    short_container_title: Optional[List[str]] = None
    published_print: Optional[Dict[str, list]] = None
    published_online: Optional[Dict[str, list]] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    page: Optional[str] = None
    issn: Optional[List[str]] = None
    isbn: Optional[List[str]] = None
    publisher: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    link: Optional[List[Dict[str, str]]] = None
    is_referenced_by_count: Optional[int] = None

    class Config:
        extra = "allow"

    @property
    def title_str(self) -> Optional[str]:
        return self.title[0] if self.title else None

    @property
    def journal_str(self) -> Optional[str]:
        return self.container_title[0] if self.container_title else None

    @property
    def year(self) -> Optional[int]:
        if self.published_print and "date-parts" in self.published_print:
            date_parts = self.published_print["date-parts"][0]
            return date_parts[0] if date_parts else None
        if self.published_online and "date-parts" in self.published_online:
            date_parts = self.published_online["date-parts"][0]
            return date_parts[0] if date_parts else None
        return None

    @property
    def author_names(self) -> List[str]:
        names = []
        for author in self.author:
            if author.family:
                name = author.family
                if author.given:
                    name += f", {author.given}"
                names.append(name)
        return names
