"""Publication Downloader — orchestrator for downloading from multiple sources."""

import re
from pathlib import Path
from typing import List, Optional

import requests
from loguru import logger

from paperbridge.clients.arxiv import ArXivFamilyClient
from paperbridge.clients.doi import DOIResolverClient
from paperbridge.clients.pubmed import PubMedClient
from paperbridge.clients.unpaywall import UnpaywallClient
from paperbridge.models.download import DownloadResult
from paperbridge.models.pubmed import SimplifiedCitation


class PublicationDownloaderClient:
    """Unified client for downloading publications from multiple sources.

    Priority: PMC -> Preprints -> DOI resolution -> Unpaywall -> Direct URL
    """

    def __init__(
        self,
        email: str,
        pubmed_client: Optional[PubMedClient] = None,
        unpaywall_client: Optional[UnpaywallClient] = None,
        timeout: int = 30,
    ):
        self.email = email
        self.timeout = timeout
        self.pubmed_client = pubmed_client or PubMedClient()
        self.unpaywall_client = unpaywall_client or UnpaywallClient(email=email)
        self.doi_resolver = DOIResolverClient(timeout=timeout)

    def download_from_citation(
        self, citation: SimplifiedCitation, output_dir: str = ".", formats: Optional[List[str]] = None,
        filename: Optional[str] = None,
    ) -> DownloadResult:
        if formats is None:
            formats = ["pdf", "xml"]
        return self.download_by_identifiers(
            doi=citation.doi, pmid=citation.pmid, pmcid=citation.pmc_id, url=citation.url,
            output_dir=output_dir, formats=formats, filename=filename,
        )

    def download_by_identifiers(
        self, doi: Optional[str] = None, pmid: Optional[str] = None, pmcid: Optional[str] = None,
        url: Optional[str] = None, output_dir: str = ".", formats: Optional[List[str]] = None,
        filename: Optional[str] = None,
    ) -> DownloadResult:
        if formats is None:
            formats = ["pdf", "xml"]

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        result = DownloadResult(success=False, doi=doi, pmid=pmid, pmcid=pmcid)

        # PRIORITY 1: PMC
        if pmid or pmcid:
            output_file = self._gen_path(output_path, doi, pmid, pmcid, filename, "xml")
            downloaded_path = self._try_pmc(pmid, pmcid, output_file)
            if downloaded_path:
                return self._success(result, downloaded_path, "pmc", "xml", doi, pmid, pmcid)

        # PRIORITY 2: Preprints
        if doi and self._detect_preprint(doi):
            output_file = self._gen_path(output_path, doi, pmid, pmcid, filename, "pdf")
            downloaded_path = self._try_preprint(doi, output_file)
            if downloaded_path:
                return self._success(result, downloaded_path, "preprint", "pdf", doi, pmid, pmcid)

        # PRIORITY 3: Unpaywall
        if doi and "pdf" in formats:
            output_file = self._gen_path(output_path, doi, pmid, pmcid, filename, "pdf")
            downloaded_path = self._try_unpaywall(doi, output_file)
            if downloaded_path:
                return self._success(result, downloaded_path, "unpaywall", "pdf", doi, pmid, pmcid)

        # PRIORITY 4: Direct URL
        if url:
            output_file = self._gen_path(output_path, doi, pmid, pmcid, filename, "pdf")
            downloaded_path = self._download_file(url, output_file)
            if downloaded_path:
                return self._success(result, downloaded_path, "url", "pdf", doi, pmid, pmcid)

        result.error_message = f"All {result.total_attempts} download sources exhausted."
        return result

    def _detect_preprint(self, doi: str) -> Optional[str]:
        if doi.startswith("10.1101/"):
            return "biorxiv_medrxiv"
        if "arxiv" in doi.lower() or re.match(r"^\d{4}\.\d{4,5}", doi):
            return "arxiv"
        return None

    def _gen_path(self, output_dir: Path, doi, pmid, pmcid, filename, ext) -> Path:
        if filename:
            return output_dir / filename
        identifier = doi or pmid or pmcid or "publication"
        safe_id = identifier.replace("/", "_").replace(":", "_")
        return output_dir / f"{safe_id}.{ext}"

    def _success(self, result, file_path, source, fmt, doi, pmid, pmcid) -> DownloadResult:
        result.success = True
        result.file_path = file_path
        result.format = fmt
        result.source = source
        result.file_size_bytes = file_path.stat().st_size
        result.doi = doi
        result.pmid = pmid
        result.pmcid = pmcid
        result.add_attempt(source=source, success=True, url=str(file_path))
        return result

    def _try_pmc(self, pmid, pmcid, output_file) -> Optional[Path]:
        try:
            if not pmcid and pmid:
                pmcid = self.pubmed_client.get_pmc_id(pmid)
            if not pmcid:
                return None
            xml_content = self.pubmed_client.fetch_full_text_xml(pmcid)
            if not xml_content:
                return None
            output_file.write_text(xml_content, encoding="utf-8")
            return output_file
        except Exception as e:
            logger.debug(f"PMC download failed: {e}")
            return None

    def _try_preprint(self, doi: str, output_file: Path) -> Optional[Path]:
        try:
            platforms = ["biorxiv", "medrxiv"] if doi.startswith("10.1101/") else ["arxiv"]
            for platform in platforms:
                client = ArXivFamilyClient(platform=platform, timeout=self.timeout)
                if client.check_availability(doi) and client.download_pdf(doi, str(output_file)):
                    if output_file.exists():
                        return output_file
            return None
        except Exception:
            return None

    def _try_unpaywall(self, doi: str, output_file: Path) -> Optional[Path]:
        try:
            pdf_url = self.unpaywall_client.get_best_pdf_url(doi)
            if not pdf_url:
                return None
            return self._download_file(pdf_url, output_file)
        except Exception:
            return None

    def _download_file(self, url: str, output_file: Path) -> Optional[Path]:
        try:
            response = requests.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return output_file
        except Exception:
            return None
