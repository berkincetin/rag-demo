"""Load DOCX policies into sections that follow the heading hierarchy.

Tables are rendered as Markdown and appended to the section they appear in,
because the most queryable facts in this corpus live in tables.
"""

from pathlib import Path

import docx
from docx.document import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from azure.rag.models import RawSection
from azure.rag.normalize import clean_text

_PREAMBLE_TITLE = "Belge Bilgileri"


def rows_to_markdown(rows: list[list[str]]) -> str:
    """Render table rows as a Markdown table. First row is the header."""
    if not rows:
        return ""
    escaped = [[cell.replace("|", "\\|").strip() for cell in row] for row in rows]
    header = "| " + " | ".join(escaped[0]) + " |"
    separator = "| " + " | ".join("---" for _ in escaped[0]) + " |"
    body = ["| " + " | ".join(row) + " |" for row in escaped[1:]]
    return "\n".join([header, separator, *body])


def _iter_block_items(document: Document):
    """Yield paragraphs and tables in document order.

    `document.paragraphs` alone would skip every table.
    """
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _style_name(paragraph: Paragraph) -> str:
    """Style can be None on some paragraphs; treat that as no style."""
    return getattr(paragraph.style, "name", "") or ""


def load_docx(path: Path) -> list[RawSection]:
    """Split a DOCX into sections keyed by its Heading 1 / Heading 2 structure."""
    document = docx.Document(str(path))
    sections: list[RawSection] = []
    heading_1 = ""
    heading_2 = ""
    current = RawSection(
        source_file=path.name,
        doc_type="docx",
        text="",
        section_title=_PREAMBLE_TITLE,
        section_path=_PREAMBLE_TITLE,
    )
    sections.append(current)

    def open_section() -> RawSection:
        path_parts = [part for part in (heading_1, heading_2) if part]
        section = RawSection(
            source_file=path.name,
            doc_type="docx",
            text="",
            section_title=heading_2 or heading_1,
            section_path=" > ".join(path_parts),
        )
        sections.append(section)
        return section

    for block in _iter_block_items(document):
        if isinstance(block, Table):
            rows = [[cell.text for cell in row.cells] for row in block.rows]
            current.text += "\n" + rows_to_markdown(rows) + "\n"
            continue

        text = block.text.strip()
        if not text:
            continue
        style = _style_name(block)
        if style == "Heading 1":
            heading_1, heading_2 = text, ""
            current = open_section()
        elif style == "Heading 2":
            heading_2 = text
            current = open_section()
        elif style == "List Paragraph":
            current.text += f"- {text}\n"
        else:
            current.text += text + "\n"

    for section in sections:
        section.text = clean_text(section.text)
    return [section for section in sections if section.text]
