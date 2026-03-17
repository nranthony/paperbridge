"""CrossRef API Client — merged from mygentic (search) + wearable (DOI-based)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from paperbridge.clients._base import BaseAPIClient
from paperbridge.models.article import ArticleAbstract, ArticleKeywords, ArticleMetadata
from paperbridge.models.crossref import CrossRefAuthor, CrossRefWork

CROSSREF_BASE = "https://api.crossref.org"


class CrossRefClient(BaseAPIClient):
    """Client for CrossRef REST API with both search and DOI-based methods."""

    source_name = "crossref"

    def __init__(self, email: Optional[str] = None, timeout: int = 30) -> None:
        super().__init__(timeout=timeout)
        self.email = email

    def _default_headers(self) -> dict[str, str]:
        ua = f"paperbridge/0.1 (mailto:{self.email})" if self.email else "paperbridge/0.1"
        return {"User-Agent": ua}

    # ── DOI-based methods (wearable pattern) ────────────────────────

    def _fetch_work_raw(self, doi: str) -> dict[str, Any] | None:
        if doi in self._cache:
            return self._cache[doi]
        resp = self.session.get(f"{CROSSREF_BASE}/works/{doi}", timeout=self.timeout)
        if resp.status_code != 200:
            logger.warning(f"CrossRef: {resp.status_code} for {doi}")
            return None
        msg = resp.json().get("message", {})
        self._cache[doi] = msg
        return msg

    def fetch_keywords(self, doi: str) -> ArticleKeywords | None:
        msg = self._fetch_work_raw(doi)
        if msg is None:
            return None
        subjects = sorted(set(msg.get("subject", [])))
        logger.info(f"CrossRef: {len(subjects)} subjects for {doi}")
        return ArticleKeywords(source=self.source_name, subjects=subjects)

    def fetch_abstract(self, doi: str) -> ArticleAbstract | None:
        msg = self._fetch_work_raw(doi)
        if msg is None:
            return None
        abstract = msg.get("abstract", "")
        if not abstract:
            return None
        text = re.sub(r"<[^>]+>", "", abstract).strip()
        return ArticleAbstract(source=self.source_name, text=text)

    def fetch_metadata(self, doi: str) -> ArticleMetadata | None:
        msg = self._fetch_work_raw(doi)
        if msg is None:
            return None

        title_list = msg.get("title", [])
        title = title_list[0] if title_list else None

        authors: list[str] = []
        for a in msg.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            authors.append(f"{given} {family}".strip())

        year = None
        date_parts = msg.get("published-print", msg.get("published-online", {})).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]

        journal_list = msg.get("container-title", [])
        journal = journal_list[0] if journal_list else None
        citation_count = msg.get("is-referenced-by-count")

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

    def get_work_by_doi(self, doi: str) -> Optional[CrossRefWork]:
        """Retrieve CrossRefWork metadata for a DOI."""
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        try:
            response = requests.get(
                f"{CROSSREF_BASE}/works/{doi}", headers=self._default_headers(), timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "ok" and "message" in data:
                return CrossRefWork(**data["message"])
            return None
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"DOI not found in CrossRef: {doi}")
            else:
                logger.warning(f"CrossRef API error for {doi}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch CrossRef metadata for {doi}: {e}")
            return None

    def search_works(
        self, query: str, rows: int = 5, filter_params: Optional[Dict[str, str]] = None
    ) -> List[CrossRefWork]:
        """Search CrossRef for publications matching a query."""
        params: Dict[str, Any] = {"query": query, "rows": min(rows, 1000)}
        if filter_params:
            filter_str = ",".join([f"{k}:{v}" for k, v in filter_params.items()])
            params["filter"] = filter_str

        try:
            response = requests.get(
                f"{CROSSREF_BASE}/works", params=params, headers=self._default_headers(), timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "ok" and "message" in data:
                items = data["message"].get("items", [])
                return [CrossRefWork(**item) for item in items]
            return []
        except Exception as e:
            logger.warning(f"CrossRef search failed for '{query}': {e}")
            return []

    def search_by_title_author(
        self, title: str, author: Optional[str] = None, year: Optional[int] = None
    ) -> List[CrossRefWork]:
        """Search by title and optionally author/year."""
        query_parts = [title]
        if author:
            query_parts.append(author)
        if year:
            query_parts.append(str(year))
        query = " ".join(query_parts)

        params: Dict[str, Any] = {"query.bibliographic": query, "rows": 5}
        try:
            response = requests.get(
                f"{CROSSREF_BASE}/works", params=params, headers=self._default_headers(), timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "ok" and "message" in data:
                return [CrossRefWork(**item) for item in data["message"].get("items", [])]
            return []
        except Exception as e:
            logger.warning(f"CrossRef title search failed: {e}")
            return []

    def get_doi_from_title(self, title: str, author: Optional[str] = None, year: Optional[int] = None) -> Optional[str]:
        """Get DOI by searching with title/author/year."""
        results = self.search_by_title_author(title, author, year)
        if results and results[0].doi:
            return results[0].doi
        return None
