"""Tests for ZoteroClient using mocked pyzotero."""

import pytest
from unittest.mock import MagicMock, patch

from paperbridge.models.article import ArticleMetadata, ArticleRecord, ArticleAbstract, ArticleKeywords
from paperbridge.models.zotero import (
    ZoteroCreator,
    ZoteroItemData,
    ZoteroTag,
)


DOI = "10.1038/s41586-021-03819-2"

ZOTERO_ITEM_FIXTURE = {
    "key": "ABC12345",
    "version": 42,
    "library": {"type": "user", "id": 12345},
    "data": {
        "key": "ABC12345",
        "version": 42,
        "itemType": "journalArticle",
        "title": "Programmable base editing",
        "creators": [
            {"creatorType": "author", "firstName": "David", "lastName": "Liu"},
            {"creatorType": "author", "firstName": "Andrew", "lastName": "Anzalone"},
        ],
        "abstractNote": "A study of base editing.",
        "publicationTitle": "Nature",
        "volume": "598",
        "issue": "7881",
        "pages": "468-473",
        "date": "2021-10-01",
        "DOI": DOI,
        "ISSN": "0028-0836",
        "url": "",
        "tags": [{"tag": "gene editing", "type": 0}],
        "collections": ["COL00001"],
        "relations": {},
        "dateAdded": "2024-01-15T10:00:00Z",
        "dateModified": "2024-06-01T12:00:00Z",
        "extra": "PMID: 34750604",
    },
    "meta": {"creatorSummary": "Liu and Anzalone", "numChildren": 1},
    "links": {},
}

ZOTERO_COLLECTION_FIXTURE = {
    "key": "COL00001",
    "version": 10,
    "library": {"type": "user", "id": 12345},
    "data": {
        "key": "COL00001",
        "version": 10,
        "name": "Gene Editing",
        "parentCollection": False,
    },
    "meta": {"numCollections": 0, "numItems": 5},
    "links": {},
}


def _make_client():
    """Create a ZoteroClient with mocked pyzotero.Zotero."""
    with patch("paperbridge.clients.zotero.zotero") as mock_zotero_module:
        mock_zot_instance = MagicMock()
        mock_zotero_module.Zotero.return_value = mock_zot_instance

        from paperbridge.clients.zotero import ZoteroClient

        client = ZoteroClient(api_key="fake-key", user_id="12345")
        client._zot = mock_zot_instance
        return client


class TestZoteroClientRead:
    def test_get_items(self):
        client = _make_client()
        client._zot.items.return_value = [ZOTERO_ITEM_FIXTURE]
        client._zot.request = MagicMock()
        client._zot.request.headers = {"Total-Results": "1"}

        result = client.get_items(limit=25)

        assert result.total_results == 1
        assert len(result.items) == 1
        assert result.items[0].key == "ABC12345"
        assert result.items[0].data.title == "Programmable base editing"
        assert result.items[0].data.doi == DOI

    def test_get_item(self):
        client = _make_client()
        client._zot.item.return_value = ZOTERO_ITEM_FIXTURE

        item = client.get_item("ABC12345")

        assert item.key == "ABC12345"
        assert item.version == 42
        assert item.data.item_type == "journalArticle"
        assert len(item.data.creators) == 2
        assert item.data.creators[0].display_name == "David Liu"

    def test_get_all_items(self):
        client = _make_client()
        client._zot.everything.return_value = [ZOTERO_ITEM_FIXTURE]

        items = client.get_all_items()

        assert len(items) == 1
        assert items[0].data.title == "Programmable base editing"

    def test_search(self):
        client = _make_client()
        client._zot.items.return_value = [ZOTERO_ITEM_FIXTURE]
        client._zot.request = MagicMock()
        client._zot.request.headers = {"Total-Results": "1"}

        result = client.search("base editing")

        assert result.query == "base editing"
        client._zot.items.assert_called_once()

    def test_find_item_by_doi_found(self):
        client = _make_client()
        client._zot.items.return_value = [ZOTERO_ITEM_FIXTURE]
        client._zot.request = MagicMock()
        client._zot.request.headers = {"Total-Results": "1"}

        item = client.find_item_by_doi(DOI)

        assert item is not None
        assert item.data.doi == DOI

    def test_find_item_by_doi_not_found(self):
        client = _make_client()
        client._zot.items.return_value = []
        client._zot.request = MagicMock()
        client._zot.request.headers = {"Total-Results": "0"}

        item = client.find_item_by_doi("10.9999/nonexistent")

        assert item is None

    def test_get_collections(self):
        client = _make_client()
        client._zot.collections.return_value = [ZOTERO_COLLECTION_FIXTURE]

        cols = client.get_collections()

        assert len(cols) == 1
        assert cols[0].key == "COL00001"
        assert cols[0].name == "Gene Editing"

    def test_get_tags(self):
        client = _make_client()
        client._zot.tags.return_value = ["gene editing", "CRISPR"]

        tags = client.get_tags()

        assert tags == ["gene editing", "CRISPR"]

    def test_get_item_tags(self):
        client = _make_client()
        client._zot.item.return_value = ZOTERO_ITEM_FIXTURE

        tags = client.get_item_tags("ABC12345")

        assert "gene editing" in tags

    def test_get_items_in_collection(self):
        client = _make_client()
        client._zot.collection_items.return_value = [ZOTERO_ITEM_FIXTURE]
        client._zot.request = MagicMock()
        client._zot.request.headers = {"Total-Results": "1"}

        result = client.get_items_in_collection("COL00001")

        assert len(result.items) == 1


