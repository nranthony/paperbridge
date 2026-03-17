"""DOI Resolver Client."""

from typing import Optional

import requests
from loguru import logger

from paperbridge.models.doi import DOIHandleResponse, DOIResolution


class DOIResolverClient:
    """Client for resolving DOIs using the Handle API."""

    HANDLE_API_BASE = "https://doi.org/api/handles"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def resolve(self, doi: str) -> Optional[DOIResolution]:
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        try:
            url = f"{self.HANDLE_API_BASE}/{clean_doi}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            handle_response = DOIHandleResponse(**response.json())
            if handle_response.responseCode != 1:
                return None
            resolution = DOIResolution.from_handle_response(handle_response)
            if resolution:
                logger.info(f"Resolved {clean_doi} -> {resolution.url}")
            return resolution
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"DOI not found: {clean_doi}")
            else:
                logger.error(f"HTTP error resolving DOI {clean_doi}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error resolving DOI {clean_doi}: {e}")
            return None

    def check_doi_exists(self, doi: str) -> bool:
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        try:
            response = requests.head(f"{self.HANDLE_API_BASE}/{clean_doi}", timeout=self.timeout)
            return response.status_code == 200
        except Exception:
            return False

    def get_raw_response(self, doi: str) -> Optional[dict]:
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        try:
            response = requests.get(f"{self.HANDLE_API_BASE}/{clean_doi}", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
