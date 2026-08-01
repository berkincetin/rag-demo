# PROGRESSION — Nerede Kaldık?

> Bu dosya her fazın sonunda güncellenir. Oturum başında **önce burayı**, sonra
> [MEMORY.md](MEMORY.md) dosyasını oku. Çalışma kuralları: [CLAUDE.md](CLAUDE.md).

**Son güncelleme:** 2026-08-01
**Aktif bölüm:** Bölüm 1 — RAG Agent
**Aktif faz:** Faz 0 — Proje İskeleti (henüz başlamadı)
**Sıradaki somut adım:** `docs/bolum1-rag/UYGULAMA-PLANI.md` → Faz 0, Adım 0.1
(klasör yapısını oluştur)

---

## Durum Özeti

| Aşama | Durum |
|---|---|
| Planlama (case analizi, veri keşfi, PRD/TRD/planlar) | ✅ Tamamlandı — 2026-08-01 |
| Bölüm 1 — RAG Agent | ⬜ Başlamadı (0/7 faz) |
| Bölüm 2 — Satış Analizi | ⬜ Başlamadı (0/7 faz) — Bölüm 1 teslim edilebilir olmadan başlanmaz |

Legend: ⬜ başlamadı · 🔄 devam ediyor · ✅ tamamlandı · ⚠️ engellendi

---

## Bölüm 1 — RAG Agent

Plan: [docs/bolum1-rag/UYGULAMA-PLANI.md](docs/bolum1-rag/UYGULAMA-PLANI.md)

| Faz | Ad | Durum | Testler | Commit | Not |
|---|---|---|---|---|---|
| 0 | Proje İskeleti | ⬜ | — | — | |
| 1 | Belge Yükleme (loaders) ⚠️ | ⬜ | — | — | En riskli faz |
| 2 | Chunking ve İndeks | ⬜ | — | — | |
| 3 | Retrieval 🎯 | ⬜ | — | — | Doğruluğun kaynağı |
| 4 | LLM ve Agent | ⬜ | — | — | |
| 5 | Arayüzler (CLI + Streamlit) | ⬜ | — | — | |
| 6 | Demo, Docker, Dokümantasyon | ⬜ | — | — | |

### Faz Detay Kontrol Listeleri

**Faz 0 — Proje İskeleti**
- [ ] 0.1 Klasör yapısı (`src/rag/`, `loaders/`, `scripts/`, `tests/`, `notebooks/`, `data/`)
- [ ] 0.2 6 belge `AI Engineer/Rag_Agent/` → `data/` kopyalandı
- [ ] 0.3 `requirements.txt` (sürüm pinli)
- [ ] 0.4 `.env.example` + `config.py`
- [ ] 0.5 `.gitignore` güncellendi (`storage/`, `.env`, `data/`, `AI Engineer/`, `.venv/`)
- [ ] 0.6 `models.py` dataclass'ları
- [ ] Testler yazıldı ve geçti · [ ] Quality gate · [ ] Commit + push · [ ] PROGRESSION/MEMORY güncellendi

**Faz 1 — Belge Yükleme**
- [ ] 1.1 `normalize.py` — `fold_tr`
- [ ] 1.2 `loaders/pdf_loader.py` — bölüm + sayfa, dipnot yanlış pozitif filtresi
- [ ] 1.3 `loaders/docx_loader.py` — başlık hiyerarşisi + **tablolar**
- [ ] 1.4 `loaders/xlsx_loader.py` — otomatik başlık satırı tespiti
- [ ] 1.5 `loaders/__init__.py` — `load_all(data_dir)` glob taraması
- [ ] Unit + integration testler · [ ] Quality gate · [ ] Commit + push · [ ] Dosyalar güncellendi

**Faz 2 — Chunking ve İndeks**
- [ ] 2.1 `chunker.py`
- [ ] 2.2 `index.py` (Chroma + BM25 + `chunks.jsonl`)
- [ ] 2.3 `scripts/ingest.py`
- [ ] Unit + integration testler · [ ] Quality gate · [ ] Commit + push · [ ] Dosyalar güncellendi

**Faz 3 — Retrieval**
- [ ] 3.1 `retriever.py` — hibrit BM25 + dense, RRF
- [ ] 3.2 Eşik kalibrasyonu (8 geçerli soru geçer, 5 konu dışı geçmez)
- [ ] Unit + integration testler · [ ] Quality gate · [ ] Commit + push · [ ] Dosyalar güncellendi

