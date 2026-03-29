# Paperbridge — Agent API Reference

Compact reference for AI agents writing code that uses `paperbridge`.
Read this alongside `CLAUDE.md` (architecture) and `README.md` (install/config).

---

## Decision guide — which client for which task?

| Task | Use |
|------|-----|
| Keyword search for papers | `ArXivFamilyClient.search`, `BASESearchClient.search`, `OpenAlexClient.search_works`, `CrossRefClient.search_works` |
| Search PubMed by term | `PubMedClient.search_and_fetch` |
| Everything about one DOI | `CitationAggregator.fetch_article(doi)` — fans out across all DOI clients |
| Just metadata for a DOI | `CrossRefClient.fetch_metadata` or `EuropePMCClient.fetch_metadata` |
| MeSH terms for a DOI | `PubMedClient.fetch_keywords` (preferred) or `EuropePMCClient.fetch_keywords` |
| Abstract for a DOI | `EuropePMCClient.fetch_abstract` or `PubMedClient.fetch_abstract` |
| Full-text XML (open access) | `EuropePMCClient.fetch_full_text` or `PubMedClient.fetch_full_text_xml` |
| Citation graph (cites/cited-by) | `CitationAggregator.fetch_citation_graph(doi)` |
| Is a paper open access? | `UnpaywallClient.check_oa_status(doi)` |
| Best PDF URL | `UnpaywallClient.get_best_pdf_url(doi)` |
| Download full text to disk | `CitationAggregator.download_article(doi, output_dir)` |
| Parse a local PDF or XML | `DocumentParserClient.parse(path)` |
| Look up DOI from title | `CrossRefClient.get_doi_from_title(title, author, year)` |
| Read/write Zotero library | `ZoteroClient` |
| Export Zotero items to BibTeX | `item.to_bibtex()` on any `ZoteroItem` |
| Import a .bib file into Zotero | `ZoteroClient.upload_bib(path_or_str)` |

---

## Imports

```python
# Fan-out aggregator (most common entry point)
from paperbridge.aggregator import CitationAggregator

# Individual clients
from paperbridge.clients import (
    ArXivFamilyClient,
    BASESearchClient,
    CrossRefClient,
    DocumentParserClient,
    DOIResolverClient,
    EuropePMCClient,
    OpenAlexClient,
    PubMedClient,
    PublicationDownloaderClient,
    UnpaywallClient,
    ZoteroClient,
)

# Models (return types)
from paperbridge.models.article import ArticleRecord, ArticleMetadata, ArticleKeywords, ArticleAbstract
from paperbridge.models.zotero import ZoteroItem, ZoteroItemData, ZoteroTag
```

---

## CitationAggregator — fan-out across all DOI clients

```python
from paperbridge.aggregator import CitationAggregator

with CitationAggregator() as agg:
    record: ArticleRecord = agg.fetch_article("10.1038/s41586-020-2649-2")
    graph  = agg.fetch_citation_graph("10.1038/s41586-020-2649-2", cited_by_limit=50)
    result = agg.download_article("10.1038/s41586-020-2649-2", output_dir="./papers")
```

`ArticleRecord` fields: `.doi`, `.metadata` (list), `.abstracts` (list), `.keywords` (list),
`.full_texts` (list), `.merged_metadata` (best-field merge), `.combined_keywords` (deduped list),
`.to_bibtex()`.

Requires: `MY_EMAIL` or `UNPAYWALL_EMAIL` env var for downloader.

---

## BaseAPIClient subclasses (DOI-oriented)

All four share the same interface and are context managers.
Use `client.capabilities` to check which methods are implemented.

### CrossRefClient

```python
from paperbridge.clients import CrossRefClient

with CrossRefClient() as cr:
    meta  = cr.fetch_metadata("10.1038/s41586-020-2649-2")   # → ArticleMetadata | None
    kw    = cr.fetch_keywords("10.1038/s41586-020-2649-2")   # → ArticleKeywords | None (subjects only)
    ab    = cr.fetch_abstract("10.1038/s41586-020-2649-2")   # → ArticleAbstract | None
    works = cr.search_works("transformer attention", rows=10) # → list[CrossRefWork]
    works = cr.search_by_title_author("Attention is all you need", author="Vaswani", year=2017)
    doi   = cr.get_doi_from_title("Attention is all you need", author="Vaswani") # → str | None
    work  = cr.get_work_by_doi("10.1038/s41586-020-2649-2")  # → CrossRefWork | None
```

