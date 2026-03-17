"""Open Access status models."""

from typing import List, Optional

from pydantic import BaseModel, Field


class OALocation(BaseModel):
    url: Optional[str] = None
    url_for_pdf: Optional[str] = None
    host_type: Optional[str] = None
    is_best: bool = False
    license: Optional[str] = None
    version: Optional[str] = None
    source: str


class OpenAccessStatus(BaseModel):
    doi: str
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    is_oa: bool = False
    oa_status: Optional[str] = None
    best_oa_location: Optional[OALocation] = None
    oa_locations: List[OALocation] = Field(default_factory=list)
    sources_checked: List[str] = Field(default_factory=list)
    is_pmc_available: bool = False
    is_preprint: bool = False
    preprint_platform: Optional[str] = None
    checked_date: Optional[str] = None
