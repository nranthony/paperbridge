"""Citation Exporter — export workflow results to markdown, JSON, and CSV."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from paperbridge.models.article import ArticleRecord
from paperbridge.models.citation_workflow import CitationVerificationResult, WorkflowInput
from paperbridge.models.citation_workflow import SupportType  # noqa: F401


class CitationExporter:
    """Export citation workflow results to multiple formats."""

    @staticmethod
    def export_article(record: ArticleRecord, filepath: str) -> str:
        """Serialise an ArticleRecord to JSON with a metadata header. Returns absolute path."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "paperbridge_version": "0.1.0",
                "record_type": "ArticleRecord",
            },
            "record": record.model_dump(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"ArticleRecord exported to: {filepath}")
        return str(filepath.absolute())

    @staticmethod
    def export_markdown(summary: str, filepath: str) -> str:
        """Export markdown summary to file. Returns absolute path."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(summary)
        logger.info(f"Markdown exported to: {filepath}")
        return str(filepath.absolute())

    @staticmethod
    def export_json(
        input_data: WorkflowInput,
        verified_citations: List[CitationVerificationResult],
        statistics: Dict[str, int],
        filepath: str,
        **metadata: Any,
    ) -> str:
        """Export workflow results to JSON. Returns absolute path."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "paperbridge_version": "0.1.0",
                "workflow": "citation_workflow",
                "total_citations": len(verified_citations),
            },
            "input": {
                "statement": input_data.statement,
                "bullet_points": input_data.bullet_points,
                "max_results_per_tier": input_data.max_results_per_tier,
                "find_contrary": input_data.find_contrary,
                "contrary_weight": input_data.contrary_weight,
                "min_publication_year": input_data.min_publication_year,
            },
            "statistics": statistics,
            "verified_citations": [
                {
                    "citation_number": i + 1,
                    "title": c.citation.title,
                    "authors": c.citation.authors,
                    "journal": c.citation.journal,
                    "year": c.citation.year,
                    "doi": c.citation.doi,
                    "pmid": c.citation.pmid,
                    "pmc_id": c.citation.pmc_id,
                    "url": c.citation.url,
                    "verification_status": c.verification_status.value,
                    "relevance_score": c.relevance_score,
                    "support_type": c.support_type.value,
                    "full_text_excerpt": c.full_text_excerpt,
                    "section_found": c.section_found,
                    "full_text_available": c.full_text_available,
                    "download_source": c.download_source,
                }
                for i, c in enumerate(verified_citations)
            ],
            "metadata": metadata,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"JSON exported to: {filepath}")
        return str(filepath.absolute())

    @staticmethod
    def export_csv(
        verified_citations: List[CitationVerificationResult],
        filepath: str,
    ) -> str:
        """Export citations to CSV table. Returns absolute path."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "citation_number", "title", "authors", "journal", "year", "doi",
            "pmid", "relevance_score", "support_type", "verification_status",
            "full_text_available", "download_source",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for i, citation in enumerate(verified_citations, 1):
                writer.writerow({
                    "citation_number": i,
                    "title": citation.citation.title or "",
                    "authors": "; ".join(citation.citation.authors or []),
                    "journal": citation.citation.journal or "",
                    "year": citation.citation.year or "",
                    "doi": citation.citation.doi or "",
                    "pmid": citation.citation.pmid or "",
                    "relevance_score": citation.relevance_score,
                    "support_type": citation.support_type.value,
                    "verification_status": citation.verification_status.value,
                    "full_text_available": citation.full_text_available,
                    "download_source": citation.download_source or "",
                })

        logger.info(f"CSV exported to: {filepath}")
        return str(filepath.absolute())

    @staticmethod
    def export_all(
        summary: str,
        input_data: WorkflowInput,
        verified_citations: List[CitationVerificationResult],
        statistics: Dict[str, int],
        base_filename: str,
        **metadata: Any,
    ) -> Dict[str, str]:
        """Export to all formats at once. Returns dict mapping format to file path."""
        paths = {}
        paths["markdown"] = CitationExporter.export_markdown(summary, f"{base_filename}.md")
        paths["json"] = CitationExporter.export_json(
            input_data, verified_citations, statistics, f"{base_filename}.json", **metadata
        )
        paths["csv"] = CitationExporter.export_csv(verified_citations, f"{base_filename}.csv")
        logger.info(f"Exported to all formats: {base_filename}.*")
        return paths