### EuropePMCClient

```python
from paperbridge.clients import EuropePMCClient

with EuropePMCClient() as epmc:
    meta  = epmc.fetch_metadata("10.1016/j.cell.2021.01.018")  # → ArticleMetadata | None (includes PMID, citation_count)
    kw    = epmc.fetch_keywords("10.1016/j.cell.2021.01.018")  # → ArticleKeywords | None (MeSH + author_keywords)
    ab    = epmc.fetch_abstract("10.1016/j.cell.2021.01.018")  # → ArticleAbstract | None
    ft    = epmc.fetch_full_text("10.1016/j.cell.2021.01.018") # → FullText | None (open-access PMC only)
```

### OpenAlexClient

```python
from paperbridge.clients import OpenAlexClient

with OpenAlexClient() as oa:
    meta  = oa.fetch_metadata("10.1038/s41586-020-2649-2")     # → ArticleMetadata | None
    kw    = oa.fetch_keywords("10.1038/s41586-020-2649-2")     # → ArticleKeywords | None (topics/keywords)
    ab    = oa.fetch_abstract("10.1038/s41586-020-2649-2")     # → ArticleAbstract | None
    works = oa.search_works("CRISPR gene editing", per_page=25) # → list[OpenAlexWork]
    work  = oa.get_work_by_doi("10.1038/s41586-020-2649-2")    # → OpenAlexWork | None
    cited = oa.get_citations(work_id, per_page=25)             # → list[OpenAlexWork] (papers citing this)
    refs  = oa.get_references(work_id, per_page=25)            # → list[OpenAlexWork] (papers this cites)
    batch = oa.batch_get_works(["W123", "W456"])               # → list[OpenAlexWork]
```

### PubMedClient

```python
from paperbridge.clients import PubMedClient

with PubMedClient() as pm:
    pubs  = pm.search_and_fetch("heart rate variability wearable", retmax=50)  # → list[PubMedPublication]
    kw    = pm.fetch_keywords("10.1016/j.cell.2021.01.018")   # → ArticleKeywords | None (MeSH + author_keywords)
    ab    = pm.fetch_abstract("10.1016/j.cell.2021.01.018")   # → ArticleAbstract | None
    meta  = pm.fetch_metadata("10.1016/j.cell.2021.01.018")   # → ArticleMetadata | None
    pmcid = pm.get_pmc_id("34750604")                         # → str | None
    xml   = pm.fetch_full_text_xml(pmcid)                     # → str | None (raw PMC XML)
    oa    = pm.check_open_access("34750604")                  # → dict with "in_pmc_oa" key
```

`PubMedPublication` fields: `.uid`, `.title`, `.authors`, `.source` (journal), `.pubdate`,
`.doi`, `.pmcid`, `.abstract`.

Env var: `NCBI_API_KEY` (optional — raises rate limit from 3 to 10 req/s).

---

## Standalone search clients

### ArXivFamilyClient — searches arXiv/bioRxiv/medRxiv

```python
from paperbridge.clients import ArXivFamilyClient

with ArXivFamilyClient() as arxiv:
    result = arxiv.search("wearable ECG deep learning", max_results=20)  # → ArXivSearchResult
    paper  = arxiv.get_by_doi("10.48550/arXiv.2301.00001")               # → ArXivPreprint | None
    url    = arxiv.get_pdf_url("10.48550/arXiv.2301.00001")              # → str | None
    ok     = arxiv.check_availability("10.48550/arXiv.2301.00001")       # → bool
```

`ArXivSearchResult` fields: `.papers` (list[ArXivPreprint]), `.total_results`, `.start`.
`ArXivPreprint` fields: `.title`, `.authors`, `.abstract`, `.doi`, `.published`, `.pdf_url`.

### BASESearchClient — searches 300M+ open-access records

```python
from paperbridge.clients import BASESearchClient

with BASESearchClient() as base:
    works = base.search("physiological stress wearable sensor", max_results=25)   # → list[BASEWork]
    works = base.search_articles("RSA emotion regulation", max_results=25)
    works = base.search_theses("heart rate variability", max_results=10)
```

