# PROGRESSION — Nerede Kaldık?

> Bu dosya her fazın sonunda güncellenir. Oturum başında **önce burayı**, sonra
> [MEMORY.md](MEMORY.md) dosyasını oku. Çalışma kuralları: [CLAUDE.md](CLAUDE.md).

**Son güncelleme:** 2026-08-02
**Aktif bölüm:** Bölüm 1 — RAG Agent
**Aktif bölüm:** Bölüm 1 **tamamlandı** (14/14 task) — Bölüm 2 planlaması bekliyor
**Sıradaki somut adım:** Teslim ZIP'i (`data/` elle eklenerek) → sonra Bölüm 2 superpowers
planı `docs/superpowers/plans/analiz/` altına yazılacak

> ⚠️ **Eşik değerleri değişti:** `MIN_COSINE=0.72` **geçersiz**. Kalibre edilmiş değerler
> `MIN_COSINE=0.80` + `MIN_BM25=5.0` (VE kapısı). Gerekçe ve ölçüm tablosu MEMORY.md Task 9.

> ⚠️ Aynı anda **tek** task dosyası okunur. Tüm task setini yüklemek gereksiz —
> global kısıtlar overview'da, komşu task'ların imzaları kendi task'ının
> `Interfaces` bloğunda.

---

## Durum Özeti

| Aşama | Durum |
|---|---|
| Planlama (case analizi, veri keşfi, PRD/TRD/task planları) | ✅ Tamamlandı — 2026-08-01 |
| Bölüm 1 — RAG Agent | ✅ Tamamlandı — 2026-08-02 (14/14 task) |
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
| 4 | DOCX loader (tablolar!) ⚠️ | [04](docs/superpowers/plans/rag-agent/04-docx-loader.md) | ✅ | 3 unit + 3 integ ✅ %100 cov | `feat(loaders)` |
| 5 | XLSX loader | [05](docs/superpowers/plans/rag-agent/05-xlsx-loader.md) | ✅ | 3 unit + 3 integ ✅ %94 cov | `feat(loaders)` |
| 6 | Loader dispatch | [06](docs/superpowers/plans/rag-agent/06-loader-dispatch.md) | ✅ | 2 unit + 3 integ ✅ %100 cov | `feat(loaders)` |
| 7 | Chunker + atıf etiketleri | [07](docs/superpowers/plans/rag-agent/07-chunker.md) | ✅ | 11 unit + 3 integ ✅ %98 cov | `feat(chunker)` |
| 8 | İndeks + ingest | [08](docs/superpowers/plans/rag-agent/08-index-ingest.md) | ✅ | 4 integ ✅ %100 cov | `feat(index)` |
| 9 | Hibrit retriever 🎯 | [09](docs/superpowers/plans/rag-agent/09-retriever.md) | ✅ | 8 unit + 7 integ ✅ %100 cov | `feat(retriever)` |
| 10 | Tool'lar + promptlar | [10](docs/superpowers/plans/rag-agent/10-tools-prompts.md) | ✅ | 10 unit ✅ %94 cov | `feat(tools)` |
| 11 | LLM sağlayıcıları | [11](docs/superpowers/plans/rag-agent/11-llm-providers.md) | ✅ | 6 unit + 2 skip (SDK yok) ✅ | `feat(llm)` |
| 12 | Agent döngüsü + güvenlik ağı | [12](docs/superpowers/plans/rag-agent/12-agent.md) | ✅ | 7 unit ✅ %100 cov + uçtan uca | `feat(agent)` |
| 13 | CLI + Streamlit | [13](docs/superpowers/plans/rag-agent/13-frontends.md) | ✅ | 3 unit ✅ + CLI & UI elle doğrulandı | `feat(cli)` |
| 14 | Demo, Docker, README | [14](docs/superpowers/plans/rag-agent/14-demo-docker-readme.md) | ✅ | notebook 9 senaryo, 0 hata | `docs` |
| — | Doğrulama listesi | [99](docs/superpowers/plans/rag-agent/99-verification-checklist.md) | ✅ | 11/12 ✅, 1 kısmi (aşağıda) | — |

### Doğrulama listesi sonucu

