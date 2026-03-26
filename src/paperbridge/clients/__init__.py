"""Client classes for academic publication APIs."""

from paperbridge.clients.arxiv import ArXivFamilyClient
from paperbridge.clients.base_search import BASESearchClient
from paperbridge.clients.crossref import CrossRefClient
from paperbridge.clients.document_parser import DocumentParserClient
from paperbridge.clients.doi import DOIResolverClient
from paperbridge.clients.downloader import PublicationDownloaderClient
from paperbridge.clients.europepmc import EuropePMCClient
from paperbridge.clients.openalex import OpenAlexClient
from paperbridge.clients.pubmed import PubMedClient
from paperbridge.clients.unpaywall import UnpaywallClient
from paperbridge.clients.zotero import ZoteroClient

__all__ = [
    "ArXivFamilyClient",
    "BASESearchClient",
    "CrossRefClient",
    "DocumentParserClient",
    "DOIResolverClient",
    "EuropePMCClient",
    "OpenAlexClient",
    "PubMedClient",
    "PublicationDownloaderClient",
    "UnpaywallClient",
    "ZoteroClient",
]
