"""Unit tests for paperbridge Pydantic models (no network required)."""

import pytest

from tests.conftest import SAMPLE_DOI
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


class TestArticleRecordMergedMetadata:
    def test_returns_none_for_empty_record(self):
        record = ArticleRecord(doi="10.1/test")
        assert record.merged_metadata is None

    def test_title_first_non_none(self):
        m1 = ArticleMetadata(source="a", title=None)
        m2 = ArticleMetadata(source="b", title="Best Title")
        record = ArticleRecord(doi="10.1/test", metadata=[m1, m2])
        assert record.merged_metadata.title == "Best Title"

    def test_authors_longest_list(self):
        m1 = ArticleMetadata(source="a", authors=["Alice"])
        m2 = ArticleMetadata(source="b", authors=["Alice", "Bob", "Carol"])
        record = ArticleRecord(doi="10.1/test", metadata=[m1, m2])
        assert record.merged_metadata.authors == ["Alice", "Bob", "Carol"]

    def test_citation_count_max(self):
        m1 = ArticleMetadata(source="a", citation_count=100)
        m2 = ArticleMetadata(source="b", citation_count=500)
        m3 = ArticleMetadata(source="c")
        record = ArticleRecord(doi="10.1/test", metadata=[m1, m2, m3])
        assert record.merged_metadata.citation_count == 500

    def test_pmid_first_non_none(self):
        m1 = ArticleMetadata(source="a", pmid=None)
        m2 = ArticleMetadata(source="b", pmid="12345678")
        record = ArticleRecord(doi="10.1/test", metadata=[m1, m2])
        assert record.merged_metadata.pmid == "12345678"

    def test_source_is_merged(self):
        m = ArticleMetadata(source="crossref", title="T")
        record = ArticleRecord(doi="10.1/test", metadata=[m])
        assert record.merged_metadata.source == "merged"


class TestArticleRecordToBibtex:
    def test_returns_none_for_empty_metadata(self):
        record = ArticleRecord(doi="10.1/test")
        assert record.to_bibtex() is None

    def test_basic_bibtex_output(self, sample_metadata):
        record = ArticleRecord(doi=sample_metadata.doi, metadata=[sample_metadata])
        bib = record.to_bibtex()
        assert bib is not None
        assert "@article{" in bib
        assert "Programmable base editing" in bib
        assert "Nature" in bib
        assert "2021" in bib
        assert SAMPLE_DOI in bib

    def test_cite_key_format(self):
        m = ArticleMetadata(source="a", authors=["Jane Doe"], year=2020, title="T")
        record = ArticleRecord(doi="10.1/t", metadata=[m])
        bib = record.to_bibtex()
        assert "@article{Doe2020," in bib

    def test_unknown_author_fallback(self):
        m = ArticleMetadata(source="a", title="T", year=2020)
        record = ArticleRecord(doi="10.1/t", metadata=[m])
        bib = record.to_bibtex()
        assert "@article{Unknown2020," in bib

    def test_pmid_in_note(self):
        m = ArticleMetadata(source="a", authors=["A B"], year=2020, pmid="99999")
        record = ArticleRecord(doi="10.1/t", metadata=[m])
        bib = record.to_bibtex()
        assert "PMID: 99999" in bib


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
