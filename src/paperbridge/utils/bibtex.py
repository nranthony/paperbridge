"""BibTeX <-> JSON conversion utilities."""

import json
from typing import Optional

from loguru import logger

try:
    import bibtexparser
    BIBTEXPARSER_AVAILABLE = True
except ImportError:
    BIBTEXPARSER_AVAILABLE = False


def _check_bibtexparser() -> None:
    if not BIBTEXPARSER_AVAILABLE:
        raise ImportError("bibtexparser required. pip install bibtexparser")


def bib_file_to_json(bib_path: str, output_path: Optional[str] = None) -> str:
    """Convert a BibTeX (.bib) file to JSON. Returns JSON string; optionally writes to output_path."""
    _check_bibtexparser()
    logger.info(f"Loading bib file: {bib_path}")
    with open(bib_path) as f:
        db = bibtexparser.load(f)

    entries = db.entries
    result = json.dumps(entries, indent=2, ensure_ascii=False)

    if output_path:
        with open(output_path, "w") as f:
            f.write(result)
        logger.info(f"Wrote {len(entries)} entries to {output_path}")

    return result


def json_to_bib_file(json_path: str, output_path: str) -> str:
    """Convert a JSON file (list of BibTeX entry dicts) back to a .bib file. Returns summary string."""
    _check_bibtexparser()
    logger.info(f"Loading JSON: {json_path}")
    with open(json_path) as f:
        entries = json.load(f)

    db = bibtexparser.bibdatabase.BibDatabase()
    db.entries = entries

    writer = bibtexparser.bwriter.BibTexWriter()
    writer.indent = "\t"

    with open(output_path, "w") as f:
        bibtexparser.dump(db, f, writer)

    logger.info(f"Wrote {len(entries)} entries to {output_path}")
    return f"Wrote {len(entries)} entries to {output_path}"


def bib_string_to_json(bib_string: str) -> str:
    """Parse a raw BibTeX string and return its entries as a JSON string."""
    _check_bibtexparser()
    db = bibtexparser.loads(bib_string)
    return json.dumps(db.entries, indent=2, ensure_ascii=False)
