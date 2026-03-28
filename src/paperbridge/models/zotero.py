"""Zotero Web API v3 data models."""

import re
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


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

    creator_type: str = Field("author", validation_alias="creatorType", serialization_alias="creatorType")
    first_name: Optional[str] = Field(None, validation_alias="firstName", serialization_alias="firstName")
    last_name: Optional[str] = Field(None, validation_alias="lastName", serialization_alias="lastName")
    name: Optional[str] = None  # single-field name for institutional authors

    model_config = ConfigDict(populate_by_name=True)

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
    item_type: str = Field("journalArticle", validation_alias="itemType", serialization_alias="itemType")
    title: Optional[str] = None
    creators: list[ZoteroCreator] = Field(default_factory=list)
    abstract_note: Optional[str] = Field(None, validation_alias="abstractNote", serialization_alias="abstractNote")
    publication_title: Optional[str] = Field(None, validation_alias="publicationTitle", serialization_alias="publicationTitle")
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    date: Optional[str] = None
    doi: Optional[str] = Field(None, validation_alias="DOI", serialization_alias="DOI")
    issn: Optional[str] = Field(None, validation_alias="ISSN", serialization_alias="ISSN")
    url: Optional[str] = None
    tags: list[ZoteroTag] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
    relations: dict[str, Any] = Field(default_factory=dict)
    date_added: Optional[str] = Field(None, validation_alias="dateAdded", serialization_alias="dateAdded")
    date_modified: Optional[str] = Field(None, validation_alias="dateModified", serialization_alias="dateModified")
    extra: Optional[str] = None  # Zotero "Extra" field; used for PMID etc.

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ZoteroItem(BaseModel):
    """Full Zotero item envelope (key + meta + data)."""

    key: str
    version: int
    library: dict[str, Any] = Field(default_factory=dict)
    data: ZoteroItemData
    meta: dict[str, Any] = Field(default_factory=dict)
    links: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    # BibTeX entry-type mapping from Zotero item types
    _BIBTEX_TYPE_MAP: dict[str, str] = {
        "journalArticle": "article",
        "book": "book",
        "bookSection": "incollection",
        "conferencePaper": "inproceedings",
        "thesis": "phdthesis",
        "report": "techreport",
        "webpage": "misc",
        "preprint": "misc",
    }

    # Zotero model_extra keys that map directly to BibTeX field names
    _EXTRA_BIBTEX_FIELDS: list[tuple[str, str]] = [
        ("publisher", "publisher"),
        ("place", "address"),
        ("edition", "edition"),
        ("ISBN", "isbn"),
        ("language", "language"),
        ("journalAbbreviation", "journal-abbrev"),
        ("seriesTitle", "series"),
        ("callNumber", "call-number"),
    ]

    def to_bibtex(self) -> str:
        """Format this item as a BibTeX entry using all available metadata fields.

        Uses the full ``ZoteroItemData`` payload (abstract, volume, issue,
        pages, ISSN, URL, tags, etc.) rather than the minimal subset exposed
        by :meth:`ZoteroClient.item_to_article_metadata`.
        """
        data = self.data
        extra_fields: dict[str, Any] = data.model_extra or {}

        # --- Cite key ---
        first_creator = next(
            (c for c in data.creators if c.creator_type == "author"), None
        ) or (data.creators[0] if data.creators else None)

        if first_creator:
            last = first_creator.last_name or first_creator.name or "unknown"
        else:
            last = "unknown"
        last_slug = re.sub(r"[^a-z0-9]", "", last.lower())

        year_str: Optional[str] = None
        month_str: Optional[str] = None
        if data.date:
            y_match = re.search(r"\b(19|20)\d{2}\b", data.date)
            if y_match:
                year_str = y_match.group()
            m_match = re.search(
                r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
                data.date,
                re.I,
            )
            if m_match:
                month_str = m_match.group()[:3].lower()
            elif re.search(r"\b(\d{4})-(\d{2})", data.date):
                month_num = int(re.search(r"\b\d{4}-(\d{2})", data.date).group(1))  # type: ignore[union-attr]
                _months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
                if 1 <= month_num <= 12:
                    month_str = _months[month_num - 1]

        title_slug = ""
        if data.title:
            first_word = re.split(r"\s+", data.title.strip())[0]
            title_slug = "_" + re.sub(r"[^a-z0-9]", "", first_word.lower())

        cite_key = f"{last_slug}{title_slug}_{year_str or '0000'}"

        # --- Entry type ---
        entry_type = self._BIBTEX_TYPE_MAP.get(data.item_type, "misc")

        # --- Author string ---
        authors = []
        for c in data.creators:
            if c.creator_type != "author":
                continue
            if c.last_name and c.first_name:
                authors.append(f"{c.last_name}, {c.first_name}")
            elif c.last_name:
                authors.append(c.last_name)
            elif c.name:
                authors.append(c.name)

        # --- Keywords from user tags ---
        keywords = [t.tag for t in data.tags if t.type == 0]

        # --- Build field list ---
        fields: list[tuple[str, str]] = []

        def _add(name: str, value: Optional[str]) -> None:
            if value:
                fields.append((name, value))

        _add("title", data.title)
        _add("volume", data.volume)
        _add("issn", data.issn)
        _add("url", data.url)
        _add("doi", data.doi)
        _add("abstract", data.abstract_note)
        _add("number", data.issue)
        _add("journal", data.publication_title)

        # Fields from model_extra (item-type-specific Zotero fields)
        for zotero_key, bibtex_key in self._EXTRA_BIBTEX_FIELDS:
            _add(bibtex_key, extra_fields.get(zotero_key))

        if authors:
            fields.append(("author", " and ".join(authors)))
        if month_str:
            fields.append(("month", month_str))
        _add("year", year_str)
        if keywords:
            fields.append(("keywords", ", ".join(keywords)))
        _add("pages", data.pages)
        _add("note", data.extra)

        # --- Render ---
        lines = [f"@{entry_type}{{{cite_key},"]
        for name, value in fields:
            lines.append(f"\t{name} = {{{value}}},")
        lines.append("}")
        return "\n".join(lines)


class ZoteroCollection(BaseModel):
    """A Zotero collection (folder)."""

    key: str
    version: int
    name: str
    parent_collection: Optional[str] = Field(None, validation_alias="parentCollection", serialization_alias="parentCollection")
    data: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


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
