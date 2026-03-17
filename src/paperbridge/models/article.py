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
