"""Tests for PubMedClient using mocked HTTP responses."""

import pytest
from unittest.mock import MagicMock, patch

from paperbridge.clients.pubmed import PubMedClient

DOI = "10.1038/s41586-021-03819-2"
PMID = "34522049"

ESEARCH_RESPONSE = {
    "esearchresult": {
        "count": "1",
        "retmax": "1",
        "retstart": "0",
        "idlist": [PMID],
        "querytranslation": f"{DOI}[doi]",
    }
}

PUBMED_XML = f"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>{PMID}</PMID>
      <Article>
        <ArticleTitle>Programmable base editing</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">CRISPR base editing enables precise changes.</AbstractText>
          <AbstractText Label="RESULTS">High efficiency observed.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Liu</LastName>
            <ForeName>David</ForeName>
          </Author>
        </AuthorList>
      </Article>
      <MeshHeadingList>
        <MeshHeading>
          <DescriptorName>CRISPR-Cas Systems</DescriptorName>
        </MeshHeading>
        <MeshHeading>
          <DescriptorName>Gene Editing</DescriptorName>
        </MeshHeading>
      </MeshHeadingList>
      <KeywordList>
        <Keyword>base editing</Keyword>
        <Keyword>prime editing</Keyword>
      </KeywordList>
    </MedlineCitation>
    <PubmedData>
      <History>
        <PubMedPubDate PubStatus="pubmed">
          <Year>2021</Year>
        </PubMedPubDate>
      </History>
      <PublicationStatus>epublish</PublicationStatus>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def _make_json_response(data: dict, status: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = data
    return mock_resp


def _make_text_response(text: str, status: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.text = text
    mock_resp.raise_for_status.return_value = None
    return mock_resp


class TestPubMedClientRateLimitConfig:
    def test_rate_limit_no_key(self):
        client = PubMedClient()
        assert client.rate_limit == pytest.approx(0.34)

    def test_rate_limit_with_key(self):
        client = PubMedClient(api_key="abc123")
        assert client.rate_limit == pytest.approx(0.11)

    def test_explicit_rate_limit(self):
        client = PubMedClient(rate_limit=0.5)
        assert client.rate_limit == pytest.approx(0.5)

    def test_source_name(self):
        assert PubMedClient.source_name == "pubmed"


class TestPubMedClientDOIMethods:
    def _patched_client(self):
        client = PubMedClient()
        client._session = MagicMock()
        client._session.headers = MagicMock()
        return client

    def _setup_xml_fetch(self, client):
        esearch_resp = _make_json_response(ESEARCH_RESPONSE)
        efetch_resp = _make_text_response(PUBMED_XML)
        client._session.get.side_effect = [esearch_resp, efetch_resp]

    def test_fetch_keywords_extracts_mesh_and_author(self):
        client = self._patched_client()
        self._setup_xml_fetch(client)

        kw = client.fetch_keywords(DOI)

        assert kw is not None
        assert kw.source == "pubmed"
        assert "CRISPR-Cas Systems" in kw.mesh_terms
        assert "Gene Editing" in kw.mesh_terms
        assert "base editing" in kw.author_keywords
        assert "prime editing" in kw.author_keywords

    def test_fetch_abstract_extracts_text(self):
        client = self._patched_client()
        self._setup_xml_fetch(client)

        ab = client.fetch_abstract(DOI)

        assert ab is not None
        assert ab.source == "pubmed"
        assert "base editing" in ab.text
        assert ab.structured is True  # has Label= attribute

    def test_fetch_metadata_extracts_fields(self):
        client = self._patched_client()
        self._setup_xml_fetch(client)

        meta = client.fetch_metadata(DOI)

        assert meta is not None
        assert meta.source == "pubmed"
        assert meta.title == "Programmable base editing"
        assert "David Liu" in meta.authors
        assert meta.doi == DOI

    def test_fetch_keywords_returns_none_when_pmid_not_found(self):
        client = self._patched_client()
        no_result = {"esearchresult": {"count": "0", "retmax": "0", "retstart": "0", "idlist": []}}
        client._session.get.return_value = _make_json_response(no_result)

        assert client.fetch_keywords(DOI) is None

    def test_xml_cached_after_first_fetch(self):
        client = self._patched_client()
        self._setup_xml_fetch(client)
        # Pre-populate cache as fetch_keywords would
        client.fetch_keywords(DOI)
        call_count_after_first = client._session.get.call_count

        # Second DOI-based call should use cache (no additional HTTP calls)
        client.fetch_abstract(DOI)
        assert client._session.get.call_count == call_count_after_first
