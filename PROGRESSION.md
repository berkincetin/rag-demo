# PROGRESSION — Nerede Kaldık?

> Bu dosya her fazın sonunda güncellenir. Oturum başında **önce burayı**, sonra
> [MEMORY.md](MEMORY.md) dosyasını oku. Çalışma kuralları: [CLAUDE.md](CLAUDE.md).

**Son güncelleme:** 2026-08-06 — arayüz **Streamlit → Gradio** taşındı (port 8501 → **7860**),
Gemini tool şeması hatası düzeltildi, model `gemini-3.5-flash` oldu. 314 test, %95,07 kapsam.
**Aktif bölüm:** Her iki bölüm de tamamlandı. Bölüm 1 (14/14) + Sağlayıcı Merkezi
genişletmesi (17/17) + Bölüm 2 (11/11).
**Okunacak dosya:** `Bölüm 2 plan genel bakışı`
**Sıradaki somut adım:** Teslim paketi — ZIP'e `data/` ve `AI Engineer/bolum2_veriseti.xlsx` elle eklenmeli

> ✅ **Bölüm 2 tamamlandı** (2026-08-04). Kalan tek iş teslim paketinin hazırlanması.

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
| Sağlayıcı Merkezi genişletmesi | ✅ Tamamlandı — 2026-08-03 (17/17 task) |
| Bölüm 2 — Satış Analizi | ✅ Tamamlandı — 2026-08-04 (11/11 task) |

Legend: ⬜ başlamadı · 🔄 devam ediyor · ✅ tamamlandı · ⚠️ engellendi

---

## Bölüm 1 — RAG Agent

Plan: `docs/superpowers/plans/rag-agent/` — 14 task, her biri kendi commit'i ile kapanır.
Kavramsal arka plan: [docs/bolum1-rag/UYGULAMA-PLANI.md](docs/bolum1-rag/UYGULAMA-PLANI.md) (faz anlatısı).

| # | Task | Dosya | Durum | Testler | Commit |
|---|---|---|---|---|---|
| 1 | İskelet, config, modeller | `01` | ✅ | 6/6 ✅ %100 cov | `feat(config)` |
| 2 | Türkçe normalizasyon | `02` | ✅ | 7/7 ✅ %100 cov | `feat(normalize)` |
| 3 | PDF loader ⚠️ | `03` | ✅ | 5 unit + 3 integ ✅ | `feat(loaders)` |
| 4 | DOCX loader (tablolar!) ⚠️ | `04` | ✅ | 3 unit + 3 integ ✅ %100 cov | `feat(loaders)` |
| 5 | XLSX loader | `05` | ✅ | 3 unit + 3 integ ✅ %94 cov | `feat(loaders)` |
| 6 | Loader dispatch | `06` | ✅ | 2 unit + 3 integ ✅ %100 cov | `feat(loaders)` |
| 7 | Chunker + atıf etiketleri | `07` | ✅ | 11 unit + 3 integ ✅ %98 cov | `feat(chunker)` |
| 8 | İndeks + ingest | `08` | ✅ | 4 integ ✅ %100 cov | `feat(index)` |
| 9 | Hibrit retriever 🎯 | `09` | ✅ | 8 unit + 7 integ ✅ %100 cov | `feat(retriever)` |
| 10 | Tool'lar + promptlar | `10` | ✅ | 10 unit ✅ %94 cov | `feat(tools)` |
| 11 | LLM sağlayıcıları | `11` | ✅ | 6 unit + 2 skip (SDK yok) ✅ | `feat(llm)` |
| 12 | Agent döngüsü + güvenlik ağı | `12` | ✅ | 7 unit ✅ %100 cov + uçtan uca | `feat(agent)` |
| 13 | CLI + Streamlit | `13` | ✅ | 3 unit ✅ + CLI & UI elle doğrulandı | `feat(cli)` |
| 14 | Demo, Docker, README | `14` | ✅ | notebook 9 senaryo, 0 hata | `docs` |
| — | Doğrulama listesi | `99` | ✅ | 11/12 ✅, 1 kısmi (aşağıda) | — |

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

