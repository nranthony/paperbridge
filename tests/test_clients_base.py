"""Tests for BaseAPIClient shared HTTP plumbing."""

import pytest
from unittest.mock import MagicMock, patch

from paperbridge.clients._base import BaseAPIClient


class ConcreteClient(BaseAPIClient):
    """Minimal concrete subclass for testing."""
    source_name = "test"


class ClientWithOverrides(BaseAPIClient):
    """Subclass that overrides all fetch methods."""
    source_name = "full"

    def fetch_keywords(self, doi):
        return None

    def fetch_abstract(self, doi):
        return None

    def fetch_metadata(self, doi):
        return None

    def fetch_full_text(self, doi):
        return None


class TestBaseAPIClient:
    def test_session_is_lazy(self):
        client = ConcreteClient()
        assert client._session is None
        _ = client.session
        assert client._session is not None

    def test_session_cached(self):
        client = ConcreteClient()
        s1 = client.session
        s2 = client.session
        assert s1 is s2

    def test_close_clears_session_and_cache(self):
        client = ConcreteClient()
        _ = client.session
        client._cache["x"] = {"data": 1}
        client.close()
        assert client._session is None
        assert client._cache == {}

    def test_close_idempotent(self):
        client = ConcreteClient()
        client.close()
        client.close()  # should not raise

    def test_context_manager(self):
        with ConcreteClient() as client:
            assert isinstance(client, ConcreteClient)
        assert client._session is None

    def test_default_fetch_methods_return_none(self):
        client = ConcreteClient()
        assert client.fetch_keywords("10.1234/x") is None
        assert client.fetch_abstract("10.1234/x") is None
        assert client.fetch_metadata("10.1234/x") is None
        assert client.fetch_full_text("10.1234/x") is None

    def test_capabilities_detects_overrides(self):
        client = ClientWithOverrides()
        caps = client.capabilities
        assert "fetch_keywords" in caps
        assert "fetch_abstract" in caps
        assert "fetch_metadata" in caps
        assert "fetch_full_text" in caps

    def test_capabilities_empty_for_base(self):
        client = ConcreteClient()
        assert client.capabilities == []

    def test_repr(self):
        client = ConcreteClient(timeout=15)
        assert "ConcreteClient" in repr(client)
        assert "15" in repr(client)

    def test_get_calls_session(self):
        client = ConcreteClient()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        client.session.get = MagicMock(return_value=mock_response)
        result = client._get("https://example.com", params={"q": "test"})
        client.session.get.assert_called_once_with(
            "https://example.com", params={"q": "test"}, timeout=client.timeout
        )
        assert result is mock_response
