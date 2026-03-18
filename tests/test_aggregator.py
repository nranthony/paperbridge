"""Tests for CitationAggregator using mock clients."""

import pytest
from unittest.mock import MagicMock, patch

from paperbridge.aggregator import CitationAggregator
from paperbridge.clients._base import BaseAPIClient
from paperbridge.clients.openalex import OpenAlexClient
from paperbridge.models.article import (
    ArticleAbstract,
    ArticleKeywords,
    ArticleMetadata,
    ArticleRecord,
)
from paperbridge.models.citation_graph import CitationGraph
from paperbridge.models.openalex import OpenAlexWork


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


def _make_openalex_work(work_id: str = "W123", doi: str = "10.1234/test", cited_by_count: int = 5) -> OpenAlexWork:
    return OpenAlexWork(id=work_id, doi=doi, cited_by_count=cited_by_count, referenced_works=["W1", "W2"])


class TestFetchCitationGraph:
    def _make_openalex_client(self, source_work=None, citations=None, references=None):
        client = MagicMock(spec=OpenAlexClient)
        client.source_name = "openalex"
        client.get_work_by_doi.return_value = source_work
        client.get_citations.return_value = citations or []
        client.get_references.return_value = references or []
        return client

    def test_returns_citation_graph(self):
        source = _make_openalex_work()
        citing = _make_openalex_work("W200", "10.1234/citing", 2)
        ref = _make_openalex_work("W300", "10.1234/ref", 10)
        oa = self._make_openalex_client(source_work=source, citations=[citing], references=[ref])

        agg = CitationAggregator(clients=[oa])
        graph = agg.fetch_citation_graph(DOI)

        assert isinstance(graph, CitationGraph)
        assert graph.source_doi == DOI
        assert graph.source_work.id == "W123"
        assert len(graph.cited_by) == 1
        assert graph.cited_by[0].id == "W200"
        assert len(graph.references) == 1
        assert graph.references[0].id == "W300"
        assert graph.cited_by_count == 5
        assert graph.reference_count == 2

    def test_returns_none_when_doi_not_found(self):
        oa = self._make_openalex_client(source_work=None)
        agg = CitationAggregator(clients=[oa])
        assert agg.fetch_citation_graph(DOI) is None

    def test_returns_none_when_no_openalex_client(self):
        agg = CitationAggregator(clients=[_make_client("crossref")])
        assert agg.fetch_citation_graph(DOI) is None

    def test_returns_none_when_get_work_raises(self):
        oa = self._make_openalex_client()
        oa.get_work_by_doi.side_effect = RuntimeError("network error")
        agg = CitationAggregator(clients=[oa])
        assert agg.fetch_citation_graph(DOI) is None

    def test_cited_by_limit_passed_to_client(self):
        source = _make_openalex_work()
        oa = self._make_openalex_client(source_work=source)
        agg = CitationAggregator(clients=[oa])
        agg.fetch_citation_graph(DOI, cited_by_limit=10, references_limit=20)
        oa.get_citations.assert_called_once_with(source.id, per_page=10)
        oa.get_references.assert_called_once_with(source.id, per_page=20)

    def test_partial_results_when_citations_fail(self):
        source = _make_openalex_work()
        oa = self._make_openalex_client(source_work=source)
        oa.get_citations.side_effect = RuntimeError("citations unavailable")
        agg = CitationAggregator(clients=[oa])
        graph = agg.fetch_citation_graph(DOI)
        assert graph is not None
        assert graph.cited_by == []
        assert graph.references == []
