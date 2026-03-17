"""Unpaywall Client for checking open access availability."""

from typing import Optional

import requests
from loguru import logger

from paperbridge.models.open_access import OALocation, OpenAccessStatus


class UnpaywallClient:
    """Unpaywall API client. Requires an email address."""

    BASE_URL = "https://api.unpaywall.org/v2"

    def __init__(self, email: str, timeout: int = 30):
        if not email:
            raise ValueError("Email address is required for Unpaywall API")
        self.email = email
        self.timeout = timeout

    def check_oa_status(self, doi: str) -> OpenAccessStatus:
        url = f"{self.BASE_URL}/{doi}"
        params = {"email": self.email}
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            if response.status_code == 404:
                return OpenAccessStatus(doi=doi, is_oa=False, sources_checked=["unpaywall"])
            response.raise_for_status()
            return self._parse_response(response.json())
        except Exception as e:
            logger.error(f"Failed to check OA status for {doi}: {e}")
            raise

    def get_best_pdf_url(self, doi: str) -> Optional[str]:
        try:
            status = self.check_oa_status(doi)
            if status.best_oa_location and status.best_oa_location.url_for_pdf:
                return status.best_oa_location.url_for_pdf
            return None
        except Exception:
            return None

    def _parse_response(self, data: dict) -> OpenAccessStatus:
        best_oa_location = None
        best_loc_data = data.get("best_oa_location")
        if best_loc_data:
            best_oa_location = OALocation(
                url=best_loc_data.get("url"),
                url_for_pdf=best_loc_data.get("url_for_pdf"),
                host_type=best_loc_data.get("host_type"),
                is_best=True,
                license=best_loc_data.get("license"),
                version=best_loc_data.get("version"),
                source="unpaywall",
            )

        oa_locations = []
        for loc_data in data.get("oa_locations", []):
            oa_locations.append(
                OALocation(
                    url=loc_data.get("url"),
                    url_for_pdf=loc_data.get("url_for_pdf"),
                    host_type=loc_data.get("host_type"),
                    is_best=loc_data.get("is_best", False),
                    license=loc_data.get("license"),
                    version=loc_data.get("version"),
                    source="unpaywall",
                )
            )

        return OpenAccessStatus(
            doi=data.get("doi", ""),
            is_oa=data.get("is_oa", False),
            oa_status=data.get("oa_status"),
            best_oa_location=best_oa_location,
            oa_locations=oa_locations,
            sources_checked=["unpaywall"],
        )
