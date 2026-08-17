"""Plain-text loader, used only by uploads.

The corpus has no .txt file, so this loader is absent from `SUPPORTED_SUFFIXES`
and the ingest path. Uploads accept it because users bring plain text.
"""

from pathlib import Path

from azure.rag.models import RawSection


def load_txt(path: Path) -> list[RawSection]:
    """Read a text file as one section.

    An uploaded file's encoding is not guaranteed. UTF-8 is tried first and
    cp1254 (Turkish Windows) second; anything still undecodable is replaced
    rather than raising, because losing a few characters beats rejecting the
    document outright.
    """
    raw = Path(path).read_bytes()
    for encoding in ("utf-8", "cp1254"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    return [RawSection(source_file=Path(path).name, doc_type="txt", text=text.strip())]
