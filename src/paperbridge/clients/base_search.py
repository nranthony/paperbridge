"""BASE (Bielefeld Academic Search Engine) API client."""

import time
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

from paperbridge.models.base_search import BASEWork


class BASESearchClient:
    """Client for BASE search API. Free, no API key required."""

    BASE_URL = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"

    def __init__(self, rate_limit: float = 1.0, timeout: int = 30):
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "paperbridge (Academic Research)", "Accept": "application/xml"})

    def _rate_limit_wait(self) -> None:
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    def _parse_xml_response(self, xml_content: str) -> List[BASEWork]:
        try:
            soup = BeautifulSoup(xml_content, "xml")
            works = []
            for doc in soup.find_all("doc"):
                work_data: dict = {}
                for field in doc.find_all("field"):
                    field_name = field.get("name")
                    field_value = field.text.strip()
                    if field_name == "dctitle":
                        work_data["title"] = field_value
                    elif field_name == "dclink":
                        work_data["link"] = field_value
                    elif field_name == "dccreator":
                        work_data.setdefault("authors", []).append(field_value)
                    elif field_name == "dcdescription":
                        work_data["abstract"] = field_value
                    elif field_name == "dcyear":
                        work_data["year"] = field_value
                    elif field_name == "dcdate":
                        work_data["date"] = field_value
                    elif field_name == "dcsource":
                        work_data["source"] = field_value
                    elif field_name == "dctype":
                        work_data["type"] = field_value
                    elif field_name == "dcdoi":
                        work_data["doi"] = field_value
                    elif field_name == "dcidentifier":
                        work_data["identifier"] = field_value
                    elif field_name == "dclang":
                        work_data["language"] = field_value
                    elif field_name == "dccollection":
                        work_data["collection"] = field_value
                if work_data:
                    works.append(BASEWork(**work_data))
            return works
        except Exception as e:
            logger.error(f"Failed to parse BASE XML response: {e}")
            return []

    def search(
        self, query: str, max_results: int = 25, page: int = 1, doc_type: Optional[str] = None
    ) -> List[BASEWork]:
        self._rate_limit_wait()
        offset = (page - 1) * max_results
        params: dict = {"func": "PerformSearch", "query": query, "hits": max_results, "offset": offset, "format": "xml"}
        if doc_type:
            params["type"] = doc_type

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            return self._parse_xml_response(response.text)
        except requests.exceptions.RequestException as e:
            logger.error(f"BASE search failed: {e}")
            return []

    def search_articles(self, query: str, max_results: int = 25, page: int = 1) -> List[BASEWork]:
        return self.search(query, max_results=max_results, page=page, doc_type="1")

    def search_theses(self, query: str, max_results: int = 25, page: int = 1) -> List[BASEWork]:
        return self.search(query, max_results=max_results, page=page, doc_type="121")

    def convert_to_citations(self, works: List[BASEWork]):
        return [work.to_simplified_citation() for work in works]