`BASEWork` fields: `.title`, `.authors`, `.year`, `.doi`, `.url`, `.description`, `.doc_type`.

### DOIResolverClient — validates DOIs via Handle.net

```python
from paperbridge.clients import DOIResolverClient

with DOIResolverClient() as resolver:
    result = resolver.resolve("10.1038/s41586-020-2649-2")   # → DOIResolution | None
    exists = resolver.check_doi_exists("10.1038/s41586-020-2649-2")  # → bool
```

### UnpaywallClient — open-access availability

```python
import os
from paperbridge.clients import UnpaywallClient

with UnpaywallClient(email=os.environ["MY_EMAIL"]) as oa:
    status  = oa.check_oa_status("10.1038/s41586-020-2649-2")  # → OpenAccessStatus
    pdf_url = oa.get_best_pdf_url("10.1038/s41586-020-2649-2") # → str | None
```

`OpenAccessStatus` fields: `.is_oa`, `.oa_status`, `.best_oa_location`, `.locations`.

### PublicationDownloaderClient — download full text to disk

```python
from paperbridge.clients import PublicationDownloaderClient

with PublicationDownloaderClient(email=os.environ["MY_EMAIL"]) as dl:
    result = dl.download_by_identifiers(
        doi="10.1038/s41586-020-2649-2",
        output_dir="./papers",
        formats=["pdf", "xml"],   # optional; tries all if omitted
    )
    # result: DownloadResult — .success, .file_path, .format, .source, .error
```

Download priority: PMC XML → arXiv PDF → Unpaywall PDF → direct URL.

### DocumentParserClient — parse PDFs, XML, HTML

Requires `[docs]` extras: `pip install paperbridge[docs]`

```python
from paperbridge.clients import DocumentParserClient

with DocumentParserClient() as parser:
    doc   = parser.parse("paper.pdf")              # → ParsedDocument (auto-detect)
    doc   = parser.parse_pdf("paper.pdf")
    doc   = parser.parse_xml(xml_string, schema="pmc")
    doc   = parser.parse_html(html_string)
    score = parser.assess_completeness(doc)        # → ContentAssessment
    links = parser.find_download_links(html, base_url)  # → list[DownloadLink]
```

`ParsedDocument` fields: `.title`, `.abstract`, `.sections` (list), `.tables` (list),
`.references` (list), `.metadata`.

---

## ZoteroClient — read/write Zotero library

Requires `[zotero]` extras: `pip install paperbridge[zotero]`
Env vars: `ZOTERO_API_KEY` + one of `ZOTERO_USER_ID` / `ZOTERO_GROUP_ID`.

```python
from paperbridge.clients import ZoteroClient
from paperbridge.models.zotero import ZoteroItemData, ZoteroTag

with ZoteroClient(api_key=API_KEY, group_id=GROUP_ID) as zot:
    # Read
    items      = zot.get_all_items()                              # → list[ZoteroItem]
    items      = zot.get_all_items(item_type="journalArticle", tag="HRV")
    item       = zot.get_item("ITEMKEY")                          # → ZoteroItem
    item       = zot.find_item_by_doi("10.1038/s41586-020-2649-2") # → ZoteroItem | None
    result     = zot.search("heart rate", limit=25)               # → ZoteroSearchResult
    cols       = zot.get_collections()                            # → list[ZoteroCollection]
    col_items  = zot.get_items_in_collection(col.key, limit=100)  # → ZoteroSearchResult
    bib        = item.to_bibtex()                                 # → str (full BibTeX entry)

    # Write
    zot.add_tags_to_item("ITEMKEY", ["reviewed", "HRV"])         # merges, does not replace
    zot.update_item("ITEMKEY", ZoteroItemData(extra="my note"))  # partial update — only sets extra
    zot.add_item_to_collection("ITEMKEY", col.key)

    # Import a .bib file or BibTeX string (mirrors Zotero UI Import)
    result = zot.upload_bib(
        Path("library.bib"),              # or a raw BibTeX string
        collection_key="EXISTINGKEY",     # add to existing collection  — OR —
        new_collection_name="Wave 2",     # create new collection (mutually exclusive)
        parent_collection_key="PARENT",   # nest new collection under parent (optional)
        skip_existing=True,               # skip entries whose DOI is already in library
        tags=["batch-import"],            # extra tags on every imported item
    )
    # BibTeX keywords field is automatically split and added as Zotero tags

    # Sync ArticleRecords from CitationAggregator into Zotero
    sync_result = zot.sync_article_records(
        records,
        collection_key=col.key,
        tags=["imported"],
        skip_existing=True,
    )
    # sync_result: ZoteroSyncResult — .created_keys, .failed, .total_attempted
```