class TestZoteroClientWrite:
    def test_create_item(self):
        client = _make_client()
        client._zot.item_template.return_value = {
            "itemType": "journalArticle",
            "title": "",
            "creators": [],
            "tags": [],
            "collections": [],
        }
        client._zot.create_items.return_value = {
            "successful": {"0": ZOTERO_ITEM_FIXTURE},
            "failed": {},
        }

        item_data = ZoteroItemData(
            item_type="journalArticle",
            title="Test Article",
            doi="10.1234/test",
        )
        item = client.create_item(item_data)

        assert item.key == "ABC12345"
        client._zot.create_items.assert_called_once()

    def test_create_items_batch(self):
        client = _make_client()
        client._zot.item_template.return_value = {
            "itemType": "journalArticle",
            "title": "",
            "creators": [],
            "tags": [],
            "collections": [],
        }
        client._zot.create_items.return_value = {
            "successful": {"0": ZOTERO_ITEM_FIXTURE},
            "failed": {},
        }

        items = [
            ZoteroItemData(item_type="journalArticle", title=f"Article {i}")
            for i in range(3)
        ]
        result = client.create_items(items)

        assert result.total_attempted == 3
        assert len(result.created_keys) == 1  # one call, one fixture returned

    def test_create_item_failure(self):
        client = _make_client()
        client._zot.item_template.return_value = {"itemType": "journalArticle", "title": "", "creators": [], "tags": [], "collections": []}
        client._zot.create_items.return_value = {
            "successful": {},
            "failed": {"0": {"code": 400, "message": "Bad request"}},
        }

        item_data = ZoteroItemData(item_type="journalArticle", title="Bad Article")

        with pytest.raises(RuntimeError, match="Failed to create"):
            client.create_item(item_data)

    def test_add_tags_to_item(self):
        client = _make_client()
        raw_item = {
            "key": "ABC12345",
            "version": 42,
            "data": {
                "tags": [{"tag": "existing", "type": 0}],
            },
        }
        client._zot.item.return_value = raw_item
        client._zot.update_item.return_value = None
        # For the get_item call after update
        updated_fixture = dict(ZOTERO_ITEM_FIXTURE)
        client._zot.item.side_effect = [raw_item, ZOTERO_ITEM_FIXTURE]

        item = client.add_tags_to_item("ABC12345", ["new_tag"])

        client._zot.update_item.assert_called_once()
        call_args = client._zot.update_item.call_args[0][0]
        tag_names = [t["tag"] for t in call_args["data"]["tags"]]
        assert "existing" in tag_names
        assert "new_tag" in tag_names

    def test_add_item_to_collection(self):
        client = _make_client()
        raw_item = {
            "key": "ABC12345",
            "version": 42,
            "data": {"collections": ["COL00001"]},
        }
        client._zot.item.side_effect = [raw_item, ZOTERO_ITEM_FIXTURE]
        client._zot.update_item.return_value = None

        item = client.add_item_to_collection("ABC12345", "COL00002")

        client._zot.update_item.assert_called_once()
        call_args = client._zot.update_item.call_args[0][0]
        assert "COL00002" in call_args["data"]["collections"]

    def test_update_item_partial_does_not_clear_tags(self):
        """update_item with only extra set must not clobber existing tags."""
        client = _make_client()
        raw_item = {
            "key": "ABC12345",
            "version": 42,
            "data": {
                "itemType": "journalArticle",
                "tags": [{"tag": "keep-me", "type": 0}],
                "collections": [],
            },
        }
        client._zot.item.side_effect = [raw_item, ZOTERO_ITEM_FIXTURE]
        client._zot.update_item.return_value = None

        from paperbridge.models.zotero import ZoteroItemData

        client.update_item("ABC12345", ZoteroItemData(extra="a note"))

        call_args = client._zot.update_item.call_args[0][0]
        # tags must be preserved — not replaced with []
        assert call_args["data"]["tags"] == [{"tag": "keep-me", "type": 0}]
        assert call_args["data"]["extra"] == "a note"

    def test_delete_item(self):
        client = _make_client()
        client._zot.item.return_value = ZOTERO_ITEM_FIXTURE
        client._zot.delete_item.return_value = None

        assert client.delete_item("ABC12345") is True


