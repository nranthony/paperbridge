"""OpenAlex API client — merged from mygentic (search) + wearable (DOI-based)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from paperbridge.clients._base import BaseAPIClient
from paperbridge.models.article import ArticleAbstract, ArticleKeywords, ArticleMetadata
from paperbridge.models.openalex import OpenAlexFilter, OpenAlexWork

OPENALEX_BASE = "https://api.openalex.org"


class OpenAlexClient(BaseAPIClient):
    """Client for OpenAlex API with both search and DOI-based methods."""

    source_name = "openalex"

    def __init__(self, email: Optional[str] = None, timeout: int = 30, rate_limit: float = 0.11) -> None:
        super().__init__(timeout=timeout)
        self.email = email
        self.rate_limit = rate_limit
        self.last_request_time = 0.0

    def _default_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.email:
            headers["User-Agent"] = f"mailto:{self.email}"
        else:
            headers["User-Agent"] = "paperbridge/0.1"
        return headers

    def _rate_limit_wait(self) -> None:
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        self._rate_limit_wait()
        url = f"{OPENALEX_BASE}{endpoint}"
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    # ── DOI-based methods (wearable pattern) ────────────────────────

    def _fetch_work_raw(self, doi: str) -> dict[str, Any] | None:
        if doi in self._cache:
            return self._cache[doi]
        resp = self.session.get(f"{OPENALEX_BASE}/works/doi:{doi}", timeout=self.timeout)
        if resp.status_code != 200:
            logger.warning(f"OpenAlex: {resp.status_code} for {doi}")
            return None
        data = resp.json()
        self._cache[doi] = data
        return data

    def fetch_keywords(self, doi: str) -> ArticleKeywords | None:
        data = self._fetch_work_raw(doi)
        if data is None:
            return None

        author_keywords: set[str] = set()
        subjects: set[str] = set()

        for kw in data.get("keywords", []):
            name = kw.get("display_name", kw.get("keyword", ""))
            if name:
                author_keywords.add(name)

        for topic in data.get("topics", []):
            name = topic.get("display_name", "")
            if name:
                subjects.add(name)

        logger.info(f"OpenAlex: {len(author_keywords)} keywords + {len(subjects)} topics for {doi}")
        return ArticleKeywords(
            source=self.source_name, author_keywords=sorted(author_keywords), subjects=sorted(subjects)
        )

    def fetch_abstract(self, doi: str) -> ArticleAbstract | None:
        data = self._fetch_work_raw(doi)
        if data is None:
            return None

        abstract_index = data.get("abstract_inverted_index")
        if not abstract_index:
            return None

        words: list[tuple[int, str]] = []
        for word, positions in abstract_index.items():
            for pos in positions:
                words.append((pos, word))
        words.sort()
        text = " ".join(w for _, w in words)
        return ArticleAbstract(source=self.source_name, text=text)

    def fetch_metadata(self, doi: str) -> ArticleMetadata | None:
        data = self._fetch_work_raw(doi)
        if data is None:
            return None

        title = data.get("title")
        authors: list[str] = []
        for a in data.get("authorships", []):
            name = a.get("author", {}).get("display_name", "")
            if name:
                authors.append(name)

        year = data.get("publication_year")
        primary_location = data.get("primary_location") or {}
        source = primary_location.get("source") or {}
        journal = source.get("display_name")
        citation_count = data.get("cited_by_count")

        return ArticleMetadata(
            source=self.source_name,
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            citation_count=citation_count,
            doi=doi,
        )

    # ── Search methods (from mygentic) ──────────────────────────────

    def search_works(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        per_page: int = 25,
        page: int = 1,
        sort: str = "cited_by_count:desc",
    ) -> List[OpenAlexWork]:
        """Search for scholarly works."""
        params: Dict[str, Any] = {
            "search": query,
            "per-page": min(per_page, 200),
            "page": page,
            "sort": sort,
        }
        if filters:
            filter_obj = OpenAlexFilter(**filters)
            filter_str = filter_obj.to_query_string()
            if filter_str:
                params["filter"] = filter_str

        try:
            data = self._make_request("/works", params)
            works = [OpenAlexWork(**result) for result in data.get("results", [])]
            logger.info(f"Found {len(works)} works (total: {data['meta']['count']})")
            return works
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_work_by_id(self, work_id: str) -> Optional[OpenAlexWork]:
        if work_id.startswith("http"):
            work_id = work_id.split("/")[-1]
        try:
            data = self._make_request(f"/works/{work_id}")
            return OpenAlexWork(**data)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_work_by_doi(self, doi: str) -> Optional[OpenAlexWork]:
        if doi.startswith("http"):
            doi = doi.split("doi.org/")[-1]
        try:
            data = self._make_request(f"/works/https://doi.org/{doi}")
            return OpenAlexWork(**data)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_citations(
        self, work_id: str, per_page: int = 25, page: int = 1
    ) -> List[OpenAlexWork]:
        if work_id.startswith("http"):
            work_id = work_id.split("/")[-1]
        params: Dict[str, Any] = {
            "filter": f"cites:{work_id}",
            "per-page": min(per_page, 200),
            "page": page,
            "sort": "cited_by_count:desc",
        }
        try:
            data = self._make_request("/works", params)
            return [OpenAlexWork(**result) for result in data.get("results", [])]
        except Exception as e:
            logger.error(f"Failed to get citations: {e}")
            return []

    def get_references(self, work_id: str, per_page: int = 25, page: int = 1) -> List[OpenAlexWork]:
        if work_id.startswith("http"):
            work_id = work_id.split("/")[-1]
        params: Dict[str, Any] = {
            "filter": f"cited_by:{work_id}",
            "per-page": min(per_page, 200),
            "page": page,
        }
        try:
            data = self._make_request("/works", params)
            return [OpenAlexWork(**result) for result in data.get("results", [])]
        except Exception as e:
            logger.error(f"Failed to get references: {e}")
            return []

    def batch_get_works(self, work_ids: List[str], batch_size: int = 50) -> List[OpenAlexWork]:
        all_works: List[OpenAlexWork] = []
        for i in range(0, len(work_ids), batch_size):
            batch = work_ids[i : i + batch_size]
            filter_str = "|".join(batch)
            try:
                data = self._make_request("/works", {"filter": f"openalex_id:{filter_str}"})
                all_works.extend([OpenAlexWork(**r) for r in data.get("results", [])])
            except Exception as e:
                logger.error(f"Batch fetch failed: {e}")
        return all_works
