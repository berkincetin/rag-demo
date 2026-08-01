# PROGRESSION — Nerede Kaldık?

> Bu dosya her fazın sonunda güncellenir. Oturum başında **önce burayı**, sonra
> [MEMORY.md](MEMORY.md) dosyasını oku. Çalışma kuralları: [CLAUDE.md](CLAUDE.md).

**Son güncelleme:** 2026-08-02
**Aktif bölüm:** Bölüm 1 — RAG Agent
**Aktif task:** Task 4 — DOCX loader (başlık hiyerarşisi + tablolar) (henüz başlamadı)
**Okunacak dosya:** [docs/superpowers/plans/rag-agent/00-overview.md](docs/superpowers/plans/rag-agent/00-overview.md)
+ [04-docx-loader.md](docs/superpowers/plans/rag-agent/04-docx-loader.md)
**Sıradaki somut adım:** Task 4 / Step 1 — `rows_to_markdown` için kırmızı testi yaz

> ⚠️ Aynı anda **tek** task dosyası okunur. Tüm task setini yüklemek gereksiz —
> global kısıtlar overview'da, komşu task'ların imzaları kendi task'ının
> `Interfaces` bloğunda.

---

## Durum Özeti

| Aşama | Durum |
|---|---|
| Planlama (case analizi, veri keşfi, PRD/TRD/task planları) | ✅ Tamamlandı — 2026-08-01 |
| Bölüm 1 — RAG Agent | 🔄 Devam ediyor (3/14 task) |
| Bölüm 2 — Satış Analizi | ⬜ Başlamadı (0/7 faz) — Bölüm 1 teslim edilebilir olmadan başlanmaz |

Legend: ⬜ başlamadı · 🔄 devam ediyor · ✅ tamamlandı · ⚠️ engellendi

---

## Bölüm 1 — RAG Agent

Plan: [docs/superpowers/plans/rag-agent/](docs/superpowers/plans/rag-agent/) — 14 task, her biri kendi commit'i ile kapanır.
Kavramsal arka plan: [docs/bolum1-rag/UYGULAMA-PLANI.md](docs/bolum1-rag/UYGULAMA-PLANI.md) (faz anlatısı).

| # | Task | Dosya | Durum | Testler | Commit |
|---|---|---|---|---|---|
| 1 | İskelet, config, modeller | [01](docs/superpowers/plans/rag-agent/01-skeleton-config-models.md) | ✅ | 6/6 ✅ %100 cov | `feat(config)` |
| 2 | Türkçe normalizasyon | [02](docs/superpowers/plans/rag-agent/02-normalize.md) | ✅ | 7/7 ✅ %100 cov | `feat(normalize)` |
| 3 | PDF loader ⚠️ | [03](docs/superpowers/plans/rag-agent/03-pdf-loader.md) | ✅ | 5 unit + 3 integ ✅ | `feat(loaders)` |
| 4 | DOCX loader (tablolar!) ⚠️ | [04](docs/superpowers/plans/rag-agent/04-docx-loader.md) | ⬜ | — | — |
| 5 | XLSX loader | [05](docs/superpowers/plans/rag-agent/05-xlsx-loader.md) | ⬜ | — | — |
| 6 | Loader dispatch | [06](docs/superpowers/plans/rag-agent/06-loader-dispatch.md) | ⬜ | — | — |
| 7 | Chunker + atıf etiketleri | [07](docs/superpowers/plans/rag-agent/07-chunker.md) | ⬜ | — | — |
| 8 | İndeks + ingest | [08](docs/superpowers/plans/rag-agent/08-index-ingest.md) | ⬜ | — | — |
| 9 | Hibrit retriever 🎯 | [09](docs/superpowers/plans/rag-agent/09-retriever.md) | ⬜ | — | — |
| 10 | Tool'lar + promptlar | [10](docs/superpowers/plans/rag-agent/10-tools-prompts.md) | ⬜ | — | — |
| 11 | LLM sağlayıcıları | [11](docs/superpowers/plans/rag-agent/11-llm-providers.md) | ⬜ | — | — |
| 12 | Agent döngüsü + güvenlik ağı | [12](docs/superpowers/plans/rag-agent/12-agent.md) | ⬜ | — | — |
| 13 | CLI + Streamlit | [13](docs/superpowers/plans/rag-agent/13-frontends.md) | ⬜ | — | — |
| 14 | Demo, Docker, README | [14](docs/superpowers/plans/rag-agent/14-demo-docker-readme.md) | ⬜ | — | — |
| — | Doğrulama listesi | [99](docs/superpowers/plans/rag-agent/99-verification-checklist.md) | ⬜ | — | — |

**Bağımlılık zinciri:** 1 → 2 → {3, 4, 5} → 6 → 7 → 8 → 9 → {10, 11} → 12 → 13 → 14

<details>
<summary>⚠️ Eski faz bazlı kontrol listesi — UYGULANMAZ, sadece kavramsal referans</summary>

> Bu liste superpowers task planından **önce** yazıldı. Adım numaraları (Faz 1.2 gibi)
> geçersizdir; uygulama yalnızca yukarıdaki 14 task üzerinden yürür. Çakışma olursa
> task dosyası kazanır. Burada tutulma sebebi: fazların **neden** bu sırada olduğunu
> anlatan gerekçe.


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

</details>

---

## Bölüm 2 — Satış Analizi

**Plan durumu:** ⏳ Superpowers task planı **henüz yazılmadı.** Bölüm 1 (Task 14) bittikten
sonra `docs/superpowers/plans/analiz/` altına yazılacak — şimdi yazmak, eşik kalibrasyonu
gibi henüz bilinmeyen çıktıları tahmine dayandırırdı.

Kavramsal arka plan (⚠️ uygulanmaz):
[docs/bolum2-analiz/UYGULAMA-PLANI.md](docs/bolum2-analiz/UYGULAMA-PLANI.md)

**Ön koşul:** Bölüm 1 Task 14 tamamlanmış olmalı.

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

| Tarih | Bölüm | Task | Commit | Test sonucu | Not |
|---|---|---|---|---|---|
| 2026-08-01 | — | Planlama | — | — | PRD/TRD/planlar + CLAUDE.md/PROGRESSION/MEMORY oluşturuldu |
| 2026-08-02 | 1 | Task 1 — İskelet, config, modeller | `feat(config)` | 6 passed, %100 cov | `.venv` kuruldu (13 paket), 6 belge `data/` altına kopyalandı |
| 2026-08-02 | 1 | Task 2 — Türkçe normalizasyon | `feat(normalize)` | 13 passed, %100 cov | `fold_tr` gerçek korpusta doğrulandı: TR sorgu → ASCII DOCX eşleşiyor |
| 2026-08-02 | 1 | Task 3 — PDF loader | `feat(loaders)` | 21 passed, %98 cov | Aksef 12s→20 bölüm, Duxet 24s→20 bölüm; 8+13 yanlış pozitif elendi |
