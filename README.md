# paperbridge

Unified Python library for literature scouting — publication search, metadata retrieval, citation aggregation, and document downloading across multiple academic APIs.

## Install

```bash
# core (search + metadata)
pip install paperbridge

# with PDF parsing support
pip install "paperbridge[docs]"

# with BibTeX export
pip install "paperbridge[bibtex]"

# with Zotero library sync
pip install "paperbridge[zotero]"

# everything
pip install "paperbridge[all]"
```

Requires Python 3.12+.

## Supported APIs

| Client | Capabilities |
|---|---|
| `PubMedClient` | Search, fetch metadata / abstract / MeSH keywords via DOI |
| `CrossRefClient` | Search, DOI lookup, metadata / abstract / subjects |
| `OpenAlexClient` | DOI lookup, topics / metadata |
| `EuropePMCClient` | DOI lookup, abstract / metadata / full text |
| `ArXivFamilyClient` | arXiv search and preprint retrieval |
| `BASESearchClient` | Bielefeld Academic Search Engine |
| `UnpaywallClient` | Open-access PDF location by DOI |
| `DOIResolverClient` | DOI → URL resolution |
| `PublicationDownloaderClient` | PDF download orchestration |
| `DocumentParserClient` | PDF → structured text extraction |
| `ZoteroClient` | Read/write Zotero user and group libraries |

## Usage

### Aggregate all data for a DOI

```python
from paperbridge import CitationAggregator

with CitationAggregator() as agg:
    record = agg.fetch_article("10.1038/s41586-021-03819-2")
    print(record.combined_keywords)
    print(record.metadata)       # list[ArticleMetadata], one per source
    print(record.abstracts)      # list[ArticleAbstract]
```

### Use a single client

```python
from paperbridge.clients import CrossRefClient, PubMedClient

with CrossRefClient() as cr:
    meta = cr.fetch_metadata("10.1038/s41586-021-03819-2")
    print(meta.title, meta.year, meta.citation_count)

with PubMedClient(api_key="...") as pm:
    results = pm.search_and_fetch("CRISPR base editing", retmax=20)
```

### Zotero library sync

```python
from paperbridge.clients import ZoteroClient

# Read from a group library
with ZoteroClient(api_key="...", library_id="12345", library_type="group") as zot:
    results = zot.get_items(limit=10)
    for item in results.items:
        print(item.data.title, item.data.doi)

# Sync paperbridge results into Zotero
with ZoteroClient(api_key="...", library_id="12345") as zot:
    zot.sync_article_records(records, collection_key="ABC123", tags=["imported"])
```

### Keyword aggregation

```python
with CitationAggregator() as agg:
    kw = agg.fetch_all_keywords("10.1038/s41586-021-03819-2")
    print(kw["combined"])   # deduplicated across all sources
    print(kw["pubmed"])     # MeSH + author keywords
    print(kw["crossref"])   # subject classifications
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `NCBI_API_KEY` | PubMed rate limit: 10 req/s (vs 3 without key) |
| `MY_EMAIL` / `UNPAYWALL_EMAIL` | Polite pool for CrossRef / Unpaywall |
| `REQUEST_TIMEOUT` | Default HTTP timeout in seconds (default: 30) |
| `MAX_RETRIES` | HTTP retry attempts (default: 3) |
| `ZOTERO_API_KEY` | Zotero API key ([create here](https://www.zotero.org/settings/keys)) |
| `ZOTERO_LIBRARY_ID` | Numeric user or group library ID |
| `ZOTERO_LIBRARY_TYPE` | `user` (default) or `group` |

## Development

```bash
uv sync --group dev                  # test + lint tools
uv sync --group notebook             # ipykernel + ipywidgets
uv sync --group dev --group notebook # both groups
uv sync --group all-dev              # shorthand for all dev groups
pytest tests/
ruff check src/
mypy src/
```