**Faz 4 — LLM ve Agent**
- [ ] 4.1 `llm.py` — provider soyutlaması (varsayılan Ollama)
- [ ] 4.2 `tools.py` — 3 tool
- [ ] 4.3 `prompts.py`
- [ ] 4.4 `agent.py` — tool döngüsü + 3 katmanlı güvenlik ağı
- [ ] Unit + integration testler (LLM mock'lu) · [ ] Quality gate · [ ] Commit + push · [ ] Dosyalar güncellendi

**Faz 5 — Arayüzler**
- [ ] 5.1 `cli.py`
- [ ] 5.2 `app.py` — Streamlit (kaynak paneli + tool izi)
- [ ] Unit + integration testler · [ ] Quality gate · [ ] Commit + push · [ ] Dosyalar güncellendi

**Faz 6 — Demo, Docker, Dokümantasyon**
- [ ] 6.1 `notebooks/demo.ipynb` — 8 senaryo
- [ ] 6.2 `Dockerfile` + `docker-compose.yml`
- [ ] 6.3 `README.md` — 3 komut, ASCII mimari, gerekçeler, zorluklar, sınırlılıklar
- [ ] 6.4 Teslim ZIP'i — ⚠️ `data/` git'te olmadığı için **elle eklenmeli**
- [ ] Quality gate · [ ] Commit + push · [ ] Dosyalar güncellendi

---

## Bölüm 2 — Satış Analizi

Plan: [docs/bolum2-analiz/UYGULAMA-PLANI.md](docs/bolum2-analiz/UYGULAMA-PLANI.md)
**Ön koşul:** Bölüm 1 Faz 6 tamamlanmış olmalı.

| Faz | Ad | Durum | Testler | Commit | Not |
|---|---|---|---|---|---|
| 0 | İskelet | ⬜ | — | — | |
| 1 | Yükleme ve Temizleme ⚠️ | ⬜ | — | — | MF ölçek düzeltmesi kritik |
| 2 | Notebook Omurgası + Veri Kalitesi Raporu | ⬜ | — | — | |
| 3 | Görev A1–A3 | ⬜ | — | — | |
| 4 | Görev A4–A6 | ⬜ | — | — | İstatistik ağırlıklı |
| 5 | Görev A7 — Tahmin | ⬜ | — | — | |
| 6 | Kapanış | ⬜ | — | — | |

### Faz Detay Kontrol Listeleri

**Faz 0 — İskelet**
- [ ] 0.1 `src/analysis/`, `figures/` klasörleri
- [ ] 0.2 `requirements-analysis.txt`
- [ ] 0.3 Veri yolu konfigürasyonu
- [ ] 0.4 UTF-8 notu

**Faz 1 — Yükleme ve Temizleme** ⚠️
- [ ] 1.1 `load.py` — wide → tidy (374 seri × 124 ay doğrulaması)
- [ ] 1.2 `clean.py` — 🚨 MF ölçek tespiti + düzeltmesi (B/Ürün-FR fiyatı pozitif olmalı)
- [ ] 1.3 `clean.py` — ürün adı normalizasyonu, MF kırpma, iade bayrağı, seri kırpma
- [ ] 1.4 `metrics.py` — Net Kutu, Birim Fiyat, pazar payı, HHI, YoY
- [ ] Unit + integration testler · [ ] Quality gate · [ ] Commit + push · [ ] Dosyalar güncellendi

**Faz 2 — Notebook Omurgası**
- [ ] 2.1 Notebook iskeleti (0. Veri Kalitesi + 7 görev)
- [ ] 2.2 `plots.py` ortak stil
- [ ] 2.3 Veri Kalitesi Raporu bölümü

**Faz 3 — A1–A3**
- [ ] 3.1 A1 Satış performansı ve ürün kırılımı
- [ ] 3.2 A2 Pazar yapısı ve rekabet pozisyonu
- [ ] 3.3 A3 Mevsimsellik

**Faz 4 — A4–A6**
- [ ] 4.1 A4 MF'in satışlara etkisi (olay çalışması + FDR)
- [ ] 4.2 A5 Rakip karşılaştırması
- [ ] 4.3 A6 Birim fiyat ve promosyon maliyeti

**Faz 5 — A7 Tahmin**
- [ ] 5.1 `forecast.py` baseline'lar + walk-forward
- [ ] 5.2 Global LightGBM + MF ablasyonu
- [ ] 5.3 Notebook A7 bölümü (pazar bazında MAE/MAPE/RMSE tablosu)

**Faz 6 — Kapanış**
- [ ] 6.1 Notebook `Restart & Run All` temiz
- [ ] 6.2 Her görevde teknik + iş yorumu
- [ ] 6.3 Figürler `figures/` altına PNG
- [ ] 6.4 Yönetici özeti
- [ ] 6.5 `tests/test_analysis.py` tam yeşil
- [ ] 6.6 README Bölüm 2 adımları

---

## Faz Kapanış Kaydı

Her faz kapandığında buraya bir satır eklenir.

| Tarih | Bölüm | Faz | Commit | Test sonucu | Not |
|---|---|---|---|---|---|
| 2026-08-01 | — | Planlama | — | — | PRD/TRD/planlar + CLAUDE.md/PROGRESSION/MEMORY oluşturuldu |
