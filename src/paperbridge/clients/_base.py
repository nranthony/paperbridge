"""Base API client ABC from wearable_publications pattern."""

from __future__ import annotations

from abc import ABC
from typing import Any

import requests
from loguru import logger

from paperbridge.models.article import ArticleAbstract, ArticleKeywords, ArticleMetadata, FullText


class BaseAPIClient(ABC):
    """Base class for citation API clients.

    Provides shared HTTP plumbing (session, headers, timeout, error handling)
    and stub data methods that subclasses override selectively.
    """

    source_name: str = "base"

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        self._session: requests.Session | None = None
        self._cache: dict[str, dict] = {}

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self._default_headers())
        return self._session

    def _default_headers(self) -> dict[str, str]:
        return {}

    def _get(self, url: str, params: dict[str, Any] | None = None) -> requests.Response:
        logger.debug(f"{self.source_name}: GET {url} params={params}")
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp

    def fetch_keywords(self, doi: str) -> ArticleKeywords | None:
        return None

    def fetch_abstract(self, doi: str) -> ArticleAbstract | None:
        return None

    def fetch_metadata(self, doi: str) -> ArticleMetadata | None:
        return None

    def fetch_full_text(self, doi: str) -> FullText | None:
        return None

    @property
    def capabilities(self) -> list[str]:
        caps = []
        for method_name in ("fetch_keywords", "fetch_abstract", "fetch_metadata", "fetch_full_text"):
            if type(self).__dict__.get(method_name) is not None:
                caps.append(method_name)
        return caps

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None
        self._cache.clear()

    def __enter__(self) -> BaseAPIClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(timeout={self.timeout})"
