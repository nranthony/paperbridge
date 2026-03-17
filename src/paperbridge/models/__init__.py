"""paperbridge.models — Pydantic models for all supported APIs."""

from paperbridge.models.article import (
    ArticleAbstract,
    ArticleKeywords,
    ArticleMetadata,
    ArticleRecord,
    FullText,
    KeywordScore,
    KeywordScoreList,
    iter_keywords,
)
from paperbridge.models.arxiv import ArXivPreprint, ArXivSearchResult
from paperbridge.models.base_search import BASESearchResponse, BASEWork
from paperbridge.models.citation_workflow import (
    CitationVerificationResult,
    ContraryQuery,
    SearchResult,
    SearchTier,
    SupportType,
    VerificationAssessment,
    VerificationStatus,
    WorkflowInput,
    WorkflowOutput,
)
from paperbridge.models.crossref import CrossRefAuthor, CrossRefWork
from paperbridge.models.document import (
    ContentAssessment,
    DocumentMetadata,
    DocumentReference,
    DocumentSection,
    ParsedDocument,
    SupplementalFile,
    Table,
)
from paperbridge.models.doi import DOIHandleResponse, DOIHandleValue, DOIResolution, DownloadLink
from paperbridge.models.download import DownloadAttempt, DownloadResult
from paperbridge.models.europepmc import EuropePMCArticle
from paperbridge.models.extraction import ArticleExtractionResult, CitationReference, ExtractionAttempt
from paperbridge.models.open_access import OALocation, OpenAccessStatus
from paperbridge.models.openalex import (
    OpenAlexFilter,
    OpenAlexLocation,
    OpenAlexSearchResponse,
    OpenAlexTopic,
    OpenAlexWork,
)
from paperbridge.models.pubmed import (
    ArticleId,
    Author,
    DateType,
    HistoryDate,
    PubMedPublication,
    PubMedSearchCriteria,
    PubMedSearchResponse,
    PubMedSummaryResponse,
    SimplifiedCitation,
    SortOrder,
)
from paperbridge.models.workflow_config import WorkflowConfig, WorkflowModelConfig, WorkflowOptimizationConfig

__all__ = [
    # article
    "ArticleAbstract",
    "ArticleKeywords",
    "ArticleMetadata",
    "ArticleRecord",
    "FullText",
    "KeywordScore",
    "KeywordScoreList",
    "iter_keywords",
    # arxiv
    "ArXivPreprint",
    "ArXivSearchResult",
    # base_search
    "BASEWork",
    "BASESearchResponse",
    # citation_workflow
    "SearchTier",
    "SupportType",
    "VerificationStatus",
    "CitationVerificationResult",
    "SearchResult",
    "WorkflowInput",
    "WorkflowOutput",
    "ContraryQuery",
    "VerificationAssessment",
    # crossref
    "CrossRefAuthor",
    "CrossRefWork",
    # document
    "DocumentMetadata",
    "Table",
    "DocumentSection",
    "ParsedDocument",
    "DocumentReference",
    "SupplementalFile",
    "ContentAssessment",
    # doi
    "DOIHandleValue",
    "DOIHandleResponse",
    "DOIResolution",
    "DownloadLink",
    # download
    "DownloadAttempt",
    "DownloadResult",
    # europepmc
    "EuropePMCArticle",
    # extraction
    "ArticleExtractionResult",
    "CitationReference",
    "ExtractionAttempt",
    # open_access
    "OALocation",
    "OpenAccessStatus",
    # openalex
    "OpenAlexTopic",
    "OpenAlexLocation",
    "OpenAlexWork",
    "OpenAlexSearchResponse",
    "OpenAlexFilter",
    # pubmed
    "DateType",
    "SortOrder",
    "PubMedSearchCriteria",
    "SimplifiedCitation",
    "ArticleId",
    "Author",
    "HistoryDate",
    "PubMedPublication",
    "PubMedSearchResponse",
    "PubMedSummaryResponse",
    # workflow_config
    "WorkflowModelConfig",
    "WorkflowOptimizationConfig",
    "WorkflowConfig",
]
