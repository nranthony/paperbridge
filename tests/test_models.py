"""Unit tests for paperbridge Pydantic models (no network required)."""

import pytest

from paperbridge.models.article import (
    ArticleAbstract,
    ArticleKeywords,
    ArticleMetadata,
    ArticleRecord,
    FullText,
    KeywordScore,
    KeywordScoreList,
    iter_keywords,
)


class TestArticleKeywords:
    def test_all_keywords_deduplicates(self):
        kw = ArticleKeywords(
            source="test",
            mesh_terms=["Gene Editing", "CRISPR"],
            author_keywords=["CRISPR", "base editing"],
            subjects=["Biochemistry"],
        )
        result = kw.all_keywords
        assert result == sorted(set(result))
        assert "CRISPR" in result
        assert result.count("CRISPR") == 1

    def test_all_keywords_sorted(self):
        kw = ArticleKeywords(source="test", mesh_terms=["Zebra", "Apple", "Mango"])
        assert kw.all_keywords == ["Apple", "Mango", "Zebra"]

    def test_empty_keywords(self):
        kw = ArticleKeywords(source="test")
        assert kw.all_keywords == []

    def test_source_stored(self):
        kw = ArticleKeywords(source="pubmed", mesh_terms=["Asthma"])
        assert kw.source == "pubmed"


class TestArticleAbstract:
    def test_defaults(self):
        ab = ArticleAbstract(source="crossref", text="Some abstract.")
        assert ab.structured is False

    def test_structured_flag(self):
        ab = ArticleAbstract(source="pubmed", text="Background: ...", structured=True)
        assert ab.structured is True


class TestArticleMetadata:
    def test_optional_fields_default_none(self):
        meta = ArticleMetadata(source="test")
        assert meta.title is None
        assert meta.year is None
        assert meta.authors == []
        assert meta.doi is None
        assert meta.pmid is None

    def test_full_metadata(self, sample_metadata):
        assert sample_metadata.title == "Programmable base editing"
        assert sample_metadata.year == 2021
        assert "David Liu" in sample_metadata.authors
        assert sample_metadata.citation_count == 1200


class TestArticleRecord:
    def test_empty_record(self):
        record = ArticleRecord(doi="10.1234/test")
        assert record.keywords == []
        assert record.abstracts == []
        assert record.metadata == []
        assert record.full_texts == []
        assert record.combined_keywords == []

    def test_combined_keywords_aggregates_sources(self, sample_keywords):
        kw2 = ArticleKeywords(source="crossref", subjects=["Genetics", "CRISPR-Cas Systems"])
        record = ArticleRecord(doi="10.1234/test", keywords=[sample_keywords, kw2])
        combined = record.combined_keywords
        assert "CRISPR-Cas Systems" in combined
        assert combined.count("CRISPR-Cas Systems") == 1
        assert "base editing" in combined
        assert "Genetics" in combined

    def test_combined_keywords_sorted(self, sample_keywords):
        record = ArticleRecord(doi="10.1234/test", keywords=[sample_keywords])
        assert record.combined_keywords == sorted(record.combined_keywords)

    def test_append_records(self, sample_keywords, sample_abstract, sample_metadata):
        record = ArticleRecord(doi="10.1234/test")
        record.keywords.append(sample_keywords)
        record.abstracts.append(sample_abstract)
        record.metadata.append(sample_metadata)
        assert len(record.keywords) == 1
        assert len(record.abstracts) == 1
        assert len(record.metadata) == 1


class TestKeywordScoreList:
    def test_iter_keywords_min_score(self):
        ksl = KeywordScoreList(
            keywords=[
                KeywordScore(keyword="CRISPR", score=0.9),
                KeywordScore(keyword="Zebra", score=0.2),
                KeywordScore(keyword="Gene editing", score=0.7),
            ]
        )
        results = list(iter_keywords(ksl, min_score=0.5))
        keywords = [k for k, _ in results]
        assert "CRISPR" in keywords
        assert "Gene editing" in keywords
        assert "Zebra" not in keywords

    def test_iter_keywords_zero_threshold(self):
        ksl = KeywordScoreList(
            keywords=[KeywordScore(keyword="A", score=0.0), KeywordScore(keyword="B", score=1.0)]
        )
        results = list(iter_keywords(ksl, min_score=0.0))
        assert len(results) == 2
