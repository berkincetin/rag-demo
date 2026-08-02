FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so first run does not wait on 1.1 GB.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('intfloat/multilingual-e5-base')"

COPY . .

EXPOSE 8501
CMD ["sh", "-c", "[ -f storage/chunks.jsonl ] || python scripts/ingest.py; \
    streamlit run app.py --server.address=0.0.0.0"]