class TestZoteroClientConversion:
    def test_item_to_article_metadata(self):
        client = _make_client()
        client._zot.item.return_value = ZOTERO_ITEM_FIXTURE
        item = client.get_item("ABC12345")

        meta = client.item_to_article_metadata(item)

        assert meta.source == "zotero"
        assert meta.title == "Programmable base editing"
        assert "David Liu" in meta.authors
        assert "Andrew Anzalone" in meta.authors
        assert meta.year == 2021
        assert meta.journal == "Nature"
        assert meta.doi == DOI
        assert meta.pmid == "34750604"

    def test_article_metadata_to_item_data(self):
        client = _make_client()
        meta = ArticleMetadata(
            source="crossref",
            title="Test Article",
            authors=["Jane Smith", "Bob Jones"],
            year=2024,
            journal="Science",
            doi="10.1234/test",
            pmid="99999",
        )

        item_data = client.article_metadata_to_item_data(
            meta, collection_keys=["COL00001"], tags=["imported"]
        )

        assert item_data.item_type == "journalArticle"
        assert item_data.title == "Test Article"
        assert len(item_data.creators) == 2
        assert item_data.creators[0].first_name == "Jane"
        assert item_data.creators[0].last_name == "Smith"
        assert item_data.date == "2024"
        assert item_data.doi == "10.1234/test"
        assert item_data.publication_title == "Science"
        assert "COL00001" in item_data.collections
        assert any(t.tag == "imported" for t in item_data.tags)
        assert "PMID: 99999" in (item_data.extra or "")

    def test_article_record_to_item_data(self):
        client = _make_client()
        record = ArticleRecord(
            doi="10.1234/test",
            metadata=[
                ArticleMetadata(
                    source="crossref",
                    title="Test Article",
                    authors=["Jane Smith"],
                    year=2024,
                    journal="Science",
                    doi="10.1234/test",
                )
            ],
            abstracts=[ArticleAbstract(source="crossref", text="This is the abstract.")],
            keywords=[ArticleKeywords(source="crossref", subjects=["Biology"])],
        )

        item_data = client.article_record_to_item_data(record, tags=["paperbridge"])

        assert item_data.title == "Test Article"
        assert item_data.abstract_note == "This is the abstract."
        tag_names = [t.tag for t in item_data.tags]
        assert "paperbridge" in tag_names
        assert "Biology" in tag_names

    def test_article_record_to_item_data_no_metadata(self):
        client = _make_client()
        record = ArticleRecord(doi="10.1234/empty")

        item_data = client.article_record_to_item_data(record)

        assert item_data.doi == "10.1234/empty"
        assert item_data.item_type == "journalArticle"


