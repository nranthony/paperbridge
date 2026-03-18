"""Citation graph model — wraps OpenAlex citation/reference data for a single DOI."""

from pydantic import BaseModel

from paperbridge.models.openalex import OpenAlexWork


class CitationGraph(BaseModel):
    """Bi-directional citation graph rooted at a single DOI."""

    source_doi: str
    source_work: OpenAlexWork
    cited_by: list[OpenAlexWork]
    references: list[OpenAlexWork]
    cited_by_count: int
    reference_count: int
