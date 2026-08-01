# Uygulama Planı — Bölüm 1: RAG Tabanlı AI Agent

Adım adım yapılacaklar. Her adımın **Bitti Tanımı (DoD)** var; bir adım DoD'si
sağlanmadan bir sonrakine geçilmez. Toplam tahmini süre: **~14–18 saat**.

Faz sırası, riski en erken düşürecek şekilde seçildi: veri okuma (en çok sürpriz burada)
→ retrieval (doğruluğun kaynağı) → LLM (dışa bağımlı) → arayüz/paketleme (en düşük risk).

---

## Faz 0 — Proje İskeleti (~1 saat)

| Adım | İş | DoD |
|---|---|---|
| 0.1 | Klasör yapısını oluştur (TRD §2) | `src/rag/`, `src/rag/loaders/`, `scripts/`, `tests/`, `notebooks/`, `data/`, `storage/` mevcut |
| 0.2 | 6 belgeyi `AI Engineer/Rag_Agent/` → `data/` kopyala | `data/` içinde 6 dosya; orijinal klasör değişmedi |
| 0.3 | `requirements.txt` (TRD §6, sürüm pinli) | Temiz venv'de `pip install -r requirements.txt` hatasız |
| 0.4 | `.env.example` + `config.py` (dataclass, `python-dotenv`) | `Config.load()` tüm alanları varsayılanlarla döndürüyor |
| 0.5 | `.gitignore`'a `storage/`, `.env`, `data/` ekle | `git status` temiz |
| 0.6 | `models.py` — `RawSection`, `Chunk`, `SearchHit`, `Answer` | Import ediliyor, tip ipuçları tam |

---

## Faz 1 — Belge Yükleme (~4 saat) ⚠️ En yüksek riskli faz

Bulgular dosyasındaki §1.2–§1.6 sorunlarının tamamı burada çözülür.

### 1.1 `normalize.py` (~30 dk)
- `fold_tr(s)`: Türkçe eşlemeler → NFKD → casefold → whitespace sıkıştırma (TRD §4.4).
- `clean_text(s)`: satır sonu normalizasyonu, çoklu boşluk, kırık tire birleştirme.
- **DoD:** `test_normalize.py` yeşil — `fold_tr("İnsan Kaynakları") == fold_tr("Insan Kaynaklari")`.

### 1.2 `loaders/pdf_loader.py` (~1,5 saat)
- Sayfa sayfa metin çıkarımı; `(page_no, line)` akışı.
- Bölüm regex + **KÜB beyaz listesi + monoton artış** filtresi (TRD §4.1).
- Sayfa üst/alt bilgisi temizliği (`1/12` deseni).
- Bölüm bulunamazsa sayfa-bazlı fallback.
- **DoD:**
  - Aksef → ≥20 bölüm, Duxet → ≥20 bölüm.
  - `4.3 Kontrendikasyonlar` Aksef'te `page_start == 3`.
  - Duxet'te `7 Plasebodan istatistiksel olarak...` bölüm olarak **çıkmıyor**.
  - Her `RawSection.text` boş değil.

### 1.3 `loaders/docx_loader.py` (~1,5 saat)
- `document.element.body` üzerinden paragraf **ve tabloları belge sırasına göre** dolaş.
- `p.style` `None` koruması (`getattr`).
- Heading 1/2 hiyerarşisi → `section_path`.
- `List Paragraph` → `- ` madde işareti.
- Tablo → Markdown tablosu, ait olduğu bölümün metnine ekleme.
- **DoD:**
  - `arac_kullanim_proseduru.docx` çıktısında `1.500 TL/ay` metni var (**US-3 kanıtı**).
  - `ik_surecleri_politikası.docx` → ≥8 farklı `section_path`.
  - Her iki belgede de tüm tablolar (7 + 9 = 16) çıktıya girmiş.

### 1.4 `loaders/xlsx_loader.py` (~1 saat)
- Otomatik başlık satırı tespiti (TRD §4.3).
- Sayfa başına chunk stratejisi; SSS'in 3 sayfası ayrı ayrı işlenir.
- Taksonomi: 15 alan `Alan: Değer` serileştirmesi.
- **DoD:**
  - Taksonomiden tam **100** `RawSection`.
  - SSS'ten 3 sayfanın toplamı ≥40 `RawSection`.
  - `Vitatin95` bir chunk metninde geçiyor; `SORU:`/`CEVAP:` yapısı korunmuş.

### 1.5 `loaders/__init__.py` — `load_all(data_dir)` (~30 dk)
- `glob` ile tarama (dosya adları koda gömülmez — bulgular §1.6).
- Uzantıya göre doğru loader'a yönlendirme; bilinmeyen uzantı uyarı ile atlanır.
- **DoD:** 6 dosyanın tamamı işleniyor; toplam `RawSection` sayısı loglanıyor.

---

## Faz 2 — Chunking ve İndeks (~2,5 saat)

