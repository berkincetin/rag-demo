"""Build the Azure index from the documents in data/.

Run from the repository root:  python -m azure.scripts.ingest

Note on where this runs: the Chroma on-disk format is version-specific, and
`azure/requirements.txt` pins chromadb 0.5.23. An index built by a different
chromadb (this repo's dev environment has 1.0.9) fails to load inside the
image with `KeyError: '_type'`. Build the index with the same version the
container runs — the Dockerfile does this during the build.
"""

import sys

from azure.rag.chunker import chunk_sections
from azure.rag.config import AzureConfig
from azure.rag.embedder import AzureOpenAIEmbedder
from azure.rag.index import build_index
from azure.rag.loaders import load_all


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    config = AzureConfig.load()

    sections = load_all(config.data_dir)
    chunks = chunk_sections(sections)
    report = build_index(chunks, config.storage_dir, AzureOpenAIEmbedder(config))

    print(f"{len(sections)} bolum -> {report.chunk_count} parca, {report.seconds:.1f} sn")
    for source_file, count in sorted(report.per_file.items()):
        print(f"  {source_file}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
