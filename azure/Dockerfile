# Cloud-only backend image.
#
# ~1.5 GB rather than the local image's 7.4 GB: no torch, no
# sentence-transformers, no pre-baked embedding model. Embeddings come from
# Azure OpenAI at runtime.
#
# Build from the REPOSITORY ROOT so azure/ and data/ are both in context:
#   docker build -f azure/Dockerfile -t nobel-rag-api:local .
#
# The ignore file is azure/Dockerfile.dockerignore, not azure/.dockerignore:
# the build context is the repo root, so Docker would read the context root's
# .dockerignore and never see a file inside azure/. BuildKit reads
# <dockerfile>.dockerignore in preference, which is what this relies on.

FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 PYTHONPATH=/app

COPY azure/requirements.txt ./azure/requirements.txt
RUN pip install --no-cache-dir -r azure/requirements.txt

COPY azure/ ./azure/
COPY data/ ./data/

# The index is built before the image and copied in, so the container starts
# serving immediately instead of embedding 276 chunks on boot.
#
# Thresholds are AZURE_-prefixed on purpose: the local deployment reads the
# unprefixed names, and python-dotenv writes into the process environment, so
# sharing names let one deployment silently override the other's gate.
# Values are measured, not guessed - see docs/superpowers/plans/
# azure-deployment/CALIBRATION.md.
ENV AZURE_STORAGE_DIR=/app/azure/storage \
    AZURE_DATA_DIR=/app/data \
    AZURE_MIN_COSINE=0.25 \
    AZURE_MIN_BM25=4.22

# Non-root: the container never needs to write outside /tmp and the SQLite
# metrics file, which lives under the app directory it owns.
RUN useradd --create-home --uid 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "azure.rag.api:app", "--host", "0.0.0.0", "--port", "8000"]
