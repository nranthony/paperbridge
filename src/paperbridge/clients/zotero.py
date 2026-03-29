"""Zotero Web API v3 client.

Wraps `pyzotero <https://github.com/urschrei/pyzotero>`_ to provide
a typed, Pydantic-model interface consistent with other paperbridge clients.

Requires the ``[zotero]`` optional dependency group::

    pip install paperbridge[zotero]
"""

import re
from pathlib import Path
from typing import Any, Optional

from paperbridge._logging import get_logger
from paperbridge.models.article import ArticleMetadata, ArticleRecord
from paperbridge.models.zotero import (
    ZoteroCollection,
    ZoteroCreator,
    ZoteroItem,
    ZoteroItemData,
    ZoteroSearchResult,
    ZoteroSyncResult,
    ZoteroTag,
)

try:
    from pyzotero import zotero
except ImportError:
    zotero = None  # type: ignore[assignment]

logger = get_logger(__name__)


class ZoteroClient:
    """Client for the Zotero Web API v3.

    Supports reading from and writing to user or group libraries.
    Provide either ``user_id`` for a personal library or ``group_id``
    for a group library. If both are given, ``group_id`` takes precedence.

    Parameters
    ----------
    api_key : str
        Zotero API key (create at https://www.zotero.org/settings/keys).
    user_id : str, optional
        Numeric user ID (shown at https://www.zotero.org/settings/keys).
        Connects to the personal library.
    group_id : str, optional
        Numeric group ID (from the group URL on zotero.org).
        Connects to the group library. Takes precedence over ``user_id``.

    Examples
    --------
    >>> with ZoteroClient(api_key="...", group_id="12345") as zot:
    ...     items = zot.get_items(limit=5)

    >>> with ZoteroClient(api_key="...", user_id="67890") as zot:
    ...     items = zot.get_items(limit=5)
    """

    def __init__(
        self,
        api_key: str,
        user_id: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> None:
        if zotero is None:
            raise ImportError(
                "pyzotero is required for ZoteroClient. "
                "Install it with: pip install paperbridge[zotero]"
            )
        if not api_key:
            raise ValueError("Zotero API key is required")
        if not user_id and not group_id:
            raise ValueError("Either user_id or group_id must be provided")

        # group_id takes precedence if both are provided
        if group_id:
            self.library_id = group_id
            self.library_type = "group"
        else:
            self.library_id = user_id  # type: ignore[assignment]
            self.library_type = "user"

        self.api_key = api_key
        self._zot = zotero.Zotero(self.library_id, self.library_type, api_key)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "ZoteroClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        """No persistent resources to release, but keeps API consistent."""

    def __repr__(self) -> str:
        if self.library_type == "group":
            return f"ZoteroClient(group_id={self.library_id!r})"
        return f"ZoteroClient(user_id={self.library_id!r})"

    # ------------------------------------------------------------------
    # READ: Items
    # ------------------------------------------------------------------

    def get_items(
        self,
        limit: int = 25,
        start: int = 0,
        sort: str = "dateModified",
        direction: str = "desc",
        item_type: Optional[str] = None,
        tag: Optional[str | list[str]] = None,
        q: Optional[str] = None,
        since: Optional[int] = None,
    ) -> ZoteroSearchResult:
        """Fetch items from the library with optional filters.

        Parameters
        ----------
        limit : int
            Max items to return (Zotero caps at 100).
        start : int
            Pagination offset.
        sort : str
            Field to sort by (``dateModified``, ``dateAdded``, ``title``, etc.).
        direction : str
            ``"asc"`` or ``"desc"``.
        item_type : str, optional
            Filter by item type (e.g. ``"journalArticle"``).
        tag : str or list[str], optional
            Filter by tag(s).
        q : str, optional
            Quick-search query string.
        since : int, optional
            Return only items modified since this library version.
        """
        kwargs: dict[str, Any] = {
            "limit": limit,
            "start": start,
            "sort": sort,
            "direction": direction,
        }
        if item_type:
            kwargs["itemType"] = item_type
        if tag:
            kwargs["tag"] = tag if isinstance(tag, str) else " || ".join(tag)
        if q:
            kwargs["q"] = q
        if since is not None:
            kwargs["since"] = since

        raw_items = self._zot.items(**kwargs)
        items = [self._dict_to_item(r) for r in raw_items]
        headers = getattr(self._zot.request, "headers", {})
        total = int(headers.get("Total-Results", len(items)))

        return ZoteroSearchResult(
            items=items,
            total_results=total,
            start=start,
            limit=limit,
            query=q,
        )

    def get_item(self, item_key: str) -> ZoteroItem:
        """Fetch a single item by its key."""
        raw = self._zot.item(item_key)
        return self._dict_to_item(raw)

    def get_all_items(
        self,
        item_type: Optional[str] = None,
        tag: Optional[str | list[str]] = None,
        q: Optional[str] = None,
    ) -> list[ZoteroItem]:
        """Auto-paginate through all items matching the filters.

        Returns every matching item in the library regardless of size.
        Use with caution on large libraries.

        Parameters
        ----------
        item_type : str, optional
            Filter by item type (e.g. ``"journalArticle"``).
        tag : str or list[str], optional
            Filter by tag(s).
        q : str, optional
            Quick-search query string.
        """
        kwargs: dict[str, Any] = {}
        if item_type:
            kwargs["itemType"] = item_type
        if tag:
            kwargs["tag"] = tag if isinstance(tag, str) else " || ".join(tag)
        if q:
            kwargs["q"] = q

        raw_items = self._zot.everything(self._zot.items(**kwargs))
        return [self._dict_to_item(r) for r in raw_items]

    def search(self, query: str, limit: int = 25, start: int = 0) -> ZoteroSearchResult:
        """Quick-search across the library (titles, creators, years, etc.)."""
        return self.get_items(q=query, limit=limit, start=start)

    def get_item_bibtex(self, item_key: str) -> str:
        """Fetch a single item as a BibTeX string."""
        return self._zot.item(item_key, format="bibtex")

    def get_items_in_collection(
        self,
        collection_key: str,
        limit: int = 25,
        start: int = 0,
    ) -> ZoteroSearchResult:
        """Fetch items belonging to a specific collection."""
        raw_items = self._zot.collection_items(collection_key, limit=limit, start=start)
        items = [self._dict_to_item(r) for r in raw_items]
        headers = getattr(self._zot.request, "headers", {})
        total = int(headers.get("Total-Results", len(items)))
        return ZoteroSearchResult(
            items=items,
            total_results=total,
            start=start,
            limit=limit,
        )

    def find_item_by_doi(self, doi: str) -> Optional[ZoteroItem]:
        """Search library for an item with the given DOI.

        Uses Zotero quick-search then filters client-side for an exact match.
        """
        result = self.get_items(q=doi, limit=10)
        for item in result.items:
            if item.data.doi and item.data.doi.lower() == doi.lower():
                return item
        return None

    # ------------------------------------------------------------------
    # READ: Collections
    # ------------------------------------------------------------------

    def get_collections(self, limit: int = 100, start: int = 0) -> list[ZoteroCollection]:
        """Fetch top-level collections."""
        raw = self._zot.collections(limit=limit, start=start)
        return [self._dict_to_collection(c) for c in raw]

    def get_collection(self, collection_key: str) -> ZoteroCollection:
        """Fetch a single collection by key."""
        raw = self._zot.collection(collection_key)
        return self._dict_to_collection(raw)

    def get_subcollections(self, collection_key: str) -> list[ZoteroCollection]:
        """Fetch child collections of a given collection."""
        raw = self._zot.collections_sub(collection_key)
        return [self._dict_to_collection(c) for c in raw]

    # ------------------------------------------------------------------
    # READ: Tags
    # ------------------------------------------------------------------

    def get_tags(self, limit: int = 100, start: int = 0) -> list[str]:
        """Fetch all tags in the library."""
        return list(self._zot.tags(limit=limit, start=start))

    def get_item_tags(self, item_key: str) -> list[str]:
        """Get tags for a specific item."""
        item = self.get_item(item_key)
        return [t.tag for t in item.data.tags]

    # ------------------------------------------------------------------
    # WRITE: Items
    # ------------------------------------------------------------------

    def create_item(self, item_data: ZoteroItemData) -> ZoteroItem:
        """Create a single item in the library.

        Returns the created item with its server-assigned key.
        """
        template = self._zot.item_template(item_data.item_type)
        payload = self._merge_item_data_into_template(template, item_data)
        resp = self._zot.create_items([payload])
        created = resp.get("successful", {})
        if "0" in created:
            return self._dict_to_item(created["0"])
        failed = resp.get("failed", {})
        raise RuntimeError(f"Failed to create Zotero item: {failed}")

    def create_items(self, items: list[ZoteroItemData]) -> ZoteroSyncResult:
        """Batch-create multiple items in the library.

        Automatically chunks into batches of 50 per Zotero API limits.
        Returns a ``ZoteroSyncResult`` with created keys and any failures.
        """
        result = ZoteroSyncResult(total_attempted=len(items))

        for chunk_start in range(0, len(items), 50):
            chunk = items[chunk_start: chunk_start + 50]
            payloads = []
            for item_data in chunk:
                template = self._zot.item_template(item_data.item_type)
                payloads.append(self._merge_item_data_into_template(template, item_data))

            resp = self._zot.create_items(payloads)
            for _idx, item_dict in resp.get("successful", {}).items():
                result.created_keys.append(item_dict["key"])
            for idx, err in resp.get("failed", {}).items():
                result.failed.append({"index": int(idx) + chunk_start, "error": err})

        return result

    def update_item(self, item_key: str, item_data: ZoteroItemData) -> ZoteroItem:
        """Update an existing item.

        Fetches the current version from the server to ensure
        optimistic-locking headers are correct.
        """
        existing = self._zot.item(item_key)
        merged = self._merge_item_data_into_template(existing["data"], item_data)
        existing["data"] = merged
        self._zot.update_item(existing)
        return self.get_item(item_key)

    def delete_item(self, item_key: str) -> bool:
        """Delete an item from the library by its key."""
        item = self._zot.item(item_key)
        self._zot.delete_item(item)
        return True

    def add_tags_to_item(self, item_key: str, tags: list[str]) -> ZoteroItem:
        """Append tags to an existing item (merge, don't replace)."""
        raw = self._zot.item(item_key)
        existing_tags = {t["tag"] for t in raw["data"].get("tags", [])}
        for tag in tags:
            if tag not in existing_tags:
                raw["data"]["tags"].append({"tag": tag, "type": 0})
        self._zot.update_item(raw)
        return self.get_item(item_key)

    def add_item_to_collection(self, item_key: str, collection_key: str) -> ZoteroItem:
        """Add an existing item to a collection."""
        raw = self._zot.item(item_key)
        collections = raw["data"].get("collections", [])
        if collection_key not in collections:
            collections.append(collection_key)
            raw["data"]["collections"] = collections
            self._zot.update_item(raw)
        return self.get_item(item_key)

    # ------------------------------------------------------------------
    # WRITE: Collections
    # ------------------------------------------------------------------

    def create_collection(
        self,
        name: str,
        parent_key: Optional[str] = None,
    ) -> ZoteroCollection:
        """Create a new collection, optionally nested under ``parent_key``."""
        payload: dict[str, Any] = {"name": name}
        if parent_key:
            payload["parentCollection"] = parent_key
        resp = self._zot.create_collections([payload])
        created = resp.get("successful", {})
        if "0" in created:
            return self._dict_to_collection(created["0"])
        failed = resp.get("failed", {})
        raise RuntimeError(f"Failed to create collection: {failed}")

    def delete_collection(self, collection_key: str) -> bool:
        """Delete a collection by key. Items in the collection are not deleted."""
        col = self._zot.collection(collection_key)
        self._zot.delete_collection(col)
        return True

    # ------------------------------------------------------------------
    # CONVERSION: Zotero <-> paperbridge models
    # ------------------------------------------------------------------

    def item_to_article_metadata(self, item: ZoteroItem) -> ArticleMetadata:
        """Convert a ZoteroItem to a paperbridge ``ArticleMetadata``.

        Extracts authors (creator_type ``"author"`` only), parses the year
        from the date string, and pulls PMID from the Extra field if present.
        """
        data = item.data
        authors = [c.display_name for c in data.creators if c.creator_type == "author"]

        year = None
        if data.date:
            match = re.search(r"\b(19|20)\d{2}\b", data.date)
            if match:
                year = int(match.group())

        pmid = self._extract_pmid_from_extra(data.extra)

        return ArticleMetadata(
            source="zotero",
            title=data.title,
            authors=authors,
            year=year,
            journal=data.publication_title,
            doi=data.doi,
            pmid=pmid,
        )

    def article_metadata_to_item_data(
        self,
        metadata: ArticleMetadata,
        collection_keys: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> ZoteroItemData:
        """Convert a paperbridge ``ArticleMetadata`` to ``ZoteroItemData``.

        Author name strings are split into first/last name. PMID is stored
        in the Zotero Extra field. The resulting item type is ``journalArticle``.
        """
        creators = []
        for author in metadata.authors:
            parts = author.split()
            if len(parts) > 1:
                creators.append(
                    ZoteroCreator(creator_type="author", first_name=" ".join(parts[:-1]), last_name=parts[-1])
                )
            else:
                creators.append(ZoteroCreator(creator_type="author", last_name=author))

        ztags = [ZoteroTag(tag=t) for t in (tags or [])]

        extra_parts = []
        if metadata.pmid:
            extra_parts.append(f"PMID: {metadata.pmid}")

        return ZoteroItemData(
            item_type="journalArticle",
            title=metadata.title,
            creators=creators,
            date=str(metadata.year) if metadata.year else None,
            doi=metadata.doi,
            publication_title=metadata.journal,
            tags=ztags,
            collections=collection_keys or [],
            extra="\n".join(extra_parts) if extra_parts else None,
        )

    def article_record_to_item_data(
        self,
        record: ArticleRecord,
        collection_keys: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> ZoteroItemData:
        """Convert an ArticleRecord to ZoteroItemData.

        Uses ``merged_metadata`` for fields, adds abstract and keywords.
        """
        merged = record.merged_metadata
        if merged is None:
            merged = ArticleMetadata(source="paperbridge", doi=record.doi)

        all_tags = list(tags or [])
        all_tags.extend(record.combined_keywords)
        # deduplicate while preserving order
        seen: set[str] = set()
        unique_tags: list[str] = []
        for t in all_tags:
            if t not in seen:
                seen.add(t)
                unique_tags.append(t)

        item_data = self.article_metadata_to_item_data(
            merged,
            collection_keys=collection_keys,
            tags=unique_tags,
        )

        if record.abstracts:
            item_data.abstract_note = record.abstracts[0].text

        return item_data

    def sync_article_records(
        self,
        records: list[ArticleRecord],
        collection_key: Optional[str] = None,
        tags: Optional[list[str]] = None,
        skip_existing: bool = True,
    ) -> ZoteroSyncResult:
        """Batch-sync ArticleRecords into Zotero.

        Parameters
        ----------
        records : list[ArticleRecord]
            Records to sync.
        collection_key : str, optional
            Add created items to this collection.
        tags : list[str], optional
            Extra tags to apply to all items.
        skip_existing : bool
            If True, skip records whose DOI already exists in the library.
        """
        collection_keys = [collection_key] if collection_key else None
        items_to_create: list[ZoteroItemData] = []

        for record in records:
            if skip_existing and self.find_item_by_doi(record.doi):
                logger.info(f"Skipping existing DOI: {record.doi}")
                continue
            items_to_create.append(
                self.article_record_to_item_data(record, collection_keys=collection_keys, tags=tags)
            )

        if not items_to_create:
            logger.info("No new items to sync")
            return ZoteroSyncResult(total_attempted=len(records))

        return self.create_items(items_to_create)

    def upload_bib(
        self,
        bib: "str | Path",
        collection_key: Optional[str] = None,
        new_collection_name: Optional[str] = None,
        parent_collection_key: Optional[str] = None,
        skip_existing: bool = True,
        tags: Optional[list[str]] = None,
    ) -> ZoteroSyncResult:
        """Import a BibTeX file or string into the Zotero library.

        Mirrors the behaviour of Zotero's UI Import function.  Each BibTeX
        entry is converted to a ``ZoteroItemData`` and created via the API.
        BibTeX ``keywords`` fields are merged with any extra ``tags`` you
        supply and stored as Zotero tags on the item.

        Parameters
        ----------
        bib : str or Path
            BibTeX content as a string, or a ``Path`` to a ``.bib`` file.
        collection_key : str, optional
            Key of an existing collection to add all imported items to.
            Mutually exclusive with ``new_collection_name``.
        new_collection_name : str, optional
            Create a new collection with this name and add all items to it.
            Mutually exclusive with ``collection_key``.
        parent_collection_key : str, optional
            When creating a new collection, nest it under this parent key.
        skip_existing : bool
            If ``True`` (default), skip any entry whose DOI is already in
            the library.
        tags : list[str], optional
            Extra tags applied to every imported item.

        Returns
        -------
        ZoteroSyncResult
            ``.created_keys`` — Zotero keys of newly created items.
            ``.failed`` — entries that could not be created.
            ``.total_attempted`` — total entries parsed from the BibTeX.

        Examples
        --------
        >>> # Import into an existing collection
        >>> result = zot.upload_bib(Path("library.bib"), collection_key="ABC123")

        >>> # Import and create a new top-level collection
        >>> result = zot.upload_bib("@article{...}", new_collection_name="Imported 2026-03")

        >>> # Import into a nested sub-collection
        >>> result = zot.upload_bib(
        ...     Path("library.bib"),
        ...     new_collection_name="Wave 2",
        ...     parent_collection_key="PARENTKEY",
        ... )
        """
        try:
            import bibtexparser
        except ImportError:
            raise ImportError(
                "bibtexparser is required for upload_bib. "
                "Install it with: pip install paperbridge[bibtex]"
            )

        if collection_key and new_collection_name:
            raise ValueError("Provide collection_key or new_collection_name, not both.")

        # Read file if a path was given
        bib_str = Path(bib).read_text(encoding="utf-8") if isinstance(bib, Path) else bib

        db = bibtexparser.loads(bib_str)
        entries = db.entries
        logger.info(f"Parsed {len(entries)} entries from BibTeX")

        # Resolve target collection key
        target_collection_key: Optional[str] = collection_key
        if new_collection_name:
            col = self.create_collection(new_collection_name, parent_key=parent_collection_key)
            target_collection_key = col.key
            logger.info(f"Created collection '{new_collection_name}' (key={col.key})")

        collection_keys = [target_collection_key] if target_collection_key else None

        result = ZoteroSyncResult(total_attempted=len(entries))
        items_to_create: list[ZoteroItemData] = []

        for entry in entries:
            item_data = self._bibtex_entry_to_item_data(entry, collection_keys=collection_keys, extra_tags=tags or [])

            if skip_existing and item_data.doi:
                if self.find_item_by_doi(item_data.doi):
                    logger.info(f"Skipping existing DOI: {item_data.doi}")
                    continue

            items_to_create.append(item_data)

        if not items_to_create:
            logger.info("No new items to import")
            return result

        batch_result = self.create_items(items_to_create)
        result.created_keys = batch_result.created_keys
        result.failed = batch_result.failed
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # BibTeX ENTRYTYPE → Zotero itemType
    _BIBTEX_ITEM_TYPE_MAP: dict[str, str] = {
        "article": "journalArticle",
        "book": "book",
        "booklet": "book",
        "inbook": "bookSection",
        "incollection": "bookSection",
        "inproceedings": "conferencePaper",
        "conference": "conferencePaper",
        "phdthesis": "thesis",
        "mastersthesis": "thesis",
        "techreport": "report",
        "preprint": "preprint",
        "misc": "journalArticle",
        "unpublished": "journalArticle",
    }

    # BibTeX fields that map to ZoteroItemData model_extra (item-type-specific)
    _BIBTEX_EXTRA_FIELDS: list[tuple[str, str]] = [
        ("publisher", "publisher"),
        ("address", "place"),
        ("edition", "edition"),
        ("isbn", "ISBN"),
        ("language", "language"),
        ("booktitle", "bookTitle"),
        ("series", "seriesTitle"),
    ]

    def _bibtex_entry_to_item_data(
        self,
        entry: dict[str, Any],
        collection_keys: Optional[list[str]] = None,
        extra_tags: Optional[list[str]] = None,
    ) -> ZoteroItemData:
        """Convert a bibtexparser entry dict to ``ZoteroItemData``.

        Handles author parsing (``Last, First and ...`` format), BibTeX
        keyword splitting, and maps field names to Zotero's schema.
        Item-type-specific fields (publisher, address, etc.) are passed
        through via ``model_extra`` using Pydantic's ``extra="allow"``.
        """
        item_type = self._BIBTEX_ITEM_TYPE_MAP.get(
            entry.get("ENTRYTYPE", "article").lower(), "journalArticle"
        )

        # --- Creators ---
        creators: list[ZoteroCreator] = []
        for field, role in (("author", "author"), ("editor", "editor")):
            raw_names = entry.get(field, "")
            if not raw_names:
                continue
            for name in re.split(r"\s+and\s+", raw_names, flags=re.IGNORECASE):
                name = name.strip()
                if not name:
                    continue
                if "," in name:
                    last, _, first = name.partition(",")
                    creators.append(
                        ZoteroCreator(
                            creator_type=role,
                            last_name=last.strip(),
                            first_name=first.strip() or None,
                        )
                    )
                else:
                    parts = name.split()
                    creators.append(
                        ZoteroCreator(
                            creator_type=role,
                            last_name=parts[-1],
                            first_name=" ".join(parts[:-1]) or None,
                        )
                    )

        # --- Tags: BibTeX keywords + caller-supplied extras ---
        tag_set: list[str] = []
        seen: set[str] = set()
        raw_kw = entry.get("keywords", "")
        kw_list = [k.strip() for k in re.split(r"[,;]", raw_kw) if k.strip()]
        for t in kw_list + (extra_tags or []):
            if t not in seen:
                seen.add(t)
                tag_set.append(t)
        tags = [ZoteroTag(tag=t) for t in tag_set]

        # --- Date: prefer 'year', fall back to 'date' ---
        date = entry.get("year") or entry.get("date") or None

        # --- item-type-specific extras via model_extra ---
        extra_kwargs: dict[str, Any] = {}
        for bib_field, zotero_field in self._BIBTEX_EXTRA_FIELDS:
            val = entry.get(bib_field)
            if val:
                extra_kwargs[zotero_field] = val

        # --- note/annote → extra field ---
        note_parts = [p for p in (entry.get("note"), entry.get("annote")) if p]
        extra_str = "\n".join(note_parts) or None

        return ZoteroItemData(
            item_type=item_type,
            title=entry.get("title"),
            creators=creators,
            abstract_note=entry.get("abstract"),
            publication_title=entry.get("journal") or entry.get("journaltitle"),
            volume=entry.get("volume"),
            issue=entry.get("number") or entry.get("issue"),
            pages=entry.get("pages"),
            date=date,
            doi=entry.get("doi") or entry.get("DOI"),
            issn=entry.get("issn") or entry.get("ISSN"),
            url=entry.get("url"),
            tags=tags,
            collections=collection_keys or [],
            extra=extra_str,
            **extra_kwargs,
        )

    def _dict_to_item(self, raw: dict[str, Any]) -> ZoteroItem:
        """Convert a pyzotero item dict to a ZoteroItem model."""
        data_dict = raw.get("data", {})
        data = ZoteroItemData.model_validate(data_dict)
        return ZoteroItem(
            key=raw["key"],
            version=raw["version"],
            library=raw.get("library", {}),
            data=data,
            meta=raw.get("meta", {}),
            links=raw.get("links", {}),
        )

    def _dict_to_collection(self, raw: dict[str, Any]) -> ZoteroCollection:
        """Convert a pyzotero collection dict to a ZoteroCollection model."""
        data = raw.get("data", {})
        parent = data.get("parentCollection")
        # Zotero uses False (not None) when there's no parent collection
        if parent is False:
            parent = None
        return ZoteroCollection(
            key=raw.get("key", data.get("key", "")),
            version=raw.get("version", data.get("version", 0)),
            name=data.get("name", ""),
            parent_collection=parent,
            data=data,
        )

    def _merge_item_data_into_template(
        self,
        template: dict[str, Any],
        item_data: ZoteroItemData,
    ) -> dict[str, Any]:
        """Merge ZoteroItemData fields into a pyzotero item template/dict.

        Only overwrites template keys with fields explicitly set on item_data.
        List fields (tags, creators, collections) default to [] and would
        otherwise clobber existing values — exclude_unset=True prevents that.
        """
        dumped = item_data.model_dump(by_alias=True, exclude_unset=True)
        # Remove internal fields that shouldn't be sent to the API
        dumped.pop("key", None)
        dumped.pop("version", None)

        for key, value in dumped.items():
            if key == "creators":
                template["creators"] = [
                    c.model_dump(by_alias=True, exclude_none=True) for c in item_data.creators
                ]
            elif key == "tags":
                template["tags"] = [t.model_dump() for t in item_data.tags]
            else:
                template[key] = value

        return template

    @staticmethod
    def _extract_pmid_from_extra(extra: Optional[str]) -> Optional[str]:
        """Extract PMID from Zotero's 'Extra' field if present."""
        if not extra:
            return None
        match = re.search(r"PMID:\s*(\d+)", extra)
        return match.group(1) if match else None
