"""Citation aggregator — fans out DOI lookups across multiple API clients."""

from __future__ import annotations

from loguru import logger

from paperbridge.clients._base import BaseAPIClient
from paperbridge.clients.crossref import CrossRefClient
from paperbridge.clients.europepmc import EuropePMCClient
from paperbridge.clients.openalex import OpenAlexClient
from paperbridge.clients.pubmed import PubMedClient
from paperbridge.models.article import ArticleRecord


class CitationAggregator:
    """Aggregates results from multiple citation API clients."""

    def __init__(self, clients: list[BaseAPIClient] | None = None) -> None:
        if clients is not None:
            self.clients = clients
            self._owns_clients = False
        else:
            self.clients = [PubMedClient(), CrossRefClient(), OpenAlexClient(), EuropePMCClient()]
            self._owns_clients = True

    def fetch_all_keywords(self, doi: str) -> dict[str, list[str]]:
        """Fetch keywords from all sources. Returns dict keyed by source plus a 'combined' superset."""
        results: dict[str, list[str]] = {}
        combined: set[str] = set()

        for client in self.clients:
            try:
                kw = client.fetch_keywords(doi)
                if kw is not None:
                    all_kw = kw.all_keywords
                    results[client.source_name] = all_kw
                    combined.update(all_kw)
                else:
                    results[client.source_name] = []
            except Exception as e:
                logger.error(f"{client.source_name} failed for {doi}: {e}")
                results[client.source_name] = []

        results["combined"] = sorted(combined)
        logger.info(f"Combined: {len(results['combined'])} unique keywords for {doi}")
        return results

    def fetch_article(self, doi: str) -> ArticleRecord:
        """Fetch all available data from all sources for a DOI."""
        record = ArticleRecord(doi=doi)

        for client in self.clients:
            try:
                kw = client.fetch_keywords(doi)
                if kw is not None:
                    record.keywords.append(kw)
            except Exception as e:
                logger.error(f"{client.source_name} keywords failed for {doi}: {e}")

            try:
                abstract = client.fetch_abstract(doi)
                if abstract is not None:
                    record.abstracts.append(abstract)
            except Exception as e:
                logger.error(f"{client.source_name} abstract failed for {doi}: {e}")

            try:
                meta = client.fetch_metadata(doi)
                if meta is not None:
                    record.metadata.append(meta)
            except Exception as e:
                logger.error(f"{client.source_name} metadata failed for {doi}: {e}")

            try:
                ft = client.fetch_full_text(doi)
                if ft is not None:
                    record.full_texts.append(ft)
            except Exception as e:
                logger.error(f"{client.source_name} full_text failed for {doi}: {e}")

        return record

    def close(self) -> None:
        if self._owns_clients:
            for client in self.clients:
                client.close()

    def __enter__(self) -> CitationAggregator:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def __repr__(self) -> str:
        names = [c.source_name for c in self.clients]
        return f"CitationAggregator(clients={names})"