## Sağlayıcı Merkezi genişletmesi

Plan: `docs/superpowers/plans/saglayici-merkezi/` —
13 task + kullanıcı isteğiyle eklenen Task 14–17.
Tasarım: `spec`.

| # | Task | Durum | Not |
|---|---|---|---|
| 1 | Model kataloğu ve fiyatlandırma | ✅ | 5 model; yalnız Anthropic fiyatları dolu, diğerleri `null` |
| 2 | Oturum kapsamlı anahtar deposu | ✅ | Diske yazmama kaynak kodu testiyle korunuyor (ADR-012) |
| 3 | Token muhasebesi + Gemini istemcisi | ✅ | 4 sağlayıcının token alanları ayrı ayrı eşlendi |
| 4 | Metrik deposu (SQLite) | ✅ | Ölçülmeyen değer NULL; `priced_runs` ayrı raporlanıyor |
| 5 | LangGraph agent migrasyonu 🎯 | ✅ | `tests/test_agent.py` **değişmedi** (SHA256 aynı), 8/8 yeşil |
| 6 | Agent → metrik entegrasyonu | ✅ | Süre, token, maliyet, kapı, tur, onarım kaydediliyor |
| 7 | Ollama model yöneticisi | ✅ | `/api/tags`, akışlı `/api/pull`, `/api/delete` |
| 8 | Otomatik değerlendirme | ✅ | 13 vaka: atıf oranı, kaynak isabeti, ret doğruluğu |
| 9 | Arayüz: sağlayıcı ve model seçimi | ✅ | `st.form` — `text_input` blur sorunu |
| 10 | Arayüz: yerel model yönetimi | ✅ | İndirme ilerlemesi; toplam bilinmiyorsa yüzde uydurulmuyor |
| 11 | Arayüz: metrik paneli + sohbet rozeti | ✅ | Fiyatı bilinmeyen model grafikten çıkarılıp sayısı yazılıyor |
| 12 | Arayüz: değerlendirme karşılaştırması | ✅ | Atıf oranı → gecikme sıralaması |
| 13 | Kurulum, Docker otomatik pull, dokümanlar | ⚠️ | `setup.py` Ollama'yı kurmaz, komutu yazar. Docker DoD 2026-08-03'te **kısmen** doğrulandı: `ollama-init` 4,7 GB'ı kendi çekti, UI HTTP 200. Doğrularken bulunan kusur: `ollama` host portunu yayımlıyordu → yerel Ollama varken stack başlamıyordu, `expose`'a çevrildi. **Açık kalan:** konteyner içi smoke test bitmeden Docker daemon çöktü (16 GB'ta iki Ollama aynı modeli yükledi) — tekrar denemek için önce host Ollama durdurulmalı |
| 14 | Kaynak tüketimi ölçümü | ✅ | `resources.py`; `None` (ölçülemedi) ile `0` (CPU'da) ayrı |
| 15 | Token'ları ayrı ayrı göster | ✅ | Giriş/çıkış ayrı sütun + tepe CPU/RAM/GPU sütunları |
| 16 | Sohbet belleği 🎯 | ✅ | Kapı riski entegrasyon testiyle ölçüldü ve çözüldü |
| 17 | Kullanıcı adı ve kişiselleştirme | ✅ | Ad boşken prompt birebir eski hali; ad veritabanına yazılmıyor. Ad **yalnız sistem promptundayken etkisizdi** — tool sonucu mesajına taşındı, sonra ölçüldü: "Merhaba Berkin, …" (atıf=2, tool=1) |
| + | 🚨 Retrieval kararsızlığı (aralıklı test hatasından çıktı) | ✅ | HNSW `search_ef=10` varsayılanı doğru parçayı 8 koşunun 2'sinde ilk 20'ye hiç sokmuyordu → kapı altı kosinüs → geçerli soruya ret. `hnsw:search_ef=200`, indeks yeniden kuruldu, 10/10 doğru (ADR-016) |

---

## Bölüm 2 — Satış Analizi

Plan: `docs/superpowers/plans/analiz/` — 11 task,
her biri kendi commit'i ile kapandı.
Kavramsal arka plan (⚠️ uygulanmaz):
[docs/bolum2-analiz/UYGULAMA-PLANI.md](docs/bolum2-analiz/UYGULAMA-PLANI.md)

| # | Task | Durum | Not |
|---|---|---|---|
| 1 | İskelet, bağımlılıklar, geniş → tidy yükleme | ✅ | 374 seri × 124 ay doğrulandı |
| 2 | Temizleme ve veri kalitesi raporu 🚨 | ✅ | MF ölçek tespiti sabit pazar adı kullanmıyor; B/Ürün-FR birim fiyatı 8,32 TL |
| 3 | Türetilmiş ve analitik metrikler | ✅ | Birim fiyat `inf` üretmiyor; STL kısa seride `None` |
| 4 | Grafik stili ve figür yazıcı | ✅ | Türkçe sayı biçimi, sabit palet, mutlak `figures/` yolu |
| 5 | Temel tahminler + walk-forward | ✅ | Sızıntı testi; MAPE `inf` üretmiyor, WAPE/sMAPE yanında |
| 6 | Global LightGBM + MF ablasyonu | ✅ | Seri sınırı ve indeks etiketi sızıntıları testle yakalandı |
| 7 | Notebook: kalite raporu + A1, A2 | ✅ | Pay tablosu bulgularla uyumlu (A %12,4 · B %13,3 · C %6,1 · D %4,0) |
| 8 | Notebook: A3, A4 | ✅ | A4'te A Pazarı anlamlı (q ≈ 9×10⁻¹², Cliff δ = −0,49) |
| 9 | Notebook: A5, A6 | ✅ | Pay değişimi toplamı her pazarda 0; promosyon maliyeti 108,3 milyon TL |
| 10 | Notebook: A7 | ✅ | Dört pazarda üç farklı kazanan model; MF 4 pazarın 3'ünde iyileştiriyor |
| 11 | Kapanış: özet, figürler, README | ✅ | `Restart & Run All` hatasız, 52 hücre, 10 PNG |

**Kabul kriterleri (PRD §4) — 11/11 doğrulandı:** notebook baştan sona hatasız
çalışıyor · her görevde ≥1 grafik (toplam 10) · 7 teknik + 7 iş yorumu · A7'de 5 model ·
pazar bazında MAE/MAPE/RMSE/WAPE · MF ablasyonu · A4'te p-değeri + Cliff's delta +
FDR · MF ölçek düzeltmesi gerekçesiyle gösterilmiş · veri kalitesi raporu başta ·
kısa seriler açıkça raporlanmış · `requirements-analysis.txt` ile kuruluyor.

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
| 2026-08-02 | 1 | Docker uçtan uca test + sıcaklık düzeltmesi | `fix(llm)` + `docs` | smoke test 0 hata, 3 koşu birebir aynı | 🚨 Atıf kaybının kökü: `options.temperature` gönderilmiyordu (Ollama varsayılanı 0.8). `LLM_TEMPERATURE=0` + `CITATION_REPAIR`. `.dockerignore` ile imaj 8,98 → 7,37 GB |
| 2026-08-02 | + | Sağlayıcı Merkezi Task 1–4 | `feat(providers)` | — | Katalog, fiyat tablosu, oturum anahtarları, token muhasebesi, SQLite metrik deposu |
| 2026-08-02 | + | Sağlayıcı Merkezi Task 5–6 | `feat(agent)` | 8/8 agent testi değişmeden yeşil | LangGraph migrasyonu; `tests/test_agent.py` SHA256 aynı kaldı |
| 2026-08-02 | + | Sağlayıcı Merkezi Task 7–12 | `feat(ui)` | — | 4 yeni Streamlit sayfası + Ollama yöneticisi + otomatik değerlendirme |
| 2026-08-02 | + | Sağlayıcı Merkezi Task 13 | `feat(setup)` | — | `scripts/setup.py`, `ollama-init` servisi, ADR-011/012/013, README |
| 2026-08-03 | + | Sağlayıcı Merkezi Task 14–17 | `feat(agent)` | 247 passed, %95,05 cov | Kaynak ölçümü (`resources.py`), giriş/çıkış token sütunları, oturum belleği (`memory.py`), kullanıcı adı. Yol boyunca 5 kusur bulundu ve düzeltildi: `st.text_input` her rerun'da yeniden cevaplatıyordu, `inject_context` çıplak soruyla arıyordu, compose host portu çakışıyordu, ad yalnız sistem promptunda etkisizdi, **HNSW `search_ef` geçerli soruya ret ürettiriyordu (ADR-016)** |
| 2026-08-04 | 2 | Task 1–6 — analiz modülleri | `feat(load)` … `feat(forecast)` | 303 passed, %95,10 cov | Yükleme, temizleme (MF ölçeği), metrikler, grafik stili, walk-forward, LightGBM + ablasyon. İki sızıntı testle yakalandı: seri sınırı ve yinelenen indeks etiketi |
| 2026-08-04 | 2 | Task 7–11 — notebook A1–A7 + kapanış | `feat(notebook)` + `docs` | 306 passed, %95,04 cov | 52 hücre, `Restart & Run All` hatasız, 10 PNG. PRD §4'ün 11 maddesi tek tek doğrulandı. Yol boyunca 3 kusur bulundu: göreli veri yolu, göreli figür dizini, satır sayısına bakan mevsimsellik eşiği (`C/Ürün 1` için 0,99 mevsimsellik uyduruyordu) |
| 2026-08-07 | + | README üç katmanı anlatıyor + teslim paketi yenilendi | `docs` | 329 passed, %95 cov · ZIP'ten 320 passed | README'ye FastAPI uç tablosu, `web/` dosya haritası, altı servislik Docker tablosu ve proje ağacı eklendi. `rag-demo.zip` **88 → 189 dosya** (`scripts/package.py` ile). 🚨 İki kusur yalnızca paketi açıp **içinden** çalıştırınca görüldü: `env_file: .env` zorunluydu ve `.env` teslimde bulunmadığı için `docker compose up` hiç başlamıyordu (`required: false` ile düzeltildi); `api.py` kapsam listesinde değildi (%87 → %95) |
| 2026-08-07 | 2 | Bölüm 2 tek dosyalık teslim paketi | `docs` | notebook izole dizinde 0 hata, 10 grafik; sayılar `analiz.ipynb` ile birebir | `notebooks/analiz_full.ipynb` üretildi: `src/analysis/`'in beş modülü notebook içine alındı, başına `%pip install` hücresi kondu, hiçbir proje modülü import etmiyor. Analiz hücreleri kaynaktan **birebir** kopyalandı (betikle, elle değil). Kopyalanan fonksiyonların modüllerle aynı sonucu verdiği `assert_frame_equal` ile kanıtlandı (LightGBM dahil). `bolum2-analiz.zip` (2,9 MB): çalıştırılmış notebook + 10 PNG + veri + README + requirements. Mevcut kodlara dokunulmadı |
| 2026-08-17 | 3 | Aşama 1 — Arayüz yenileme + SSE + yükleme + özetleme (Task 1–12) | `feat(ui)` … `fix(uploads)` | azure: 163 passed, %93 cov · web: 36 passed, lint 0 hata | Yeni palet, konuşma kenar çubuğu, **gerçek token akışı** (`graph.py`'ye dokunulmadan), TTL'li disksiz yükleme, 10 mesaj özetleme. Yol boyunca 4 kusur bulundu: `azure/web/lib/` kök `.gitignore`'daki `lib/` kuralına takılıp **hiç commit edilmemişti** (taze klon derlenmezdi); özetleme ucu geçersiz isteği LLM'e dokunmadan reddetmiyordu; yüklenen belgenin alıntısı geçici dosya adını sızdırıyordu; `txt` için alıntı etiketi `— , s.None` basıyordu |
| 2026-08-17 | 3 | Aşama 1 canlıya alındı + Aşama 2 — Analiz sayfası | `fix(azure)` · `feat(web)` | azure: 174 passed, %93 cov · web: 48 passed, lint 0 hata · `next build` temiz | **Deploy:** iki imaj ACR'a push edildi, digest ile rollout. 🚨 Backend ilk revizyonda **çöktü**: `python-multipart` `azure/requirements.txt`'te yoktu — yerelde başka bir paketten geldiği için 163 testin tamamı geçiyordu, konteynerde `Form data requires python-multipart` ile import zamanında patladı. Testle yakalandı (`test_requirements.py`), düzeltildi, imaj yerel duman testinden geçirilip yeniden dağıtıldı. Canlı doğrulama: backend internete kapalı, üç yeni uç de 401, palet CSS'te, kullanıcı onayladı. **Aşama 2:** notebook → `analysis.json` + 10 PNG dışa aktarımı, `/analiz` rotası, 12 bölüm / 96 blok. Tema iki rota arasında `lib/theme.ts` ile paylaşıldı |
| 2026-08-17 | 3 | Aşama 3 — Model katalogu + ayarlar menüsü, Aşama 2+3 canlıya alındı | `feat(catalog)` | azure: 202 passed, %93,6 cov · web: 58 passed, lint 0 hata | 🚨 **Spec'in model listesi gerçeğe uymadı:** `list-models` katalogda *var mı* sorusunu yanıtlıyor, *kotan var mı* sorusunu değil. eastus'ta altı modelden yalnızca ikisinin kotası vardı (`gpt-5-mini`, `Phi-4-mini`); Cohere ailesi ve `text-embedding-3-large` sıfır kotalı çıktı. Kullanıcı kararıyla o dördü kapsam dışı bırakıldı — üç embedding indeksi ve rerank katmanı **yapılmadı**. 🚨 **Ölçülen kalite dürüstçe raporlandı:** aynı soruda gpt-4.1-mini 2 atıfla doğru cevap verirken gpt-5-mini 6 turda bile aramayı tekrarlayıp hiç cevap yazmadı, Phi-4-mini ise doğru kaynağı bulup [n] işaretini koymadı. İkisi de menüde uyarıyla gösteriliyor. Yol boyunca 1 kusur: `_agent_for` `base.tools` okuyordu, gerçek alan `base.toolbox` — stub'lı testler kaçırmıştı, gerçek `Agent`'a bakan test yakaladı. **Deploy:** iki imaj digest ile rollout, ikisi de Healthy/Running; palet + analiz stilleri + üç modelli katalog canlıda doğrulandı |
| 2026-08-18 | 3 | Model kalite kusuru giderildi (`final_answer` düğümü) | `fix(graph)` | azure: 213 passed, %93,9 cov · web: 58 passed | Aşama 3'te dürüstçe raporlanan iki kusurun **tek kök nedeni** çıktı: her iki model de araç şeması önlerindeyken metin üretmiyor — `gpt-5-mini` aramayı tekrarlıyor, `Phi-4-mini` boş yanıt döndürüyor (3/3 tekrarlandı). Toplanan bağlam doğruydu; grafik modelden hiç cevap istemiyordu. `graph.py`'ye `final_answer` düğümü eklendi: araç şeması geri çekilip aynı bağlamla bir tur daha isteniyor. Ölçüm — gpt-5-mini 0→3 atıf, Phi-4-mini 0→1 atıf, gpt-4.1-mini değişmedi (bu yola hiç uğramıyor). Yol boyunca 1 kusur daha: gpt-5-mini araçsız turda transkriptteki `[tool: search_documents]` yer tutucusunu taklit edip cevaba sızdırdı — satır bazlı temizlik eklendi. Canlıda üç model + reddetme yolu doğrulandı |
