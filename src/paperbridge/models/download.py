"""Download result models."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class DownloadAttempt(BaseModel):
    source: str
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class DownloadResult(BaseModel):
    success: bool
    file_path: Optional[Path] = None
    format: Optional[str] = None
    source: Optional[str] = None
    file_size_bytes: Optional[int] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    attempts: List[DownloadAttempt] = Field(default_factory=list)
    total_attempts: int = 0
    download_timestamp: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None

    class Config:
        extra = "allow"

    def add_attempt(
        self,
        source: str,
        success: bool,
        url: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        attempt = DownloadAttempt(source=source, success=success, url=url, error=error)
        self.attempts.append(attempt)
        self.total_attempts = len(self.attempts)

    def get_successful_attempt(self) -> Optional[DownloadAttempt]:
        for attempt in self.attempts:
            if attempt.success:
                return attempt
        return None

    def get_attempted_sources(self) -> List[str]:
        return [attempt.source for attempt in self.attempts]

    def summary(self) -> str:
        if self.success:
            return (
                f"Downloaded {self.format} from {self.source} "
                f"({self.file_size_bytes} bytes) to {self.file_path}"
            )
        else:
            sources_tried = ", ".join(self.get_attempted_sources())
            return (
                f"Download failed after {self.total_attempts} attempts "
                f"({sources_tried}). Error: {self.error_message}"
            )
