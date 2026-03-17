"""Europe PMC client (unique to wearable_publications)."""

from __future__ import annotations

from typing import Any

from loguru import logger

from paperbridge.clients._base import BaseAPIClient
from paperbridge.models.article import ArticleAbstract, ArticleKeywords, ArticleMetadata, FullText

EUROPEPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPEPMC_FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest"


class EuropePMCClient(BaseAPIClient):
    source_name = "europepmc"

    def _fetch_article(self, doi: str) -> dict[str, Any] | None:
        if doi in self._cache:
            return self._cache[doi]
        resp = self.session.get(
            EUROPEPMC_SEARCH,
            params={"query": f"DOI:{doi}", "resultType": "core", "format": "json"},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            logger.warning(f"Europe PMC: {resp.status_code} for {doi}")
            return None
        results = resp.json().get("resultList", {}).get("result", [])
        if not results:
            return None
        article = results[0]
        self._cache[doi] = article
        return article

    def fetch_keywords(self, doi: str) -> ArticleKeywords | None:
        article = self._fetch_article(doi)
        if article is None:
            return None

        author_keywords: set[str] = set()
        mesh_terms: set[str] = set()

        for kw in article.get("keywordList", {}).get("keyword", []):
            if kw:
                author_keywords.add(kw)
        for mh in article.get("meshHeadingList", {}).get("meshHeading", []):
            name = mh.get("descriptorName", "")
            if name:
                mesh_terms.add(name)

        logger.info(f"Europe PMC: {len(mesh_terms)} MeSH + {len(author_keywords)} keywords for {doi}")
        return ArticleKeywords(
            source=self.source_name, mesh_terms=sorted(mesh_terms), author_keywords=sorted(author_keywords)
        )

    def fetch_abstract(self, doi: str) -> ArticleAbstract | None:
        article = self._fetch_article(doi)
        if article is None:
            return None
        abstract = article.get("abstractText", "")
        if not abstract:
            return None
        return ArticleAbstract(source=self.source_name, text=abstract)

    def fetch_metadata(self, doi: str) -> ArticleMetadata | None:
        article = self._fetch_article(doi)
        if article is None:
            return None

        title = article.get("title")
        authors: list[str] = []
        for a in article.get("authorList", {}).get("author", []):
            full = a.get("fullName", "")
            if full:
                authors.append(full)

        year_str = article.get("pubYear")
        year = int(year_str) if year_str and year_str.isdigit() else None
        journal = article.get("journalTitle")
        citation_count = article.get("citedByCount")
        pmid = article.get("pmid")

        return ArticleMetadata(
            source=self.source_name,
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            citation_count=citation_count,
            doi=doi,
            pmid=pmid,
        )

    def fetch_full_text(self, doi: str) -> FullText | None:
        article = self._fetch_article(doi)
        if article is None:
            return None
        pmcid = article.get("pmcid")
        if not pmcid:
            return None
        try:
            resp = self._get(f"{EUROPEPMC_FULLTEXT}/{pmcid}/fullTextXML")
        except Exception:
            logger.warning(f"Europe PMC: full text not available for {pmcid}")
            return None
        return FullText(source=self.source_name, text=resp.text, format="xml")
