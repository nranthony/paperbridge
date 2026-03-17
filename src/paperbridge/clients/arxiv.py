"""ArXiv family client (arXiv, bioRxiv, medRxiv, chemRxiv)."""

from datetime import datetime
from typing import List, Literal, Optional
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import requests
from loguru import logger

from paperbridge.models.arxiv import ArXivPreprint, ArXivSearchResult


class ArXivFamilyClient:
    """Unified client for arXiv family platforms."""

    PLATFORMS = {
        "arxiv": {
            "api_url": "http://export.arxiv.org/api/query",
            "pdf_pattern": "https://arxiv.org/pdf/{arxiv_id}.pdf",
        },
        "biorxiv": {
            "api_url": "https://api.biorxiv.org/details/biorxiv",
            "pdf_pattern": "https://www.biorxiv.org/content/{doi}v{version}.full.pdf",
            "html_pattern": "https://www.biorxiv.org/content/{doi}v{version}",
        },
        "medrxiv": {
            "api_url": "https://api.biorxiv.org/details/medrxiv",
            "pdf_pattern": "https://www.medrxiv.org/content/{doi}v{version}.full.pdf",
            "html_pattern": "https://www.medrxiv.org/content/{doi}v{version}",
        },
        "chemarxiv": {
            "api_url": None,
            "pdf_pattern": "https://chemrxiv.org/engage/api-gateway/chemrxiv/assets/orp/resource/item/{item_id}/original",
            "html_pattern": "https://chemrxiv.org/engage/chemrxiv/article-details/{doi}",
        },
    }

    def __init__(
        self,
        platform: Literal["arxiv", "biorxiv", "medrxiv", "chemarxiv"] = "arxiv",
        timeout: int = 30,
    ):
        if platform not in self.PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}. Supported: {list(self.PLATFORMS.keys())}")
        self.platform = platform
        self.timeout = timeout
        self.config = self.PLATFORMS[platform]

    def search(self, query: str, max_results: int = 10, start: int = 0) -> ArXivSearchResult:
        if self.platform == "arxiv":
            return self._search_arxiv(query, max_results, start)
        raise NotImplementedError(f"{self.platform} doesn't support search via API.")

    def _search_arxiv(self, query: str, max_results: int, start: int) -> ArXivSearchResult:
        params = {"search_query": f"all:{query}", "start": start, "max_results": max_results}
        url = f"{self.config['api_url']}?{urlencode(params)}"

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        total_results_el = root.find("atom:totalResults", ns)
        total = int(total_results_el.text) if total_results_el is not None else 0

        preprints = []
        for entry in root.findall("atom:entry", ns):
            preprint = self._parse_arxiv_entry(entry, ns)
            if preprint:
                preprints.append(preprint)

        return ArXivSearchResult(
            query=query, total_results=total, returned_results=len(preprints), start_index=start,
            preprints=preprints, platform="arxiv",
        )

    def _parse_arxiv_entry(self, entry, ns) -> Optional[ArXivPreprint]:
        try:
            arxiv_id_tag = entry.find("atom:id", ns)
            arxiv_id = arxiv_id_tag.text.split("/abs/")[-1] if arxiv_id_tag is not None else None

            version = None
            if arxiv_id and "v" in arxiv_id:
                arxiv_id, version = arxiv_id.rsplit("v", 1)
                version = f"v{version}"

            doi_tag = entry.find("arxiv:doi", ns)
            doi = doi_tag.text if doi_tag is not None else arxiv_id

            title_tag = entry.find("atom:title", ns)
            title = title_tag.text.strip() if title_tag is not None else "Untitled"

            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns)
                if name is not None:
                    authors.append(name.text)

            summary_tag = entry.find("atom:summary", ns)
            abstract = summary_tag.text.strip() if summary_tag is not None else ""

            published_tag = entry.find("atom:published", ns)
            published_date = (
                datetime.fromisoformat(published_tag.text.replace("Z", "+00:00"))
                if published_tag is not None
                else datetime.now()
            )

            updated_tag = entry.find("atom:updated", ns)
            updated_date = (
                datetime.fromisoformat(updated_tag.text.replace("Z", "+00:00"))
                if updated_tag is not None
                else None
            )

            categories = []
            for category in entry.findall("atom:category", ns):
                term = category.get("term")
                if term:
                    categories.append(term)

            pdf_url = self.config["pdf_pattern"].format(arxiv_id=arxiv_id)

            journal_ref_tag = entry.find("arxiv:journal_ref", ns)
            journal_ref = journal_ref_tag.text if journal_ref_tag is not None else None

            comment_tag = entry.find("arxiv:comment", ns)
            comments = comment_tag.text if comment_tag is not None else None

            return ArXivPreprint(
                doi=doi, title=title, authors=authors, abstract=abstract,
                published_date=published_date, updated_date=updated_date,
                pdf_url=pdf_url, platform="arxiv", categories=categories,
                version=version, arxiv_id=arxiv_id, journal_ref=journal_ref, comments=comments,
            )
        except Exception as e:
            logger.warning(f"Failed to parse arXiv entry: {e}")
            return None

    def get_by_doi(self, doi: str) -> Optional[ArXivPreprint]:
        if self.platform == "arxiv":
            return self._get_arxiv_by_id(doi)
        elif self.platform in ["biorxiv", "medrxiv"]:
            return self._get_biorxiv_by_doi(doi)
        return None

    def _get_arxiv_by_id(self, arxiv_id: str) -> Optional[ArXivPreprint]:
        params = {"id_list": arxiv_id, "max_results": 1}
        url = f"{self.config['api_url']}?{urlencode(params)}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        entry = root.find("atom:entry", ns)
        return self._parse_arxiv_entry(entry, ns) if entry is not None else None

    def _get_biorxiv_by_doi(self, doi: str) -> Optional[ArXivPreprint]:
        version = "1"
        if "v" in doi:
            doi_base, version = doi.rsplit("v", 1)
        else:
            doi_base = doi

        pdf_url = self.config["pdf_pattern"].format(doi=doi_base, version=version)
        html_url = self.config.get("html_pattern", "").format(doi=doi_base, version=version)

        return ArXivPreprint(
            doi=doi, title=f"Preprint {doi}", authors=[], abstract="",
            published_date=datetime.now(), pdf_url=pdf_url, html_url=html_url,
            platform=self.platform, version=f"v{version}",
        )

    def get_pdf_url(self, doi: str) -> Optional[str]:
        if self.platform == "arxiv":
            return self.config["pdf_pattern"].format(arxiv_id=doi)
        elif self.platform in ["biorxiv", "medrxiv"]:
            version = "1"
            if "v" in doi:
                doi, version = doi.rsplit("v", 1)
            return self.config["pdf_pattern"].format(doi=doi, version=version)
        return None

    def download_pdf(self, doi: str, output_path: str) -> bool:
        pdf_url = self.get_pdf_url(doi)
        if not pdf_url:
            return False
        try:
            html_url = pdf_url.replace(".full.pdf", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": html_url,
            }
            response = requests.get(pdf_url, timeout=self.timeout, headers=headers, stream=True, allow_redirects=True)
            response.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            logger.error(f"Failed to download PDF: {e}")
            return False

    def check_availability(self, doi: str) -> bool:
        pdf_url = self.get_pdf_url(doi)
        if not pdf_url:
            return False
        try:
            html_url = pdf_url.replace(".full.pdf", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": html_url,
            }
            response = requests.get(pdf_url, timeout=self.timeout, headers=headers, stream=True, allow_redirects=True)
            return response.status_code == 200
        except Exception:
            return False
