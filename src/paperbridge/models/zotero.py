"""Zotero Web API v3 data models."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ZoteroItemType(str, Enum):
    """Common Zotero item types."""

    journal_article = "journalArticle"
    book = "book"
    book_section = "bookSection"
    conference_paper = "conferencePaper"
    thesis = "thesis"
    report = "report"
    webpage = "webpage"
    preprint = "preprint"
    attachment = "attachment"
    note = "note"


class ZoteroCreator(BaseModel):
    """A single creator (author, editor, etc.) on a Zotero item."""

    creator_type: str = Field("author", alias="creatorType")
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    name: Optional[str] = None  # single-field name for institutional authors

    model_config = {"populate_by_name": True}

    @property
    def display_name(self) -> str:
        """Return a formatted name string, preferring ``name`` for institutional authors."""
        if self.name:
            return self.name
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts)


class ZoteroTag(BaseModel):
    """A tag on a Zotero item."""

    tag: str
    type: int = 0  # 0 = user tag, 1 = automatic


class ZoteroItemData(BaseModel):
    """The data payload of a Zotero item.

    Uses aliases to match Zotero's camelCase JSON field names.
    ``extra="allow"`` accepts item-type-specific fields (e.g. bookTitle)
    without enumerating every possible Zotero schema field.
    """

    key: Optional[str] = None
    version: Optional[int] = None
    item_type: str = Field("journalArticle", alias="itemType")
    title: Optional[str] = None
    creators: list[ZoteroCreator] = Field(default_factory=list)
    abstract_note: Optional[str] = Field(None, alias="abstractNote")
    publication_title: Optional[str] = Field(None, alias="publicationTitle")
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    date: Optional[str] = None
    doi: Optional[str] = Field(None, alias="DOI")
    issn: Optional[str] = Field(None, alias="ISSN")
    url: Optional[str] = None
    tags: list[ZoteroTag] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
    relations: dict[str, Any] = Field(default_factory=dict)
    date_added: Optional[str] = Field(None, alias="dateAdded")
    date_modified: Optional[str] = Field(None, alias="dateModified")
    extra: Optional[str] = None  # Zotero "Extra" field; used for PMID etc.

    model_config = {"populate_by_name": True, "extra": "allow"}


class ZoteroItem(BaseModel):
    """Full Zotero item envelope (key + meta + data)."""

    key: str
    version: int
    library: dict[str, Any] = Field(default_factory=dict)
    data: ZoteroItemData
    meta: dict[str, Any] = Field(default_factory=dict)
    links: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class ZoteroCollection(BaseModel):
    """A Zotero collection (folder)."""

    key: str
    version: int
    name: str
    parent_collection: Optional[str] = Field(None, alias="parentCollection")
    data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True, "extra": "allow"}


class ZoteroSearchResult(BaseModel):
    """Paginated result set from a Zotero library query."""

    items: list[ZoteroItem] = Field(default_factory=list)
    total_results: int = 0
    start: int = 0
    limit: int = 25
    query: Optional[str] = None


class ZoteroSyncResult(BaseModel):
    """Result of syncing paperbridge items to Zotero."""

    created_keys: list[str] = Field(default_factory=list)
    updated_keys: list[str] = Field(default_factory=list)
    failed: list[dict[str, Any]] = Field(default_factory=list)
    total_attempted: int = 0
