# Verification Checklist

> Run this after [Task 14](14-demo-docker-readme.md), against `docs/bolum1-rag/PRD.md` section 6.

Run this after Task 14, against `docs/bolum1-rag/PRD.md` §6.

- [ ] `pip install -r requirements.txt` succeeds in a clean venv
- [ ] `python scripts/ingest.py` processes all 6 documents and reports chunk counts
- [ ] `streamlit run app.py` serves a working UI
- [ ] Demo notebook holds ≥5 question/answer pairs (8 planned), all with citations
- [ ] ≥1 "I don't know" scenario and ≥1 off-topic refusal are demonstrated
- [ ] ≥1 question answered per format: PDF, DOCX, XLSX
- [ ] ≥1 question answered from a **DOCX table** (`1.500 TL/ay`)
- [ ] Tool-call trace is visible in the demo
- [ ] README covers: 3-command setup, ASCII architecture, framework/model reasoning, challenges, limitations
- [ ] `docker compose up` brings the system up
- [ ] `pytest -q --cov --cov-fail-under=70` passes
- [ ] Delivery ZIP includes `data/` and runs from scratch
