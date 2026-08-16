"""Discover and load every supported document in the corpus directory."""

import logging
from pathlib import Path

from azure.rag.loaders.docx_loader import load_docx
from azure.rag.loaders.pdf_loader import load_pdf
from azure.rag.loaders.xlsx_loader import load_xlsx
from azure.rag.models import RawSection

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".xlsx"}

_LOADERS = {".pdf": load_pdf, ".docx": load_docx, ".xlsx": load_xlsx}


def load_all(data_dir: Path) -> list[RawSection]:
    """Load every supported file in `data_dir`, skipping temp and unknown files."""
    sections: list[RawSection] = []
    for path in sorted(Path(data_dir).glob("*")):
        if path.name.startswith("~$") or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        loader = _LOADERS[path.suffix.lower()]
        loaded = loader(path)
        logger.info("loaded %s sections from %s", len(loaded), path.name)
        sections.extend(loaded)
    return sections
