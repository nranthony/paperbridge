"""Tests for CitationAggregator using mock clients."""

import pytest
from unittest.mock import MagicMock

from paperbridge.aggregator import CitationAggregator
from paperbridge.clients._base import BaseAPIClient
from paperbridge.models.article import (
    ArticleAbstract,
    ArticleKeywords,
    ArticleMetadata,
    ArticleRecord,
)


def _make_client(source: str, keywords=None, abstract=None, metadata=None, full_text=None):
    client = MagicMock(spec=BaseAPIClient)
    client.source_name = source
    client.fetch_keywords.return_value = keywords
    client.fetch_abstract.return_value = abstract
    client.fetch_metadata.return_value = metadata
    client.fetch_full_text.return_value = full_text
    return client


DOI = "10.1234/test"


class TestCitationAggregator:
    def test_fetch_all_keywords_combines_sources(self):
        kw1 = ArticleKeywords(source="a", mesh_terms=["Gene Editing"], subjects=["Biology"])
        kw2 = ArticleKeywords(source="b", author_keywords=["CRISPR", "Gene Editing"])
        agg = CitationAggregator(clients=[_make_client("a", keywords=kw1), _make_client("b", keywords=kw2)])

        result = agg.fetch_all_keywords(DOI)

        assert "Gene Editing" in result["a"]
        assert "CRISPR" in result["b"]
        combined = result["combined"]
        assert combined.count("Gene Editing") == 1
        assert "CRISPR" in combined
        assert "Biology" in combined

    def test_fetch_all_keywords_handles_none(self):
        agg = CitationAggregator(clients=[_make_client("a", keywords=None)])
        result = agg.fetch_all_keywords(DOI)
        assert result["a"] == []
        assert result["combined"] == []

    def test_fetch_all_keywords_handles_client_exception(self):
        client = _make_client("a")
        client.fetch_keywords.side_effect = RuntimeError("network error")
        agg = CitationAggregator(clients=[client])
        result = agg.fetch_all_keywords(DOI)
        assert result["a"] == []
        assert result["combined"] == []

    def test_fetch_article_populates_record(self):
        kw = ArticleKeywords(source="a", mesh_terms=["Asthma"])
        ab = ArticleAbstract(source="a", text="Background...")
        meta = ArticleMetadata(source="a", title="Test Paper", year=2023)
        agg = CitationAggregator(clients=[_make_client("a", keywords=kw, abstract=ab, metadata=meta)])

        record = agg.fetch_article(DOI)

        assert isinstance(record, ArticleRecord)
        assert record.doi == DOI
        assert len(record.keywords) == 1
        assert len(record.abstracts) == 1
        assert len(record.metadata) == 1
        assert record.metadata[0].title == "Test Paper"

    def test_fetch_article_skips_none_results(self):
        agg = CitationAggregator(clients=[_make_client("a")])
        record = agg.fetch_article(DOI)
        assert record.keywords == []
        assert record.abstracts == []
        assert record.metadata == []
        assert record.full_texts == []

    def test_fetch_article_tolerates_client_errors(self):
        client = _make_client("a")
        client.fetch_keywords.side_effect = RuntimeError("boom")
        client.fetch_abstract.side_effect = RuntimeError("boom")
        client.fetch_metadata.side_effect = RuntimeError("boom")
        client.fetch_full_text.side_effect = RuntimeError("boom")
        agg = CitationAggregator(clients=[client])
        record = agg.fetch_article(DOI)
        assert record.doi == DOI

    def test_fetch_article_multiple_clients(self):
        kw1 = ArticleKeywords(source="a", subjects=["Biology"])
        kw2 = ArticleKeywords(source="b", subjects=["Genetics"])
        agg = CitationAggregator(
            clients=[_make_client("a", keywords=kw1), _make_client("b", keywords=kw2)]
        )
        record = agg.fetch_article(DOI)
        assert len(record.keywords) == 2
        assert "Biology" in record.combined_keywords
        assert "Genetics" in record.combined_keywords

    def test_close_only_owns_clients_it_created(self):
        client = _make_client("a")
        agg = CitationAggregator(clients=[client])
        agg.close()
        client.close.assert_not_called()

    def test_context_manager(self):
        client = _make_client("a")
        with CitationAggregator(clients=[client]) as agg:
            assert isinstance(agg, CitationAggregator)

    def test_repr(self):
        agg = CitationAggregator(clients=[_make_client("pubmed"), _make_client("crossref")])
        assert "pubmed" in repr(agg)
        assert "crossref" in repr(agg)
