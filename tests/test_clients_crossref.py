"""Tests for CrossRefClient using mocked HTTP responses."""

import pytest
from unittest.mock import MagicMock, patch

from paperbridge.clients.crossref import CrossRefClient

DOI = "10.1038/s41586-021-03819-2"

CROSSREF_WORK_FIXTURE = {
    "title": ["Programmable base editing"],
    "author": [
        {"given": "David", "family": "Liu"},
        {"given": "Andrew", "family": "Anzalone"},
    ],
    "published-print": {"date-parts": [[2021, 10, 1]]},
    "container-title": ["Nature"],
    "is-referenced-by-count": 1200,
    "subject": ["Biochemistry", "Genetics"],
    "abstract": "<jats:p>A study of base editing.</jats:p>",
}


def _mock_crossref_response(data: dict, status: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = {"status": "ok", "message": data}
    return mock_resp


class TestCrossRefClientDOIMethods:
    def test_fetch_metadata(self):
        client = CrossRefClient()
        client._session = MagicMock()
        client._session.get.return_value = _mock_crossref_response(CROSSREF_WORK_FIXTURE)
        client._session.headers = MagicMock()

        meta = client.fetch_metadata(DOI)

        assert meta is not None
        assert meta.source == "crossref"
        assert meta.title == "Programmable base editing"
        assert "David Liu" in meta.authors
        assert meta.year == 2021
        assert meta.journal == "Nature"
        assert meta.citation_count == 1200
        assert meta.doi == DOI

    def test_fetch_keywords(self):
        client = CrossRefClient()
        client._session = MagicMock()
        client._session.get.return_value = _mock_crossref_response(CROSSREF_WORK_FIXTURE)
        client._session.headers = MagicMock()

        kw = client.fetch_keywords(DOI)

        assert kw is not None
        assert kw.source == "crossref"
        assert "Biochemistry" in kw.subjects
        assert "Genetics" in kw.subjects

    def test_fetch_abstract_strips_xml_tags(self):
        client = CrossRefClient()
        client._session = MagicMock()
        client._session.get.return_value = _mock_crossref_response(CROSSREF_WORK_FIXTURE)
        client._session.headers = MagicMock()

        ab = client.fetch_abstract(DOI)

        assert ab is not None
        assert ab.source == "crossref"
        assert "<jats:p>" not in ab.text
        assert "base editing" in ab.text

    def test_fetch_abstract_returns_none_when_missing(self):
        fixture = {**CROSSREF_WORK_FIXTURE, "abstract": ""}
        client = CrossRefClient()
        client._session = MagicMock()
        client._session.get.return_value = _mock_crossref_response(fixture)
        client._session.headers = MagicMock()

        assert client.fetch_abstract(DOI) is None

    def test_fetch_returns_none_on_404(self):
        client = CrossRefClient()
        client._session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        client._session.get.return_value = mock_resp
        client._session.headers = MagicMock()

        assert client.fetch_metadata(DOI) is None
        assert client.fetch_keywords(DOI) is None
        assert client.fetch_abstract(DOI) is None

    def test_cache_prevents_duplicate_requests(self):
        client = CrossRefClient()
        client._session = MagicMock()
        client._session.get.return_value = _mock_crossref_response(CROSSREF_WORK_FIXTURE)
        client._session.headers = MagicMock()

        client.fetch_metadata(DOI)
        client.fetch_keywords(DOI)
        client.fetch_abstract(DOI)

        assert client._session.get.call_count == 1

    def test_default_headers_no_email(self):
        client = CrossRefClient()
        headers = client._default_headers()
        assert "paperbridge" in headers["User-Agent"]

    def test_default_headers_with_email(self):
        client = CrossRefClient(email="test@example.com")
        headers = client._default_headers()
        assert "test@example.com" in headers["User-Agent"]

    def test_source_name(self):
        assert CrossRefClient.source_name == "crossref"
