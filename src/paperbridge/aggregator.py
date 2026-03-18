"""Citation aggregator — fans out DOI lookups across multiple API clients."""

from __future__ import annotations

from loguru import logger

from paperbridge._config import PaperBridgeSettings
from paperbridge.clients._base import BaseAPIClient
from paperbridge.clients.crossref import CrossRefClient
from paperbridge.clients.downloader import PublicationDownloaderClient
from paperbridge.clients.europepmc import EuropePMCClient
from paperbridge.clients.openalex import OpenAlexClient
from paperbridge.clients.pubmed import PubMedClient
from paperbridge.models.article import ArticleRecord
from paperbridge.models.citation_graph import CitationGraph
from paperbridge.models.download import DownloadResult


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

    def fetch_citation_graph(
        self,
        doi: str,
        cited_by_limit: int = 50,
        references_limit: int = 50,
    ) -> CitationGraph | None:
        """Return a bi-directional citation graph for *doi* via OpenAlex.

        Returns None if the DOI is not found in OpenAlex. Does not raise.
        """
        openalex = next(
            (c for c in self.clients if isinstance(c, OpenAlexClient)), None
        )
        if openalex is None:
            logger.warning("No OpenAlexClient in client list — cannot build citation graph")
            return None

        try:
            source_work = openalex.get_work_by_doi(doi)
        except Exception as e:
            logger.error(f"OpenAlex lookup failed for {doi}: {e}")
            return None

        if source_work is None:
            logger.info(f"DOI not found in OpenAlex: {doi}")
            return None

        work_id = source_work.id

        try:
            cited_by = openalex.get_citations(work_id, per_page=cited_by_limit)
        except Exception as e:
            logger.error(f"OpenAlex get_citations failed for {work_id}: {e}")
            cited_by = []

        try:
            references = openalex.get_references(work_id, per_page=references_limit)
        except Exception as e:
            logger.error(f"OpenAlex get_references failed for {work_id}: {e}")
            references = []

        return CitationGraph(
            source_doi=doi,
            source_work=source_work,
            cited_by=cited_by,
            references=references,
            cited_by_count=source_work.cited_by_count,
            reference_count=len(source_work.referenced_works),
        )

    def download_article(
        self,
        doi: str,
        output_dir: str = ".",
    ) -> DownloadResult:
        """Download the full text for *doi* using PublicationDownloaderClient."""
        settings = PaperBridgeSettings()
        email = settings.unpaywall_email
        if not email:
            logger.warning("No email configured (MY_EMAIL/UNPAYWALL_EMAIL) — Unpaywall path unavailable")
            email = "unknown@example.com"
        downloader = PublicationDownloaderClient(email=email)
        return downloader.download_by_identifiers(doi=doi, output_dir=output_dir)

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