### 2.1 `chunker.py` (~1 saat)
- `RawSection` → `Chunk`; `MAX_CHARS=1200`, `OVERLAP=150`, paragraf sınırı önceliği.
- XLSX satırları **bölünmez**.
- `search_text = fold_tr(text)`, `citation_label` üretimi (TRD §4.5).
- **DoD:** `test_chunker.py` yeşil; toplam chunk sayısı 250–450 aralığında; hiçbir chunk
  1200+`OVERLAP` karakteri aşmıyor; her chunk'ın `citation_label`'ı boş değil.

### 2.2 `index.py` (~1 saat)
- Embedding modeli yükleme (e5 `passage:` öneki).
- Chroma `PersistentClient`, koleksiyon reset + batch ekleme.
- BM25 indeksi kurulumu + pickle.
- `chunks.jsonl` yazımı.
- **DoD:** `storage/` altında `chroma/`, `bm25.pkl`, `chunks.jsonl` oluşuyor;
  ikinci kez çalıştırıldığında chunk sayısı **değişmiyor** (idempotent).

### 2.3 `scripts/ingest.py` (~30 dk)
- `load_all` → `chunk` → `build_index`, ilerleme çıktısı, özet rapor
  (dosya başına chunk sayısı, toplam süre).
- **DoD:** `python scripts/ingest.py` < 3 dk'da (model önbellekteyse) tamamlanıyor,
  özet tablo basıyor, hata vermiyor.

---

## Faz 3 — Retrieval (~2 saat) 🎯 Doğruluğun kaynağı

### 3.1 `retriever.py` (~1,5 saat)
- Hibrit arama: dense (Chroma, `query:` öneki) + BM25, her biri top-20.
- RRF birleştirme (k=60).
- `source_filter` metadata filtresi.
- Güven skoru hesabı (dense kosinüs + BM25 çift koşulu, TRD §4.7).
- **DoD:** `test_retriever.py` yeşil:
  - "İnsan Kaynakları yıllık izin" → ilk 3'te İK belgesinden chunk (**ASCII sorununun kanıtı**).
  - "Aksef kontrendikasyon" → ilk 1'de Aksef Bölüm 4.3.
  - "OPS-PRO-003" (belge kodu) → ilk 1'de araç prosedürü (**BM25'in kanıtı**).
  - "Vitatin95 ürün müdürü" → ilk 3'te taksonomi satırı.

