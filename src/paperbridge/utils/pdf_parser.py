"""Enhanced PDF Parser using pymupdf4llm for academic PDFs."""

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

try:
    import pymupdf4llm
    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    PYMUPDF4LLM_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class EnhancedPDFParser:
    """Enhanced PDF parser using pymupdf4llm for better academic PDF handling.

    Features multi-column layout detection, floating figure/caption handling,
    markdown output with structure preservation. Falls back to basic PyMuPDF
    extraction if pymupdf4llm is unavailable.
    """

    def __init__(self, use_pymupdf4llm: bool = True):
        self.use_pymupdf4llm = use_pymupdf4llm and PYMUPDF4LLM_AVAILABLE
        if use_pymupdf4llm and not PYMUPDF4LLM_AVAILABLE:
            logger.warning("pymupdf4llm not available — install with: pip install pymupdf4llm")

    def parse_pdf(
        self, pdf_path: str, extract_images: bool = False, pages: Optional[List[int]] = None
    ) -> Dict:
        """Parse PDF and extract structured content.

        Returns dict with keys: text, metadata, page_count, method, sections, quality.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        if self.use_pymupdf4llm:
            return self._parse_with_pymupdf4llm(pdf_path, extract_images, pages)
        return self._parse_fallback(pdf_path, pages)

    def _parse_with_pymupdf4llm(
        self, pdf_path: Path, extract_images: bool, pages: Optional[List[int]]
    ) -> Dict:
        try:
            md_text = pymupdf4llm.to_markdown(str(pdf_path), pages=pages, write_images=extract_images)
            metadata = {}
            page_count = 0
            if PYMUPDF_AVAILABLE:
                try:
                    doc = fitz.open(pdf_path)
                    metadata = doc.metadata or {}
                    page_count = doc.page_count
                    doc.close()
                except Exception as e:
                    logger.debug(f"Failed to extract metadata: {e}")

            sections = self._detect_sections_from_markdown(md_text)
            return {
                "text": md_text, "metadata": metadata, "page_count": page_count,
                "method": "pymupdf4llm", "sections": sections, "quality": "high",
            }
        except Exception as e:
            logger.error(f"pymupdf4llm parsing failed: {e}")
            return self._parse_fallback(pdf_path, pages)

    def _parse_fallback(self, pdf_path: Path, pages: Optional[List[int]]) -> Dict:
        if not PYMUPDF_AVAILABLE:
            return {
                "text": "", "metadata": {}, "page_count": 0, "method": "none",
                "sections": {}, "quality": "none", "error": "No PDF parsing libraries available",
            }
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata or {}
            page_count = doc.page_count
            page_list = [p for p in pages if 0 <= p < page_count] if pages else range(page_count)
            text_parts = [doc[p].get_text() for p in page_list]
            doc.close()
            text = "\n\n".join(text_parts)
            sections = self._detect_sections_basic(text)
            return {
                "text": text, "metadata": metadata, "page_count": page_count,
                "method": "pymupdf_basic", "sections": sections, "quality": "medium",
            }
        except Exception as e:
            logger.error(f"Fallback PDF parsing failed: {e}")
            return {
                "text": "", "metadata": {}, "page_count": 0, "method": "failed",
                "sections": {}, "quality": "none", "error": str(e),
            }

    def _detect_sections_from_markdown(self, md_text: str) -> Dict[str, str]:
        sections: Dict[str, str] = {}
        common_headers = [
            "abstract", "introduction", "background", "methods", "methodology",
            "materials and methods", "results", "findings", "discussion",
            "conclusion", "conclusions", "references",
        ]
        lines = md_text.split("\n")
        current_section = None
        current_content: List[str] = []

        for line in lines:
            if line.startswith("#"):
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                header_text = line.lstrip("#").strip().lower()
                current_section = None
                current_content = []
                for common in common_headers:
                    if common in header_text:
                        current_section = common.replace(" ", "_")
                        break
            elif current_section:
                current_content.append(line)

        if current_section and current_content:
            sections[current_section] = "\n".join(current_content).strip()
        return sections

    def _detect_sections_basic(self, text: str) -> Dict[str, str]:
        sections: Dict[str, str] = {}
        section_markers = [
            ("abstract", ["ABSTRACT", "Abstract"]),
            ("introduction", ["INTRODUCTION", "Introduction", "1. INTRODUCTION"]),
            ("methods", ["METHODS", "Methods", "MATERIALS AND METHODS", "METHODOLOGY"]),
            ("results", ["RESULTS", "Results"]),
            ("discussion", ["DISCUSSION", "Discussion"]),
            ("conclusion", ["CONCLUSION", "Conclusion", "CONCLUSIONS"]),
        ]
        for section_key, markers in section_markers:
            for marker in markers:
                start_idx = text.find(marker)
                if start_idx != -1:
                    end_idx = len(text)
                    for next_key, next_markers in section_markers:
                        if next_key == section_key:
                            continue
                        for nm in next_markers:
                            ni = text.find(nm, start_idx + len(marker))
                            if ni != -1 and ni < end_idx:
                                end_idx = ni
                    section_text = text[start_idx + len(marker):end_idx].strip()
                    sections[section_key] = section_text[:2000]
                    break
        return sections

    @staticmethod
    def is_available() -> bool:
        return PYMUPDF4LLM_AVAILABLE or PYMUPDF_AVAILABLE

    @staticmethod
    def get_capabilities() -> Dict[str, bool]:
        return {
            "pymupdf4llm": PYMUPDF4LLM_AVAILABLE,
            "pymupdf_basic": PYMUPDF_AVAILABLE,
            "markdown_output": PYMUPDF4LLM_AVAILABLE,
            "section_detection": PYMUPDF4LLM_AVAILABLE or PYMUPDF_AVAILABLE,
            "metadata_extraction": PYMUPDF_AVAILABLE,
        }