class TestZoteroClientInit:
    def test_missing_api_key(self):
        with patch("paperbridge.clients.zotero.zotero") as mock_mod:
            mock_mod.Zotero.return_value = MagicMock()
            from paperbridge.clients.zotero import ZoteroClient

            with pytest.raises(ValueError, match="API key"):
                ZoteroClient(api_key="", user_id="123")

    def test_missing_both_ids(self):
        with patch("paperbridge.clients.zotero.zotero") as mock_mod:
            mock_mod.Zotero.return_value = MagicMock()
            from paperbridge.clients.zotero import ZoteroClient

            with pytest.raises(ValueError, match="user_id or group_id"):
                ZoteroClient(api_key="key")

    def test_user_id_sets_user_type(self):
        with patch("paperbridge.clients.zotero.zotero") as mock_mod:
            mock_mod.Zotero.return_value = MagicMock()
            from paperbridge.clients.zotero import ZoteroClient

            client = ZoteroClient(api_key="key", user_id="111")
            assert client.library_type == "user"
            assert client.library_id == "111"

    def test_group_id_sets_group_type(self):
        with patch("paperbridge.clients.zotero.zotero") as mock_mod:
            mock_mod.Zotero.return_value = MagicMock()
            from paperbridge.clients.zotero import ZoteroClient

            client = ZoteroClient(api_key="key", group_id="222")
            assert client.library_type == "group"
            assert client.library_id == "222"

    def test_group_id_takes_precedence(self):
        with patch("paperbridge.clients.zotero.zotero") as mock_mod:
            mock_mod.Zotero.return_value = MagicMock()
            from paperbridge.clients.zotero import ZoteroClient

            client = ZoteroClient(api_key="key", user_id="111", group_id="222")
            assert client.library_type == "group"
            assert client.library_id == "222"

    def test_context_manager(self):
        client = _make_client()
        with client as c:
            assert c is client

    def test_repr_user(self):
        client = _make_client()
        assert "user_id=" in repr(client)
        assert "12345" in repr(client)

    def test_repr_group(self):
        with patch("paperbridge.clients.zotero.zotero") as mock_mod:
            mock_mod.Zotero.return_value = MagicMock()
            from paperbridge.clients.zotero import ZoteroClient

            client = ZoteroClient(api_key="key", group_id="999")
            assert "group_id=" in repr(client)
            assert "999" in repr(client)


class TestZoteroModels:
    def test_creator_display_name_personal(self):
        c = ZoteroCreator(creator_type="author", first_name="Jane", last_name="Doe")
        assert c.display_name == "Jane Doe"

    def test_creator_display_name_institutional(self):
        c = ZoteroCreator(creator_type="author", name="World Health Organization")
        assert c.display_name == "World Health Organization"

    def test_creator_display_name_last_only(self):
        c = ZoteroCreator(creator_type="author", last_name="Smith")
        assert c.display_name == "Smith"

    def test_item_data_from_zotero_json(self):
        """Test that ZoteroItemData can parse camelCase Zotero JSON."""
        raw = {
            "itemType": "journalArticle",
            "title": "Test",
            "DOI": "10.1234/test",
            "abstractNote": "Abstract text",
            "publicationTitle": "Nature",
            "dateAdded": "2024-01-01T00:00:00Z",
        }
        data = ZoteroItemData.model_validate(raw)
        assert data.item_type == "journalArticle"
        assert data.doi == "10.1234/test"
        assert data.abstract_note == "Abstract text"
        assert data.publication_title == "Nature"

    def test_item_data_extra_fields_allowed(self):
        """Zotero items may have type-specific fields not in our schema."""
        raw = {
            "itemType": "bookSection",
            "title": "Chapter 1",
            "bookTitle": "A Great Book",
        }
        data = ZoteroItemData.model_validate(raw)
        assert data.title == "Chapter 1"
        # Extra field accessible via model_extra
        assert data.model_extra.get("bookTitle") == "A Great Book"

    def test_extract_pmid_from_extra(self):
        from paperbridge.clients.zotero import ZoteroClient

        assert ZoteroClient._extract_pmid_from_extra("PMID: 12345678") == "12345678"
        assert ZoteroClient._extract_pmid_from_extra("Some note\nPMID: 99999") == "99999"
        assert ZoteroClient._extract_pmid_from_extra("No PMID here") is None
        assert ZoteroClient._extract_pmid_from_extra(None) is None