### 3.2 Eşik kalibrasyonu (~30 dk)
- 8 demo sorusu + 5 konu dışı soru için skor dağılımını ölç.
- `MIN_COSINE` ve `MIN_BM25` değerlerini ayır edecek şekilde seç.
- **DoD:** 8 geçerli sorunun **hepsi** eşiği geçiyor, 5 konu dışı sorunun **hiçbiri** geçmiyor.
  Seçilen değerler ve dağılım tablosu not edildi (README'ye girecek).

---

## Faz 4 — LLM ve Agent (~3 saat)

### 4.1 `llm.py` (~1 saat)
- `LLMResponse` dataclass + `LLMClient` protokolü.
- `OllamaClient` (`/api/chat`, `tools` desteği), `AnthropicClient`, `OpenAIClient`.
- `get_client()` fabrika, env tabanlı seçim, anahtar yoksa anlamlı hata mesajı.
- **DoD:** Seçilen sağlayıcıyla basit bir "merhaba" çağrısı ve bir tool çağrısı dönüyor.

### 4.2 `tools.py` (~45 dk)
- 3 tool'un JSON şeması + Python implementasyonu.
- `search_documents` → retriever; `lookup_section` → `chunks.jsonl` üzerinde
  `source_file` + `section_id`/`section_title` eşleşmesi; `list_documents` → belge envanteri.
- Numaralandırılmış çıktı formatı (TRD §4.8).
- **DoD:** Her tool doğrudan Python'dan çağrıldığında beklenen sonucu dönüyor;
  `lookup_section("Aksef", "4.3")` doğru bölüm metnini getiriyor.

### 4.3 `prompts.py` (~30 dk)
- Sistem promptu (grounded, atıf zorunlu, Türkçe).
- `REFUSAL_TEMPLATE` (konu dışı), `NO_INFO_TEMPLATE` (bilgi yok).
- **DoD:** Promptlar tek yerden yönetiliyor, kodda string literal yok.

### 4.4 `agent.py` (~45 dk)
- Ön kapı (skor eşiği) → tool döngüsü (max 3 tur) → atıf post-check (TRD §4.10).
- `tool_trace` toplama.
- **DoD:**
  - Demo sorusu 1 → doğru cevap + ≥1 atıf + trace'te `search_documents` görünüyor.
  - Soru 8a ("2027 kâr hedefi") → `NO_INFO_TEMPLATE`, uydurma yok.
  - Soru 8b ("hava nasıl") → `REFUSAL_TEMPLATE`, **LLM çağrısı yapılmadı** (trace boş).

---

## Faz 5 — Arayüzler (~2 saat)

### 5.1 `cli.py` (~45 dk)
- Tek atışlık: `python -m src.rag.cli "soru"`.
- İnteraktif mod: `python -m src.rag.cli` → prompt döngüsü, `çıkış` ile son.
- Windows'ta UTF-8 çıktı garantisi (`sys.stdout.reconfigure(encoding="utf-8")`).
- **DoD:** Windows PowerShell'de Türkçe karakterli soru-cevap bozulmadan görünüyor.

### 5.2 `app.py` — Streamlit (~1,25 saat)
- Soru kutusu, cevap alanı.
- Genişletilebilir **"Kaynaklar"** paneli: her kaynağın etiketi + chunk metni.
- Genişletilebilir **"Tool çağrıları"** paneli: hangi tool, hangi argüman, kaç sonuç.
- Yan panel: sağlayıcı bilgisi, `top_k`, örnek sorular butonları.
- `@st.cache_resource` ile indeks ve model tek kez yüklenir.
- **DoD:** `streamlit run app.py` açılıyor; 8 demo sorusu arayüzden çalışıyor;
  kaynak paneli her cevapta dolu.

---

## Faz 6 — Demo, Docker, Dokümantasyon (~3 saat)

### 6.1 `notebooks/demo.ipynb` (~1 saat)
- Kurulum hücresi + indeks yükleme.
- **8 senaryo** (PRD §7): her biri için soru, cevap, kaynaklar, tool trace.
- Retrieval skor dağılımı tablosu (eşik kalibrasyonunun kanıtı).
- **DoD:** Notebook baştan sona `Restart & Run All` ile hatasız çalışıyor;
  çıktılar kaydedilmiş; ≥5 soru-cevap ✔, ≥1 "bilmiyorum" ✔, her formattan ≥1 soru ✔.

### 6.2 Docker (~45 dk)
- `Dockerfile`: python:3.11-slim, bağımlılıklar, **embedding modeli build'de indirilir**,
  entrypoint = (gerekirse ingest) + streamlit.
- `docker-compose.yml`: `rag` servisi (+ `ollama` servisi, sağlayıcı seçimine göre profil).
- **DoD:** `docker compose up` sonrası `localhost:8501` çalışıyor ve soru cevaplıyor.

### 6.3 `README.md` (~1 saat) — case §1.4.3'ün tamamını karşılamalı
- **3 komutluk kurulum** (NFR-1):
  ```
  pip install -r requirements.txt
  python scripts/ingest.py
  streamlit run app.py
  ```
- **ASCII mimari diyagramı** (TRD §1'den).
- **Framework ve model seçim gerekçeleri** → ADR-001…004, 007 özeti.
- **Karşılaşılan zorluklar ve çözüm yaklaşımı** → bulgular §1.2–§1.6
  (Türkçe karakter tutarsızlığı, DOCX tabloları, XLSX kaymalı başlık, PDF dipnot
  yanlış pozitifi, dosya adında Türkçe karakter).
- **Sınırlılıklar ve iyileştirme önerileri** → TRD §9.
- Demo soru-cevap örnekleri (notebook'a link).
- **DoD:** Projeyi hiç görmemiş biri README ile sıfırdan çalıştırabiliyor.

### 6.4 Teslim paketi (~15 dk)
- `storage/`, `.env`, `__pycache__` hariç ZIP.
- **DoD:** ZIP açılıp 3 komutla çalıştırıldığında sistem ayağa kalkıyor.

---

## Faz Özeti ve Kritik Yol

```
Faz 0 (1s) ──► Faz 1 (4s) ──► Faz 2 (2,5s) ──► Faz 3 (2s) ──► Faz 4 (3s) ──► Faz 5 (2s) ──► Faz 6 (3s)
 iskelet      loaders ⚠️      chunk+index     retrieval 🎯    agent+LLM     arayüz       teslim
```

**Kritik yol Faz 1 → Faz 3.** Bu iki faz doğru biterse geri kalanı düşük riskli.
Faz 4'te LLM sağlayıcısı sorun çıkarırsa (lokal model tool-calling'i tutarsız üretirse)
`LLM_PROVIDER` değiştirilerek ilerlenebilir — bu, ADR-007'deki soyutlamanın asıl sebebi.

## Erken Doğrulama Noktaları

| Ne zaman | Kontrol | Başarısızsa |
|---|---|---|
| Faz 1 sonu | 6 belgeden de `RawSection` çıkıyor, tablolar dahil | Loader'da kal, ilerleme |
| Faz 3 sonu | 4 retrieval testi geçiyor | Normalizasyon/RRF'yi gözden geçir |
| Faz 4.4 sonu | "Bilmiyorum" ve konu dışı senaryoları çalışıyor | Eşiği yeniden kalibre et |
| Faz 6.1 sonu | Notebook `Restart & Run All` temiz | Teslim etme |
