# Task 11: Backend Container Image

**Goal:** A slim image with no torch and no `sentence-transformers`, carrying
the prebuilt index.

**Files:**
- Create: `azure/requirements.txt`
- Create: `azure/Dockerfile`
- Create: `azure/.dockerignore`
- Create: `azure/tests/test_image_contents.py`

**Interfaces:**
- Consumes: everything from Tasks 1-10
- Produces: a local image tagged `nobel-rag-api:local`

---

## Why the index ships inside the image

Decision D11: ~276 chunks cost a fraction of a cent to embed once, the index
is ~12 MB, and baking it removes both the persistent-volume requirement and
the ingest delay from cold start. The trade-off — documents cannot change
without a rebuild — is acceptable for a fixed corpus.

- [ ] **Step 1: Write the dependency list**

Create `azure/requirements.txt`:

```
# Cloud-only: no torch, no sentence-transformers, no local model.
chromadb==0.5.23
rank-bm25==0.2.2
pypdf==5.1.0
python-docx==1.1.2
pandas==2.2.3
openpyxl==3.1.5
python-dotenv==1.0.1
requests==2.32.3

# Azure OpenAI
openai==1.59.6

# Agent graph (ADR-011)
langgraph==0.2.60
langchain-core==0.3.29

# HTTP API
fastapi==0.115.6
uvicorn[standard]==0.34.0

# Development only
pytest==8.3.4
pytest-cov==6.0.0
ruff==0.9.3
```

Confirm the FastAPI and uvicorn versions actually resolve on Python 3.11
before pinning; if pip objects, use the nearest working release and note it.

- [ ] **Step 2: Write the failing image test**

Create `azure/tests/test_image_contents.py`:

```python
"""The Azure image must not carry the local-model stack."""

from pathlib import Path

REQUIREMENTS = Path("azure/requirements.txt").read_text(encoding="utf-8")


def test_no_sentence_transformers():
    assert "sentence-transformers" not in REQUIREMENTS


def test_no_torch():
    assert "torch" not in REQUIREMENTS


def test_no_gradio():
    """The Azure deployment serves Next.js, not Gradio."""
    assert "gradio" not in REQUIREMENTS


def test_no_other_cloud_providers():
    """One provider only — Azure OpenAI."""
    assert "anthropic" not in REQUIREMENTS
    assert "google-genai" not in REQUIREMENTS


def test_source_has_no_local_embedding_imports():
    for path in Path("azure/rag").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "sentence_transformers" not in source, path
        assert "SentenceTransformer" not in source, path
```

- [ ] **Step 3: Run the tests**

Run: `pytest azure/tests/test_image_contents.py -v`
Expected: 5 passed (the requirements file now exists)

- [ ] **Step 4: Write the ignore file**

> ⚠️ **Controller ruling (pre-flight scan).** The build runs
> `docker build -f azure/Dockerfile .` from the repository root, so Docker
> reads the **context root's** `.dockerignore`. A file at
> `azure/.dockerignore` would be silently ignored — an earlier draft of this
> plan made that mistake. BuildKit (default since Docker 23) reads
> `<dockerfile-path>.dockerignore` in preference, so the file goes at
> `azure/Dockerfile.dockerignore`.
>
> **Do not modify the root `.dockerignore`** — the local image build depends
> on it. If BuildKit is unavailable, the root file applies instead and is an
> adequate fallback: it already excludes `.venv/`, `.git/`, `__pycache__/`,
> `docs/`, `AI Engineer/` and `storage/`. Note that its `storage/` pattern
> matches only the top-level directory, so `azure/storage` still reaches the
> image either way — which is what we want.

Create `azure/Dockerfile.dockerignore`:

```
**/__pycache__
**/*.pyc
.git
.venv
.env
azure/.env
node_modules
web/
azure/web/
notebooks
figures
docs
tests
azure/tests
AI Engineer/
storage/
rag-demo.zip
```

`azure/storage` is deliberately absent from this list — the built index must
reach the image. `storage/` matches only the top-level directory. Both `.env`
paths are ignored: secrets come from Container Apps, never from a layer.

Verify the index actually survives the ignore rules in Step 7.

- [ ] **Step 5: Write the Dockerfile**

Create `azure/Dockerfile`:

```dockerfile
# Cloud-only backend image.
#
# ~1.5 GB rather than the local image's 7.4 GB: no torch, no
# sentence-transformers, no pre-baked embedding model. Embeddings come from
# Azure OpenAI at runtime.
#
# Build from the REPOSITORY ROOT so azure/ and data/ are both in context:
#   docker build -f azure/Dockerfile -t nobel-rag-api:local .

FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 PYTHONPATH=/app

COPY azure/requirements.txt ./azure/requirements.txt
RUN pip install --no-cache-dir -r azure/requirements.txt

COPY azure/ ./azure/
COPY data/ ./data/

# The index is built before the image (Task 8) and copied in, so the container
# starts serving immediately instead of embedding 276 chunks on boot.
ENV STORAGE_DIR=/app/azure/storage DATA_DIR=/app/data

# Non-root: the container never needs to write outside /tmp.
RUN useradd --create-home --uid 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "azure.rag.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: Build the image**

```bash
docker build -f azure/Dockerfile -t nobel-rag-api:local .
```

- [ ] **Step 7: Verify the image size and contents**

```bash
docker images nobel-rag-api:local --format "{{.Size}}"
docker run --rm nobel-rag-api:local pip list 2>/dev/null | grep -iE "torch|sentence" || echo "clean: no torch, no sentence-transformers"
docker run --rm nobel-rag-api:local ls -la /app/azure/storage
```

Expected: a size well under 2 GB, `clean: …`, and `chroma/`, `bm25.pkl`,
`chunks.jsonl` present.

If the index is missing, Task 8 was not run before the build — run it and
rebuild.

- [ ] **Step 8: Run the container and verify it answers**

```bash
docker run --rm -d --name nobel-api-test -p 8001:8000 \
  -e INTERNAL_TOKEN=test \
  -e AZURE_OPENAI_ENDPOINT="https://foundry-lab-hbc26.openai.azure.com/" \
  -e AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
  -e MIN_COSINE="$MIN_COSINE" -e MIN_BM25="$MIN_BM25" \
  nobel-rag-api:local

sleep 8
curl -s localhost:8001/api/health
curl -s -X POST localhost:8001/api/ask \
  -H "X-Internal-Token: test" -H "X-Session-Id: s1" \
  -H "Content-Type: application/json" \
  -d '{"question":"Araç yakıt limiti ne kadar?"}'
docker stop nobel-api-test
```

Expected: `{"ok":true}` then an answer containing `1.500 TL/ay` with at least
one citation. Use the calibrated values from Task 8 for `MIN_COSINE` /
`MIN_BM25`.

- [ ] **Step 9: Confirm the local path is untouched**

```bash
git status --short src/ tests/ gradio_app.py docker-compose.yml Dockerfile
```

Expected: no output. Note the root `Dockerfile` is included in this check —
the Azure one is `azure/Dockerfile`.

- [ ] **Step 10: Quality gate**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 11: Commit**

```bash
git add azure/
git commit -m "feat(azure): add slim backend image with prebuilt index"
```

Record the measured image size in the commit body.
