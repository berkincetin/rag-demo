# Task 14: Demo notebook, Docker, and README

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 13](13-frontends.md)
**Next:** [Verification Checklist](99-verification-checklist.md)

---

**Files:**
- Create: `notebooks/demo.ipynb`, `Dockerfile`, `docker-compose.yml`, `README.md`

**Interfaces:**
- Consumes: everything built so far
- Produces: the case deliverables

- [ ] **Step 1: Build the demo notebook with all eight scenarios**

Cells, in order: setup and index load; then one cell per question printing the question, the answer, the citations, and the tool trace. The eight questions come from `docs/bolum1-rag/PRD.md` §7:

1. `Yıllık izin talebimi nasıl yaparım?` (XLSX)
2. `İşe alım süreci kaç aşamadan oluşur?` (DOCX headings)
3. `Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?` (**DOCX table**)
4. `Havuz aracı nasıl talep edilir?` (DOCX procedure)
5. `Aksef 500 mg'ın kontrendikasyonları nelerdir?` (**PDF section + page**)
6. `Duxet'in gebelikte kullanımı hakkında ne yazıyor?` (multi-page PDF)
7. `Vitatin95 ürününün terapötik sistemi ve ürün müdürü kim?` (XLSX taxonomy)
8. `Şirketin 2027 yılı kâr hedefi nedir?` (**"bilmiyorum"**) and `Bugün hava nasıl olacak?` (**off-topic**)

Add a final cell printing the retrieval score distribution (cosine and BM25 for each of the eight questions plus five off-topic ones) as the calibration evidence.

- [ ] **Step 2: Run the notebook end to end and verify**

Run: `jupyter nbconvert --to notebook --execute notebooks/demo.ipynb --inplace`
Expected: exit 0. Then confirm by reading the output: at least 5 question/answer pairs (there are 8), every answer carries a citation naming a real file, question 8 produces the no-info answer, the off-topic question produces the refusal with an empty tool trace, and at least one answer per format (PDF, DOCX, XLSX) is present.

- [ ] **Step 3: Write `Dockerfile`**

```dockerfile
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
```

- [ ] **Step 4: Write `docker-compose.yml`**

```yaml
services:
  rag:
    build: .
    ports: ["8501:8501"]
    env_file: .env
    environment:
      OLLAMA_BASE_URL: http://ollama:11434
    volumes:
      - ./data:/app/data
      - ./storage:/app/storage
    depends_on: [ollama]

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: ["ollama:/root/.ollama"]

volumes:
  ollama: {}
```

- [ ] **Step 5: Verify Docker brings the system up**

Run: `docker compose up --build`
Expected: `localhost:8501` serves the app and answers a question. Note in `MEMORY.md` that `ollama pull qwen2.5:7b-instruct` must be run inside the ollama container on first use.

- [ ] **Step 6: Write `README.md` covering every case §1.4.3 requirement**

Required sections:
- **Three-command setup:** `pip install -r requirements.txt` → `python scripts/ingest.py` → `streamlit run app.py`
- **ASCII architecture diagram** (copy from `docs/bolum1-rag/TRD.md` §1)
- **Framework and model choices with reasoning** (summarize ADR-001 through ADR-004 and ADR-007: why no LangChain, why e5-base, why Chroma, why hybrid retrieval, why Ollama by default)
- **Challenges and how they were solved** — the five measured problems from `docs/01-veri-kesif-bulgulari.md`: Turkish/ASCII spelling inconsistency across formats, DOCX tables invisible to `document.paragraphs`, XLSX headers on row 3, PDF footnotes masquerading as section headings, a Turkish character in a source filename
- **Limitations and improvement ideas** (copy from `docs/bolum1-rag/TRD.md` §9)
- **Demo examples** with a link to `notebooks/demo.ipynb`
- **Windows note:** set `PYTHONIOENCODING=utf-8` for Turkish console output
- **Delivery note:** `data/` is gitignored; the ZIP must include it

- [ ] **Step 7: Verify the README's three commands in a clean environment**

Run, in a fresh virtualenv with `storage/` deleted:
```bash
pip install -r requirements.txt
python scripts/ingest.py
streamlit run app.py
```
Expected: all three succeed with no undocumented step in between.

- [ ] **Step 8: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add notebooks Dockerfile docker-compose.yml README.md
git commit -m "docs: add demo notebook, Docker setup, and README"
```

- [ ] **Step 9: Assemble the delivery ZIP**

```bash
git archive --format=zip --output=rag-demo.zip HEAD
```
Then **add `data/` manually** — it is gitignored, and `ingest.py` cannot run without it. Verify by extracting the ZIP into a clean directory and running the three README commands.
