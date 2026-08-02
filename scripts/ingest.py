"""Build the search index from the documents in the data directory."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.chunker import chunk_sections  # noqa: E402
from src.rag.config import Config  # noqa: E402
from src.rag.index import build_index  # noqa: E402
from src.rag.loaders import load_all  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = Config.load()

    sections = load_all(config.data_dir)
    chunks = chunk_sections(sections, config.chunk_max_chars, config.chunk_overlap)
    report = build_index(chunks, config.storage_dir, config.embedding_model)

    print(f"\nSections: {len(sections)}  Chunks: {report.chunk_count}")
    for name, count in sorted(report.per_file.items()):
        print(f"  {count:>4}  {name}")
    print(f"Completed in {report.seconds:.1f}s -> {config.storage_dir}")


if __name__ == "__main__":
    main()
