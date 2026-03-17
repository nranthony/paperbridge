"""Document Parser Client for PDF, XML, HTML."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from loguru import logger

from paperbridge.models.document import ContentAssessment, DocumentMetadata, ParsedDocument, Table
from paperbridge.models.doi import DownloadLink

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import trafilatura
except ImportError:
    trafilatura = None


class DocumentParserClient:
    """Generic document parser for scientific documents."""

    def __init__(self):
        if pdfplumber is None:
            logger.warning("pdfplumber not installed. PDF parsing unavailable. pip install pdfplumber")

    def parse(self, source: Union[str, Path], format: str = "auto") -> ParsedDocument:
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"Document not found: {source}")

        if format == "auto":
            suffix = source_path.suffix.lower()
            format_map = {".pdf": "pdf", ".xml": "xml", ".nxml": "xml", ".html": "html", ".htm": "html"}
            format = format_map.get(suffix)
            if not format:
                raise ValueError(f"Cannot auto-detect format for: {suffix}")

        if format == "pdf":
            return self.parse_pdf(str(source_path))
        elif format == "xml":
            return self.parse_xml(source_path.read_text(encoding="utf-8"))
        elif format == "html":
            return self.parse_html(source_path.read_text(encoding="utf-8"))
        raise ValueError(f"Unsupported format: {format}")

    def parse_pdf(self, pdf_path: Union[str, Path]) -> ParsedDocument:
        if pdfplumber is None:
            raise ImportError("pdfplumber required for PDF parsing. pip install pdfplumber")

        with pdfplumber.open(pdf_path) as pdf:
            full_text = []
            tables = []
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    full_text.append(page_text)
                for table_data in page.extract_tables():
                    if table_data and len(table_data) > 0:
                        headers = table_data[0] if table_data[0] else []
                        rows = table_data[1:] if len(table_data) > 1 else []
                        tables.append(Table(headers=headers, rows=rows, location=f"Page {page_num}"))

            content = "\n\n".join(full_text)
            sections = self._extract_sections(content)
            metadata = self._extract_pdf_metadata(full_text[0] if full_text else "")

            return ParsedDocument(
                content=content, sections=sections, tables=tables, metadata=metadata,
                format="pdf", page_count=len(pdf.pages), parser_version="pdfplumber",
            )

    def parse_xml(self, xml_content: str, schema: str = "pmc") -> ParsedDocument:
        soup = BeautifulSoup(xml_content, "xml")
        if schema == "pmc":
            return self._parse_pmc_xml(soup, xml_content)
        content = soup.get_text(separator=" ", strip=True)
        return ParsedDocument(
            content=content, format="xml", raw_content=xml_content, metadata=DocumentMetadata(),
            parser_version="beautifulsoup4",
        )

    def _parse_pmc_xml(self, soup: BeautifulSoup, raw_xml: str) -> ParsedDocument:
        metadata = self._extract_pmc_metadata(soup)
        sections: Dict[str, str] = {}
        full_text_parts = []

        abstract = soup.find("abstract")
        if abstract:
            abstract_text = abstract.get_text(separator=" ", strip=True)
            sections["abstract"] = abstract_text
            full_text_parts.append(abstract_text)

        body = soup.find("body")
        if body:
            for section in body.find_all("sec", recursive=False):
                title_tag = section.find("title")
                section_title = title_tag.get_text(strip=True) if title_tag else "Untitled"
                section_text = section.get_text(separator=" ", strip=True)
                sections[section_title.lower().replace(" ", "_")] = section_text
                full_text_parts.append(section_text)

        tables = self._extract_xml_tables(soup)
        content = "\n\n".join(full_text_parts)

        return ParsedDocument(
            content=content, sections=sections, tables=tables, metadata=metadata,
            format="xml", raw_content=raw_xml, parser_version="beautifulsoup4",
        )

    def parse_html(self, html_content: str) -> ParsedDocument:
        soup = BeautifulSoup(html_content, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()

        content = soup.get_text(separator=" ", strip=True)
        sections: Dict[str, str] = {}
        for heading in soup.find_all(["h1", "h2", "h3"]):
            title = heading.get_text(strip=True)
            section_text = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ["h1", "h2", "h3"]:
                    break
                section_text.append(sibling.get_text(strip=True))
            if section_text:
                sections[title.lower().replace(" ", "_")] = " ".join(section_text)

        tables = []
        for table in soup.find_all("table"):
            table_obj = self._parse_html_table(table)
            if table_obj:
                tables.append(table_obj)

        metadata = DocumentMetadata()
        title_tag = soup.find("title")
        if title_tag:
            metadata.title = title_tag.get_text(strip=True)

        return ParsedDocument(
            content=content, sections=sections, tables=tables, metadata=metadata,
            format="html", raw_content=html_content, parser_version="beautifulsoup4",
        )

    def parse_html_trafilatura(self, html_content: str, url: Optional[str] = None) -> ParsedDocument:
        if trafilatura is None:
            return self.parse_html(html_content)

        try:
            import json as _json
            extracted = trafilatura.extract(
                html_content, url=url, include_tables=True, include_images=False,
                include_links=False, output_format="json", with_metadata=True,
            )
            if not extracted:
                return self.parse_html(html_content)

            data = _json.loads(extracted)
            metadata = DocumentMetadata(
                title=data.get("title"),
                authors=data.get("author", "").split("; ") if data.get("author") else [],
                abstract=data.get("excerpt"),
            )
            content = data.get("text", "")
            sections = self._extract_sections(content)

            soup = BeautifulSoup(html_content, "html.parser")
            tables = [t for t in (self._parse_html_table(tbl) for tbl in soup.find_all("table")) if t]

            return ParsedDocument(
                content=content, sections=sections, tables=tables, metadata=metadata,
                format="html", raw_content=html_content, parser_version="trafilatura",
            )
        except Exception:
            return self.parse_html(html_content)

    def assess_completeness(self, doc: ParsedDocument) -> ContentAssessment:
        return ContentAssessment.from_parsed_document(doc)

    def find_download_links(self, html_content: str, base_url: str) -> List[DownloadLink]:
        soup = BeautifulSoup(html_content, "html.parser")
        links = []
        pdf_patterns = ["download pdf", "pdf", "full text pdf", "download article"]
        xml_patterns = ["download xml", "xml", "full text xml"]

        for tag in soup.find_all(["a", "button"]):
            href = tag.get("href", "")
            text = tag.get_text(strip=True).lower()
            if not href:
                continue
            absolute_url = urljoin(base_url, href)
            detected_format = None
            if any(p in text for p in pdf_patterns) or ".pdf" in href.lower():
                detected_format = "pdf"
            elif any(p in text for p in xml_patterns) or ".xml" in href.lower():
                detected_format = "xml"
            if detected_format:
                links.append(DownloadLink(
                    url=absolute_url, format=detected_format, link_text=tag.get_text(strip=True), element_type=tag.name
                ))
        return links

    def _extract_sections(self, text: str) -> Dict[str, str]:
        sections: Dict[str, str] = {}
        section_patterns = [
            r"abstract", r"introduction", r"background", r"methods", r"materials\s+and\s+methods",
            r"methodology", r"results", r"discussion", r"conclusions?", r"acknowledgments?", r"references",
        ]
        pattern = r"\n\s*(" + "|".join(section_patterns) + r")\s*\n"
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for i, match in enumerate(matches):
            section_name = match.group(1).strip().lower()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections[section_name] = text[start:end].strip()
        return sections

    def _extract_pdf_metadata(self, first_page_text: str) -> DocumentMetadata:
        metadata = DocumentMetadata()
        doi_match = re.search(r"10\.\d{4,}/[^\s]+", first_page_text)
        if doi_match:
            metadata.doi = doi_match.group(0)
        lines = first_page_text.split("\n")
        if lines:
            metadata.title = lines[0].strip()
        return metadata

    def _extract_pmc_metadata(self, soup: BeautifulSoup) -> DocumentMetadata:
        metadata = DocumentMetadata()
        title_tag = soup.find("article-title")
        if title_tag:
            metadata.title = title_tag.get_text(strip=True)
        authors = []
        for contrib in soup.find_all("contrib", {"contrib-type": "author"}):
            surname = contrib.find("surname")
            given_names = contrib.find("given-names")
            if surname:
                name = surname.get_text(strip=True)
                if given_names:
                    name = f"{name}, {given_names.get_text(strip=True)}"
                authors.append(name)
        metadata.authors = authors
        doi_tag = soup.find("article-id", {"pub-id-type": "doi"})
        if doi_tag:
            metadata.doi = doi_tag.get_text(strip=True)
        pmc_tag = soup.find("article-id", {"pub-id-type": "pmc"})
        if pmc_tag:
            metadata.pmcid = f"PMC{pmc_tag.get_text(strip=True)}"
        pmid_tag = soup.find("article-id", {"pub-id-type": "pmid"})
        if pmid_tag:
            metadata.pmid = pmid_tag.get_text(strip=True)
        journal_tag = soup.find("journal-title")
        if journal_tag:
            metadata.journal = journal_tag.get_text(strip=True)
        abstract = soup.find("abstract")
        if abstract:
            metadata.abstract = abstract.get_text(separator=" ", strip=True)
        return metadata

    def _extract_xml_tables(self, soup: BeautifulSoup) -> List[Table]:
        tables = []
        for table_wrap in soup.find_all("table-wrap"):
            caption_tag = table_wrap.find("caption")
            caption = caption_tag.get_text(strip=True) if caption_tag else None
            table_id = table_wrap.get("id")
            table_tag = table_wrap.find("table")
            if table_tag:
                headers = []
                thead = table_tag.find("thead")
                if thead:
                    headers = [th.get_text(strip=True) for th in thead.find_all("th")]
                rows = []
                tbody = table_tag.find("tbody")
                if tbody:
                    rows = [[td.get_text(strip=True) for td in tr.find_all(["td", "th"])] for tr in tbody.find_all("tr")]
                tables.append(Table(caption=caption, headers=headers, rows=rows, table_id=table_id))
        return tables

    def _parse_html_table(self, table_tag) -> Optional[Table]:
        headers = []
        thead = table_tag.find("thead")
        if thead:
            headers = [th.get_text(strip=True) for th in thead.find_all("th")]
        if not headers:
            first_row = table_tag.find("tr")
            if first_row:
                headers = [th.get_text(strip=True) for th in first_row.find_all("th")]
        rows = []
        tbody = table_tag.find("tbody") or table_tag
        for tr in tbody.find_all("tr"):
            if tr.find("th") and headers:
                continue
            row = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if row:
                rows.append(row)
        if not rows:
            return None
        caption_tag = table_tag.find("caption")
        caption = caption_tag.get_text(strip=True) if caption_tag else None
        return Table(caption=caption, headers=headers, rows=rows)
