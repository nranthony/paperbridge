"""PubMed E-utilities API client — merged from mygentic (search/fetch) + wearable (DOI-based methods).

Rate Limits: 3 req/sec (no key), 10 req/sec (with key)
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Union

import requests
from loguru import logger

from paperbridge.clients._base import BaseAPIClient
from paperbridge.models.article import ArticleAbstract, ArticleKeywords, ArticleMetadata
from paperbridge.models.pubmed import (
    DateType,
    PubMedPublication,
    PubMedSearchCriteria,
    PubMedSearchResponse,
    PubMedSummaryResponse,
    SortOrder,
)

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedClient(BaseAPIClient):
    """Unified PubMed client with both search/fetch and DOI-based methods."""

    source_name = "pubmed"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        rate_limit: Optional[float] = None,
        max_retries: int = 3,
    ) -> None:
        super().__init__(timeout=timeout)
        self.api_key = api_key or os.environ.get("NCBI_API_KEY", "") or None
        self._pmid_cache: dict[str, str | None] = {}

        if rate_limit is not None:
            self.rate_limit = rate_limit
        elif self.api_key:
            self.rate_limit = 0.11
        else:
            self.rate_limit = 0.34

        self.last_request_time = 0.0
        self.max_retries = max_retries

    def _base_params(self) -> dict[str, str]:
        params: dict[str, str] = {"db": "pubmed"}
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _get_with_rate_limit(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                self.last_request_time = time.time()
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited by server, waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue
                return response
            except Exception as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)

        raise Exception(f"Failed after {self.max_retries} attempts: {last_error}")

    # ── Search API (from mygentic) ──────────────────────────────────

    def search(
        self,
        term: str,
        datetype: Optional[DateType] = None,
        mindate: Optional[str] = None,
        maxdate: Optional[str] = None,
        reldate: Optional[int] = None,
        sort: Optional[SortOrder] = None,
        retstart: int = 0,
        retmax: int = 100,
    ) -> Dict[str, Any]:
        """Search PubMed for publications matching text query."""
        logger.info(f"Searching PubMed for: {term[:100]}...")

        criteria = PubMedSearchCriteria(
            term=term,
            datetype=datetype,
            mindate=mindate,
            maxdate=maxdate,
            reldate=reldate,
            sort=sort or SortOrder.RELEVANCE,
            retstart=retstart,
            retmax=min(retmax, 10000),
        )

        params: Dict[str, Any] = {
            "db": "pubmed",
            "term": criteria.term,
            "retmode": "json",
            "retstart": criteria.retstart,
            "retmax": criteria.retmax,
        }
        if criteria.sort:
            params["sort"] = criteria.sort
        if criteria.datetype:
            params["datetype"] = criteria.datetype
        if criteria.mindate:
            params["mindate"] = criteria.mindate
        if criteria.maxdate:
            params["maxdate"] = criteria.maxdate
        if criteria.reldate:
            params["reldate"] = criteria.reldate
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self._get_with_rate_limit(f"{PUBMED_BASE}/esearch.fcgi", params=params)
            response.raise_for_status()
            data = response.json()
            esearch_result = data.get("esearchresult", {})
            search_response = PubMedSearchResponse(**esearch_result)
            logger.info(f"Found {search_response.count} publications (returned {len(search_response.idlist)})")
            return {
                "pmids": search_response.idlist,
                "count": search_response.count,
                "retstart": search_response.retstart,
                "retmax": search_response.retmax,
                "query_translation": search_response.querytranslation,
            }
        except Exception as e:
            logger.error(f"Failed to search PubMed: {e}")
            return {"pmids": [], "count": 0, "retstart": retstart, "retmax": retmax, "query_translation": None}

    def get_summaries(self, pmids: Union[List[str], List[int]], version: str = "2.0") -> List[PubMedPublication]:
        """Fetch publication summaries for given PMIDs."""
        if not pmids:
            return []

        pmid_strings = [str(pmid) for pmid in pmids]
        logger.info(f"Fetching summaries for {len(pmid_strings)} publications")

        params: Dict[str, Any] = {
            "db": "pubmed",
            "id": ",".join(pmid_strings),
            "retmode": "json",
            "version": version,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self._get_with_rate_limit(f"{PUBMED_BASE}/esummary.fcgi", params=params)
            response.raise_for_status()
            data = response.json()
            summary_response = PubMedSummaryResponse(**data)
            publications = summary_response.get_publications()
            logger.info(f"Retrieved {len(publications)} publication summaries")
            return publications
        except Exception as e:
            logger.error(f"Failed to get publication summaries: {e}")
            return []

    def search_and_fetch(
        self,
        term: str,
        datetype: Optional[DateType] = None,
        mindate: Optional[str] = None,
        maxdate: Optional[str] = None,
        reldate: Optional[int] = None,
        sort: Optional[SortOrder] = None,
        retmax: int = 100,
    ) -> List[PubMedPublication]:
        """Search PubMed and fetch full publication summaries in one call."""
        search_results = self.search(
            term=term, datetype=datetype, mindate=mindate, maxdate=maxdate, reldate=reldate, sort=sort, retmax=retmax
        )
        pmids = search_results.get("pmids", [])
        if not pmids:
            return []
        return self.get_summaries(pmids)

    def search_by_field(
        self, field: str, value: str, additional_filters: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Search PubMed by specific field."""
        term = f"{value}[{field}]"
        if additional_filters:
            term = f"({term}) AND ({additional_filters})"
        return self.search(term=term, **kwargs)

    # ── PMC methods (from mygentic) ─────────────────────────────────

    def get_pmc_id(self, pmid: str) -> Optional[str]:
        """Convert PMID to PMCID using ELink."""
        params = {
            "dbfrom": "pubmed",
            "db": "pmc",
            "id": pmid,
            "linkname": "pubmed_pmc",
            "retmode": "json",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self._get_with_rate_limit(f"{PUBMED_BASE}/elink.fcgi", params=params)
            response.raise_for_status()
            data = response.json()
            linksets = data.get("linksets", [])
            if not linksets:
                return None
            linksetdbs = linksets[0].get("linksetdbs", [])
            if not linksetdbs:
                return None
            pmc_ids = linksetdbs[0].get("links", [])
            if pmc_ids:
                return f"PMC{pmc_ids[0]}"
            return None
        except Exception as e:
            logger.error(f"Failed to convert PMID to PMCID: {e}")
            return None

    def fetch_full_text_xml(self, pmcid: str) -> Optional[str]:
        """Fetch full-text XML from PubMed Central."""
        pmc_number = pmcid.replace("PMC", "")
        params: Dict[str, Any] = {"db": "pmc", "id": pmc_number, "retmode": "xml"}
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self._get_with_rate_limit(f"{PUBMED_BASE}/efetch.fcgi", params=params)
            response.raise_for_status()
            xml_content = response.text
            if "<pmc-articleset>" in xml_content or "<article" in xml_content:
                return xml_content
            return None
        except Exception as e:
            logger.error(f"Failed to fetch full-text XML for {pmcid}: {e}")
            return None

    def check_open_access(self, pmid: str) -> Dict[str, Any]:
        """Check if publication is available in PMC Open Access subset."""
        summaries = self.get_summaries([pmid])
        if not summaries:
            return {"is_pmc_available": False, "pmcid": None, "is_open_access": False, "full_text_xml_available": False}

        pub = summaries[0]
        pmcid = None
        for article_id in pub.articleids:
            if article_id.idtype == "pmc":
                pmcid = f"PMC{article_id.value}"
                break

        if not pmcid:
            pmcid = self.get_pmc_id(pmid)
        if not pmcid:
            return {"is_pmc_available": False, "pmcid": None, "is_open_access": False, "full_text_xml_available": False}

        xml = self.fetch_full_text_xml(pmcid)
        is_open_access = xml is not None
        return {
            "is_pmc_available": True,
            "pmcid": pmcid,
            "is_open_access": is_open_access,
            "full_text_xml_available": is_open_access,
        }

    # ── DOI-based methods (from wearable_publications) ──────────────

    def _doi_to_pmid(self, doi: str) -> str | None:
        if doi in self._pmid_cache:
            return self._pmid_cache[doi]
        params = {**self._base_params(), "term": f"{doi}[doi]", "retmode": "json"}
        resp = self._get_with_rate_limit(f"{PUBMED_BASE}/esearch.fcgi", params=params)
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        pmid = ids[0] if ids else None
        self._pmid_cache[doi] = pmid
        return pmid

    def _fetch_xml(self, doi: str) -> str | None:
        if doi in self._cache:
            return self._cache[doi].get("xml")
        pmid = self._doi_to_pmid(doi)
        if not pmid:
            logger.warning(f"No PMID found for DOI: {doi}")
            return None
        params = {**self._base_params(), "id": pmid, "retmode": "xml"}
        resp = self._get_with_rate_limit(f"{PUBMED_BASE}/efetch.fcgi", params=params)
        xml = resp.text
        self._cache[doi] = {"xml": xml, "pmid": pmid}
        return xml

    def fetch_keywords(self, doi: str) -> ArticleKeywords | None:
        xml = self._fetch_xml(doi)
        if xml is None:
            return None

        mesh_terms: list[str] = []
        author_keywords: list[str] = []

        for m in re.finditer(r"<DescriptorName[^>]*>([^<]+)</DescriptorName>", xml):
            mesh_terms.append(m.group(1))
        for m in re.finditer(r"<Keyword[^>]*>([^<]+)</Keyword>", xml):
            author_keywords.append(m.group(1))

        mesh_terms = sorted(set(mesh_terms))
        author_keywords = sorted(set(author_keywords))

        logger.info(f"PubMed: {len(mesh_terms)} MeSH + {len(author_keywords)} author keywords for {doi}")
        return ArticleKeywords(source=self.source_name, mesh_terms=mesh_terms, author_keywords=author_keywords)

    def fetch_abstract(self, doi: str) -> ArticleAbstract | None:
        xml = self._fetch_xml(doi)
        if xml is None:
            return None

        structured = bool(re.search(r"<AbstractText\s+Label=", xml))
        abstract_parts: list[str] = []
        for m in re.finditer(r"<AbstractText[^>]*>(.*?)</AbstractText>", xml, re.DOTALL):
            abstract_parts.append(m.group(1).strip())

        if not abstract_parts:
            return None

        text = " ".join(abstract_parts)
        text = re.sub(r"<[^>]+>", "", text)
        return ArticleAbstract(source=self.source_name, text=text, structured=structured)

    def fetch_metadata(self, doi: str) -> ArticleMetadata | None:
        xml = self._fetch_xml(doi)
        if xml is None:
            return None

        pmid = self._cache.get(doi, {}).get("pmid")
        title_match = re.search(r"<ArticleTitle>(.+?)</ArticleTitle>", xml, re.DOTALL)
        title = re.sub(r"<[^>]+>", "", title_match.group(1).strip()) if title_match else None

        authors: list[str] = []
        for m in re.finditer(
            r"<Author[^>]*>.*?<LastName>([^<]+)</LastName>.*?<ForeName>([^<]+)</ForeName>.*?</Author>",
            xml,
            re.DOTALL,
        ):
            authors.append(f"{m.group(2)} {m.group(1)}")

        year_match = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", xml, re.DOTALL)
        year = int(year_match.group(1)) if year_match else None

        journal_match = re.search(r"<Title>([^<]+)</Title>", xml)
        journal = journal_match.group(1) if journal_match else None

        return ArticleMetadata(
            source=self.source_name, title=title, authors=authors, year=year, journal=journal, doi=doi, pmid=pmid
        )
