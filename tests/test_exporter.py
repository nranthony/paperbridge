"""Tests for CitationExporter.export_article."""

import json
from pathlib import Path

import pytest

from paperbridge.models.article import ArticleAbstract, ArticleKeywords, ArticleMetadata, ArticleRecord
from paperbridge.utils.exporter import CitationExporter


@pytest.fixture
def sample_record():
    return ArticleRecord(
        doi="10.1234/test",
        metadata=[
            ArticleMetadata(source="crossref", title="Test Paper", authors=["Alice"], year=2023, doi="10.1234/test")
        ],
        abstracts=[ArticleAbstract(source="crossref", text="Some abstract.")],
        keywords=[ArticleKeywords(source="crossref", author_keywords=["CRISPR"])],
    )


class TestExportArticle:
    def test_writes_valid_json(self, tmp_path, sample_record):
        filepath = str(tmp_path / "record.json")
        result = CitationExporter.export_article(sample_record, filepath)
        assert Path(result).exists()
        with open(result) as f:
            data = json.load(f)
        assert "export_info" in data
        assert "record" in data

    def test_export_info_has_expected_keys(self, tmp_path, sample_record):
        filepath = str(tmp_path / "record.json")
        result = CitationExporter.export_article(sample_record, filepath)
        with open(result) as f:
            data = json.load(f)
        info = data["export_info"]
        assert "timestamp" in info
        assert info["paperbridge_version"] == "0.1.0"
        assert info["record_type"] == "ArticleRecord"

    def test_record_preserves_all_sources(self, tmp_path, sample_record):
        filepath = str(tmp_path / "record.json")
        result = CitationExporter.export_article(sample_record, filepath)
        with open(result) as f:
            data = json.load(f)
        record = data["record"]
        assert record["doi"] == "10.1234/test"
        assert len(record["metadata"]) == 1
        assert record["metadata"][0]["source"] == "crossref"
        assert len(record["abstracts"]) == 1
        assert len(record["keywords"]) == 1

    def test_returns_absolute_path(self, tmp_path, sample_record):
        filepath = str(tmp_path / "record.json")
        result = CitationExporter.export_article(sample_record, filepath)
        assert Path(result).is_absolute()

    def test_creates_parent_directories(self, tmp_path, sample_record):
        filepath = str(tmp_path / "nested" / "dir" / "record.json")
        result = CitationExporter.export_article(sample_record, filepath)
        assert Path(result).exists()