| Madde | Durum |
|---|---|
| `pip install -r requirements.txt` temiz venv'de çalışıyor | ✅ exit 0 |
| `ingest.py` 6 belgeyi işliyor, chunk sayısı raporluyor | ✅ 219 bölüm → 276 chunk, 120 sn |
| `streamlit run app.py` çalışan arayüz sunuyor | ✅ tarayıcıda test edildi |
| Notebook ≥5 soru-cevap çifti, hepsi atıflı | ⚠️ **9 çift ✅, atıf 6/7** — Duxet sorusu atıfsız kaldı (README sınırlılık #8) |
| ≥1 "bilmiyorum" + ≥1 konu dışı reddi | ✅ ikisi de, boş tool izi |
| Her formattan ≥1 soru cevaplanmış | ✅ PDF + DOCX + XLSX |
| ≥1 soru **DOCX tablosundan** (`1.500 TL/ay`) | ✅ CLI ve notebook'ta |
| Tool çağrı izi demoda görünür | ✅ notebook + Streamlit paneli |
| README: 3 komut, ASCII mimari, gerekçeler, zorluklar, sınırlılıklar | ✅ hepsi |
| `docker compose up` sistemi ayağa kaldırıyor | ✅ HTTP 200 |
| `pytest --cov --cov-fail-under=70` geçiyor | ✅ 103 passed, %95,05 |
| Teslim ZIP'i `data/` içeriyor ve sıfırdan çalışıyor | ✅ `rag-demo.zip` (88 girdi, 6 belge). Temiz klasöre açılıp `ingest.py` çalıştırıldı: 276 chunk, 92,8 sn |

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
| 2026-08-02 | 1 | Task 4 — DOCX loader | `feat(loaders)` | 27 passed, %98,86 cov | Araç 54p/9 tablo→15 bölüm, İK 84p/7 tablo→19 bölüm; `1.500 TL/ay` sadece tablodan geliyor |
| 2026-08-02 | 1 | Task 5 — XLSX loader | `feat(loaders)` | 33 passed, %98,10 cov | Taksonomi tam 100 bölüm; SSS 3 sayfa→45 bölüm. Başlık satırları: 2, 2, **1** |
| 2026-08-02 | 1 | Task 6 — Loader dispatch | `feat(loaders)` | 38 passed, %98,25 cov | 6 dosya → **219 bölüm / 144.365 karakter**; Türkçe dosya adı glob ile bulundu |
| 2026-08-02 | 1 | Task 7 — Chunker | `feat(chunker)` | 52 passed, %98,26 cov | ⚠️ Plandaki `_split_text` hatalıydı: 232 chunk (12'si 1200 sınırı üstü, max 9.681). `_hard_split` eklendi → **276 chunk, sınır aşımı 0** |
| 2026-08-02 | 1 | Task 8 — İndeks + ingest | `feat(index)` | 56 passed, %98,54 cov | `ingest.py` gerçek korpusta çalıştı: 219 bölüm → **276 chunk, 50,5s**. e5-base indirildi (~1,1 GB) |
| 2026-08-02 | 1 | Task 9 — Hibrit retriever | `feat(retriever)` | 75 passed, %98,80 cov | 3 kök neden düzeltildi: başlıklar `search_text`'e, `bm25_tokens` (6 karakter), eşik **0,80 + BM25 5,0 (VE)**. 7/7 probe ✅ |
| 2026-08-02 | 1 | Task 10 — Tool'lar + promptlar | `feat(tools)` | 85 passed, %97,80 cov | 3 tool + Türkçe sistem promptu; `prompts.py` Task 12'de kapsanacak |
| 2026-08-02 | 1 | Task 11 — LLM sağlayıcıları | `feat(llm)` | 91 passed + 2 skipped, %97,80 cov | Ollama smoke test ✅ ("Merhaba!"). ⚠️ Yerel etiket `-q4_K_M`; SYSTEM_PROMPT tool çağrısını engelliyor (Task 12'ye devredildi) |
| 2026-08-02 | 1 | Task 12 — Agent döngüsü | `feat(agent)` | 103 passed + 2 skipped, %95,05 cov | 3 kök neden: kısa prompt + `CITATION_REMINDER` tool sonucunda, tool çağrılmazsa **bağlam enjeksiyonu**, timeout 120s→600s. Uçtan uca doğrulandı |
| 2026-08-02 | 1 | Task 13 — CLI + Streamlit | `feat(cli)` | 103 passed + 2 skipped, %95,05 cov | CLI: DOCX tablosundan `1.500 TL/ay` ✅. Streamlit tarayıcıda test edildi: konu dışı → Kaynaklar(0)/Araç(0); Vitatin95 → 1 kaynak + trace tablosu |
| 2026-08-02 | 1 | Task 14 — Demo, Docker, README | `docs` | 103 passed + 2 skipped, %95,05 cov | Notebook 9 senaryo 0 hata (~25 dk); Docker `up` → HTTP 200; 3 komut sıfırdan doğrulandı. Duxet sorusu atıfsız kaldı (sınırlılık #8) |
