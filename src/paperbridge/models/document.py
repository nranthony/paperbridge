"""Generic document models for parsed documents (PDF, XML, HTML)."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    publication_date: Optional[datetime] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Table(BaseModel):
    caption: Optional[str] = None
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    location: Optional[str] = None
    table_id: Optional[str] = None
    footnotes: Optional[str] = None


class DocumentSection(BaseModel):
    name: str
    content: str
    subsections: List["DocumentSection"] = Field(default_factory=list)
    level: int = 1


DocumentSection.model_rebuild()


class ParsedDocument(BaseModel):
    content: str
    sections: Dict[str, str] = Field(default_factory=dict)
    structured_sections: List[DocumentSection] = Field(default_factory=list)
    tables: List[Table] = Field(default_factory=list)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    format: Literal["pdf", "xml", "html", "text"]
    raw_content: Optional[str] = None
    page_count: Optional[int] = None
    parse_date: datetime = Field(default_factory=datetime.now)
    parser_version: Optional[str] = None


class DocumentReference(BaseModel):
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    reference_text: Optional[str] = None


class SupplementalFile(BaseModel):
    filename: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    file_type: Optional[str] = None
    size_bytes: Optional[int] = None


class ContentAssessment(BaseModel):
    is_complete: bool
    has_abstract: bool = False
    has_methods: bool = False
    has_results: bool = False
    has_discussion: bool = False
    body_length: int = 0
    section_count: int = 0
    missing_sections: List[str] = Field(default_factory=list)
    quality_score: float = Field(0.0, ge=0.0, le=1.0)

    @classmethod
    def from_parsed_document(cls, doc: "ParsedDocument") -> "ContentAssessment":
        sections = doc.sections if isinstance(doc.sections, dict) else {}
        section_names = [name.lower() for name in sections.keys()]

        has_abstract = any("abstract" in name for name in section_names)
        has_methods = any(kw in name for name in section_names for kw in ["method", "material", "experimental"])
        has_results = any("result" in name for name in section_names)
        has_discussion = any(kw in name for name in section_names for kw in ["discussion", "conclusion"])

        body_length = len(doc.content) if doc.content else 0
        if doc.metadata and doc.metadata.abstract:
            body_length -= len(doc.metadata.abstract)

        missing = []
        if not has_abstract:
            missing.append("abstract")
        if not has_methods:
            missing.append("methods")
        if not has_results:
            missing.append("results")
        if not has_discussion:
            missing.append("discussion")

        section_score = (
            (0.25 if has_abstract else 0)
            + (0.25 if has_methods else 0)
            + (0.25 if has_results else 0)
            + (0.25 if has_discussion else 0)
        )
        length_score = min(body_length / 5000, 1.0) if body_length > 0 else 0
        quality_score = (section_score * 0.7) + (length_score * 0.3)
        is_complete = quality_score >= 0.6 and body_length >= 1000

        return cls(
            is_complete=is_complete,
            has_abstract=has_abstract,
            has_methods=has_methods,
            has_results=has_results,
            has_discussion=has_discussion,
            body_length=body_length,
            section_count=len(sections),
            missing_sections=missing,
            quality_score=quality_score,
        )
