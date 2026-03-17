"""Shared fixtures for paperbridge tests."""

import pytest

from paperbridge.models.article import (
    ArticleAbstract,
    ArticleKeywords,
    ArticleMetadata,
)


SAMPLE_DOI = "10.1038/s41586-021-03819-2"


@pytest.fixture
def sample_keywords():
    return ArticleKeywords(
        source="test",
        mesh_terms=["CRISPR-Cas Systems", "Gene Editing"],
        author_keywords=["base editing", "prime editing"],
        subjects=["Biochemistry"],
    )


@pytest.fixture
def sample_abstract():
    return ArticleAbstract(
        source="test",
        text="A study of CRISPR base editing.",
        structured=False,
    )


@pytest.fixture
def sample_metadata():
    return ArticleMetadata(
        source="test",
        title="Programmable base editing",
        authors=["David Liu", "Andrew Anzalone"],
        year=2021,
        journal="Nature",
        doi=SAMPLE_DOI,
        citation_count=1200,
    )
