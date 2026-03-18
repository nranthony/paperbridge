"""Article-level models from wearable_publications."""

from pydantic import BaseModel, Field


class KeywordScore(BaseModel):
    keyword: str
    score: float


class KeywordScoreList(BaseModel):
    keywords: list[KeywordScore] = Field(default_factory=list)


def iter_keywords(result: KeywordScoreList, min_score: float = 0.0):
    """Yield (keyword, score) tuples from a KeywordScoreList."""
    for kw in result.keywords:
        if kw.score >= min_score:
            yield kw.keyword, kw.score


class ArticleKeywords(BaseModel):
    source: str
    mesh_terms: list[str] = Field(default_factory=list)
    author_keywords: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)

    @property
    def all_keywords(self) -> list[str]:
        return sorted(set(self.mesh_terms + self.author_keywords + self.subjects))


class ArticleAbstract(BaseModel):
    source: str
    text: str
    structured: bool = False


class ArticleMetadata(BaseModel):
    source: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    citation_count: int | None = None
    doi: str | None = None
    pmid: str | None = None


class FullText(BaseModel):
    source: str
    text: str
    format: str = "plain"


class ArticleRecord(BaseModel):
    doi: str
    keywords: list[ArticleKeywords] = Field(default_factory=list)
    abstracts: list[ArticleAbstract] = Field(default_factory=list)
    metadata: list[ArticleMetadata] = Field(default_factory=list)
    full_texts: list[FullText] = Field(default_factory=list)

    @property
    def combined_keywords(self) -> list[str]:
        combined: set[str] = set()
        for kw in self.keywords:
            combined.update(kw.all_keywords)
        return sorted(combined)

    @property
    def merged_metadata(self) -> "ArticleMetadata | None":
        """Reduce per-source metadata into one best-field record."""
        if not self.metadata:
            return None
        title = next((m.title for m in self.metadata if m.title is not None), None)
        authors = max((m.authors for m in self.metadata), key=len, default=[])
        year = next((m.year for m in self.metadata if m.year is not None), None)
        journal = next((m.journal for m in self.metadata if m.journal is not None), None)
        doi = next((m.doi for m in self.metadata if m.doi is not None), None)
        pmid = next((m.pmid for m in self.metadata if m.pmid is not None), None)
        citation_count = max(
            (m.citation_count for m in self.metadata if m.citation_count is not None),
            default=None,
        )
        return ArticleMetadata(
            source="merged",
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            doi=doi,
            pmid=pmid,
            citation_count=citation_count,
        )

    def to_bibtex(self) -> "str | None":
        """Format merged_metadata as a BibTeX @article entry."""
        meta = self.merged_metadata
        if meta is None:
            return None
        first_author_last = (
            meta.authors[0].split()[-1] if meta.authors else "Unknown"
        )
        year_str = str(meta.year) if meta.year else "0000"
        cite_key = f"{first_author_last}{year_str}"
        lines = [f"@article{{{cite_key},"]
        if meta.title:
            lines.append(f"  title = {{{meta.title}}},")
        if meta.authors:
            lines.append(f"  author = {{{' and '.join(meta.authors)}}},")
        if meta.journal:
            lines.append(f"  journal = {{{meta.journal}}},")
        if meta.year:
            lines.append(f"  year = {{{meta.year}}},")
        if meta.doi:
            lines.append(f"  doi = {{{meta.doi}}},")
        if meta.pmid:
            lines.append(f"  note = {{PMID: {meta.pmid}}},")
        lines.append("}")
        return "\n".join(lines)
