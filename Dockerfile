FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so first run does not wait on 1.1 GB.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('intfloat/multilingual-e5-base')"

COPY . .

# Bu imaj compose'da üç rolde kullanılır (ingest / api / rag); her biri kendi
# `command` değerini verir. Aşağıdaki varsayılan, imaj tek başına
# çalıştırıldığında anlamlı olan yoldur.
EXPOSE 7860 8000
CMD ["sh", "-c", "[ -f storage/chunks.jsonl ] || python scripts/ingest.py; \
    python gradio_app.py"]
