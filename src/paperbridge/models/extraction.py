"""Article extraction workflow models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from paperbridge.models.download import DownloadResult
from paperbridge.models.document import ParsedDocument
from paperbridge.models.pubmed import SimplifiedCitation


class ExtractionAttempt(BaseModel):
    method: str
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool
    results_found: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CitationReference(BaseModel):
    citation: SimplifiedCitation
    context: str
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)
    extraction_depth: int = 0
    parent_citation: Optional[SimplifiedCitation] = None


class ArticleExtractionResult(BaseModel):
    citation: SimplifiedCitation
    download_result: Optional[DownloadResult] = None
    parsed_document: Optional[ParsedDocument] = None
    supplemental_files: list = Field(default_factory=list)
    extraction_attempts: List[ExtractionAttempt] = Field(default_factory=list)
    citations_to_follow: List[CitationReference] = Field(default_factory=list)
    extraction_depth: int = 0
    success: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    def add_attempt(
        self, method: str, success: bool, results_found: int = 0, error: Optional[str] = None
    ) -> None:
        attempt = ExtractionAttempt(
            method=method, success=success, results_found=results_found, error_message=error
        )
        self.extraction_attempts.append(attempt)

    def get_successful_attempts(self) -> List[ExtractionAttempt]:
        return [a for a in self.extraction_attempts if a.success]

    def summary(self) -> str:
        lines = [
            f"Article: {self.citation.title or 'Unknown'}",
            f"Depth: {self.extraction_depth}",
            f"Success: {self.success}",
            f"Attempts: {len(self.extraction_attempts)} ({len(self.get_successful_attempts())} successful)",
        ]
        if self.citations_to_follow:
            lines.append(f"Citations to Follow: {len(self.citations_to_follow)}")
        if self.error_message:
            lines.append(f"Error: {self.error_message}")
        return "\n".join(lines)