`ZoteroItem.data` fields: `.title`, `.doi`, `.issn`, `.volume`, `.issue`, `.pages`,
`.date`, `.abstract_note`, `.publication_title`, `.creators`, `.tags`, `.url`, `.extra`.

**Partial updates**: `ZoteroItemData(extra="note")` only updates `extra` — unset fields
are not touched. Pass `tags=[ZoteroTag(tag="x")]` only when you intend to replace all tags.

---

## Key return-type fields

### ArticleMetadata
`.source`, `.title`, `.authors` (list[str]), `.year` (int), `.journal`, `.doi`, `.pmid`, `.citation_count`

### ArticleKeywords
`.source`, `.mesh_terms` (list[str]), `.author_keywords` (list[str]), `.subjects` (list[str]),
`.all_keywords` (property — combined deduped list)

### ArticleAbstract
`.source`, `.text`

### ArticleRecord
`.doi`, `.merged_metadata` (best-field ArticleMetadata), `.combined_keywords` (deduped list),
`.metadata` (list[ArticleMetadata]), `.abstracts` (list[ArticleAbstract]),
`.keywords` (list[ArticleKeywords]), `.full_texts` (list[FullText]),
`.to_bibtex()` → str

---

## Environment variables

| Variable | Required by | Notes |
|----------|-------------|-------|
| `NCBI_API_KEY` | PubMedClient | Raises rate limit 3 → 10 req/s |
| `MY_EMAIL` or `UNPAYWALL_EMAIL` | UnpaywallClient, PublicationDownloaderClient, CitationAggregator | Required for Unpaywall |
| `ZOTERO_API_KEY` | ZoteroClient | Zotero Web API auth |
| `ZOTERO_USER_ID` | ZoteroClient | Personal library (use one of user/group) |
| `ZOTERO_GROUP_ID` | ZoteroClient | Group library — takes precedence over user_id |
| `REQUEST_TIMEOUT` | all clients | HTTP timeout in seconds (default: 30) |
| `MAX_RETRIES` | all clients | Retry attempts on failure (default: 3) |

Load from `.env` via `python-dotenv` or set in shell. All vars are also accepted as
constructor parameters on each client.

---

## Common patterns

```python
# 1. Fan-out DOI lookup (recommended starting point)
with CitationAggregator() as agg:
    record = agg.fetch_article(doi)
    print(record.merged_metadata.title)
    print(record.combined_keywords)
    print(record.to_bibtex())

# 2. Search → DOI → full record
with CrossRefClient() as cr, CitationAggregator() as agg:
    doi = cr.get_doi_from_title("Attention is all you need", author="Vaswani", year=2017)
    if doi:
        record = agg.fetch_article(doi)

# 3. PubMed search → MeSH terms
with PubMedClient() as pm:
    pubs = pm.search_and_fetch("RSA emotion dysregulation children", retmax=50)
    for pub in pubs:
        kw = pm.fetch_keywords(pub.doi)
        if kw:
            print(kw.mesh_terms)

# 4. Export Zotero collection to .bib
with ZoteroClient(api_key=KEY, group_id=GID) as zot:
    cols = zot.get_collections()
    col  = next(c for c in cols if c.name == "MyCollection")
    items = zot.get_items_in_collection(col.key, limit=100)
    bibs  = [i.to_bibtex() for i in items.items if i.data.item_type not in ("attachment", "note")]
    Path("library.bib").write_text("\n\n".join(bibs))

# 5. Download paper and parse it
with CitationAggregator() as agg, DocumentParserClient() as parser:
    result = agg.download_article(doi, output_dir="./papers")
    if result.success:
        doc = parser.parse(result.file_path)
        print(doc.abstract)
```
