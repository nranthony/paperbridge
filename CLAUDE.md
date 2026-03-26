# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

`paperbridge` is a standalone Python library for literature scouting — unified publication search, metadata retrieval, citation aggregation, and document downloading across multiple academic APIs.

Consolidates publication-related code from `mygentic` (my-agentic-tools) and `wearable_publications` into a single, dependency-light package.

## Development Commands

```bash
# Install via uv (preferred)
uv sync --group dev                  # test + lint tools
uv sync --group notebook             # ipykernel + ipywidgets
uv sync --group all-dev              # all dev groups combined

# Install via pip (alternative)
pip install -e ".[all]"              # core + optional PDF/bibtex deps

# Tests
pytest tests/
pytest tests/test_foo.py::test_bar   # single test

# Lint / type check
ruff check src/
mypy src/
```

## Architecture

Two client hierarchies exist side-by-side:

1. **`BaseAPIClient` subclasses** (`clients/_base.py`) — DOI-oriented clients that implement any subset of `fetch_keywords`, `fetch_abstract`, `fetch_metadata`, `fetch_full_text`. Currently: `CrossRefClient`, `EuropePMCClient`, `OpenAlexClient`, `PubMedClient`.

2. **Standalone search clients** — not DOI-driven; operate independently. Currently: `ArXivFamilyClient`, `BASESearchClient`, `DOIResolverClient`, `UnpaywallClient`, `PublicationDownloaderClient`, `DocumentParserClient`, `ZoteroClient`.

`CitationAggregator` (`aggregator.py`) owns a list of `BaseAPIClient` instances and fans out DOI lookups across all of them, merging results into an `ArticleRecord`.

**Configuration** (`_config.py`): `PaperBridgeSettings` loads from env vars or `.env`. Relevant vars: `NCBI_API_KEY`, `MY_EMAIL` / `UNPAYWALL_EMAIL`, `REQUEST_TIMEOUT`, `MAX_RETRIES`, `ZOTERO_API_KEY`, `ZOTERO_LIBRARY_ID`, `ZOTERO_LIBRARY_TYPE`. No global singleton — instantiate per client.

**Optional dependency groups** (guard all imports with `try/except`):
- `[docs]` — `pdfplumber`, `pymupdf`, `pymupdf4llm`, `trafilatura`
- `[bibtex]` — `bibtexparser`
- `[zotero]` — `pyzotero`

## Key Conventions

- **Logging**: `from paperbridge._logging import get_logger; logger = get_logger(__name__)` — never call `logger.remove()` globally
- **Models separate from clients**: All Pydantic models live in `models/`, never inline in client files
- **Clients are context managers**: Use `with CrossRefClient() as client:` or call `.close()` explicitly
- **`capabilities` property**: `BaseAPIClient.capabilities` introspects which fetch methods a subclass actually overrides — use this rather than `hasattr` checks