class TestUploadBib:
    BIB = """
@article{smith2024,
  title     = {Heart Rate Variability in Children},
  author    = {Smith, Jane and Doe, John},
  journal   = {Psychophysiology},
  year      = {2024},
  volume    = {61},
  number    = {3},
  pages     = {e14500},
  doi       = {10.1111/psyp.14500},
  issn      = {0048-5772},
  abstract  = {We studied HRV.},
  keywords  = {HRV, children, autonomic},
}

@article{jones2023,
  title   = {No DOI Article},
  author  = {Jones, Bob},
  journal = {Nature},
  year    = {2023},
}
"""

    def test_bibtex_entry_to_item_data_fields(self):
        client = _make_client()
        import bibtexparser
        entries = bibtexparser.loads(self.BIB).entries
        item_data = client._bibtex_entry_to_item_data(entries[0], extra_tags=["imported"])

        assert item_data.item_type == "journalArticle"
        assert item_data.title == "Heart Rate Variability in Children"
        assert item_data.publication_title == "Psychophysiology"
        assert item_data.volume == "61"
        assert item_data.issue == "3"
        assert item_data.pages == "e14500"
        assert item_data.doi == "10.1111/psyp.14500"
        assert item_data.issn == "0048-5772"
        assert item_data.abstract_note == "We studied HRV."
        assert item_data.date == "2024"

        tag_names = [t.tag for t in item_data.tags]
        assert "HRV" in tag_names
        assert "children" in tag_names
        assert "autonomic" in tag_names
        assert "imported" in tag_names

    def test_bibtex_entry_to_item_data_authors(self):
        client = _make_client()
        import bibtexparser
        entries = bibtexparser.loads(self.BIB).entries
        item_data = client._bibtex_entry_to_item_data(entries[0])

        assert len(item_data.creators) == 2
        assert item_data.creators[0].last_name == "Smith"
        assert item_data.creators[0].first_name == "Jane"
        assert item_data.creators[1].last_name == "Doe"
        assert item_data.creators[1].first_name == "John"

    def test_upload_bib_creates_items(self):
        client = _make_client()
        client._zot.item_template.return_value = {
            "itemType": "journalArticle", "title": "", "creators": [],
            "tags": [], "collections": [],
        }
        client._zot.create_items.return_value = {
            "successful": {"0": {"key": "NEW0001"}, "1": {"key": "NEW0002"}},
            "failed": {},
        }
        # find_item_by_doi → not found (so nothing skipped)
        client._zot.items.return_value = []
        client._zot.request = MagicMock()
        client._zot.request.headers = {"Total-Results": "0"}

        result = client.upload_bib(self.BIB)

        assert len(result.created_keys) == 2
        assert not result.failed
        assert result.total_attempted == 2

    def test_upload_bib_skip_existing(self):
        from paperbridge.models.zotero import ZoteroItem, ZoteroItemData as ZID
        client = _make_client()

        # find_item_by_doi returns a hit for the first DOI only
        existing = MagicMock(spec=ZoteroItem)
        existing.data = ZID(doi="10.1111/psyp.14500")

        call_count = {"n": 0}
        def _fake_get_items(**kwargs):
            call_count["n"] += 1
            if "10.1111/psyp.14500" in str(kwargs.get("q", "")):
                mock_result = MagicMock()
                mock_result.items = [existing]
                return mock_result
            mock_result = MagicMock()
            mock_result.items = []
            return mock_result

        client.get_items = _fake_get_items
        client._zot.item_template.return_value = {
            "itemType": "journalArticle", "title": "", "creators": [],
            "tags": [], "collections": [],
        }
        client._zot.create_items.return_value = {
            "successful": {"0": {"key": "NEW0002"}},
            "failed": {},
        }

        result = client.upload_bib(self.BIB, skip_existing=True)

        # Only the no-DOI article (jones2023) gets created; smith2024 is skipped
        assert len(result.created_keys) == 1

    def test_upload_bib_new_collection(self):
        client = _make_client()
        client._zot.create_collections.return_value = {
            "successful": {"0": {"key": "NEWCOL1", "version": 1,
                                  "data": {"key": "NEWCOL1", "name": "My Import",
                                           "parentCollection": False}}},
            "failed": {},
        }
        client._zot.item_template.return_value = {
            "itemType": "journalArticle", "title": "", "creators": [],
            "tags": [], "collections": [],
        }
        client._zot.create_items.return_value = {
            "successful": {"0": {"key": "NEW0001"}, "1": {"key": "NEW0002"}},
            "failed": {},
        }
        client._zot.items.return_value = []
        client._zot.request = MagicMock()
        client._zot.request.headers = {"Total-Results": "0"}

        result = client.upload_bib(self.BIB, new_collection_name="My Import")

        client._zot.create_collections.assert_called_once()
        assert len(result.created_keys) == 2

    def test_upload_bib_mutual_exclusion(self):
        client = _make_client()
        import pytest
        with pytest.raises(ValueError, match="not both"):
            client.upload_bib(self.BIB, collection_key="ABC", new_collection_name="New")

    def test_upload_bib_from_path(self, tmp_path):
        client = _make_client()
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(self.BIB, encoding="utf-8")
        client._zot.item_template.return_value = {
            "itemType": "journalArticle", "title": "", "creators": [],
            "tags": [], "collections": [],
        }
        client._zot.create_items.return_value = {
            "successful": {"0": {"key": "A"}, "1": {"key": "B"}},
            "failed": {},
        }
        client._zot.items.return_value = []
        client._zot.request = MagicMock()
        client._zot.request.headers = {"Total-Results": "0"}

        result = client.upload_bib(bib_file)
        assert len(result.created_keys) == 2
