"""DOI Resolver models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DOIHandleValue(BaseModel):
    index: int
    type: str
    data: Dict[str, Any]
    ttl: int
    timestamp: str

    def get_value(self) -> Optional[str]:
        if isinstance(self.data, dict) and "value" in self.data:
            value = self.data["value"]
            if isinstance(value, str):
                return value
            elif isinstance(value, dict):
                return str(value)
        return None


class DOIHandleResponse(BaseModel):
    responseCode: int
    handle: str
    values: List[DOIHandleValue] = Field(default_factory=list)

    def get_url(self) -> Optional[str]:
        for value in self.values:
            if value.type == "URL":
                return value.get_value()
        return None


class DOIResolution(BaseModel):
    doi: str
    url: str
    publisher_domain: Optional[str] = None
    response_code: int

    @classmethod
    def from_handle_response(cls, response: DOIHandleResponse) -> Optional["DOIResolution"]:
        url = response.get_url()
        if not url:
            return None
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return cls(
            doi=response.handle,
            url=url,
            publisher_domain=parsed.netloc,
            response_code=response.responseCode,
        )


class DownloadLink(BaseModel):
    """PDF/XML download link found in HTML page."""

    url: str
    format: str
    link_text: Optional[str] = None
    element_type: Optional[str] = None

    class Config:
        extra = "forbid"
