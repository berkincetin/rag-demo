# TRD — Bölüm 1: RAG Tabanlı AI Agent

Teknik tasarım dokümanı. Kararların gerekçeleri [../02-karar-kaydi.md](../planlama/02-karar-kaydi.md),
veri gerçekleri [../01-veri-kesif-bulgulari.md](../planlama/01-veri-kesif-bulgulari.md) dosyalarında.

---

## 1. Mimari

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          KULLANICI KATMANI                               │
│   Streamlit (app.py)                 CLI (src/rag/cli.py)                │
│   soru + kaynak paneli + tool izi     soru → cevap (stdout)              │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ soru (Türkçe, doğal dil)
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       AGENT (src/rag/agent.py)                           │
│                                                                          │
│   1. Grounded sistem promptu + kullanıcı sorusu                          │
│   2. LLM tool-calling döngüsü (max 3 tur)                                │
│   3. Güvenlik ağı: skor kapısı → prompt → atıf post-check                │
└───────┬──────────────────────────────────────────────┬───────────────────┘
        │ tool çağrısı                                 │ chat(messages, tools)
        ▼                                              ▼
┌───────────────────────────────┐        ┌─────────────────────────────────┐
│    TOOLS (src/rag/tools.py)   │        │      LLM (src/rag/llm.py)       │
│  • search_documents(q,k,src)  │        │  Provider soyutlaması:          │
│  • lookup_section(doc,sec)    │        │   ollama | anthropic | openai   │
│  • list_documents()           │        │  LLM_PROVIDER env ile seçilir   │
└───────────────┬───────────────┘        └─────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    RETRIEVER (src/rag/retriever.py)                      │
│                                                                          │
│    sorgu ──► normalize (ASCII katlama, TR)                               │
│              ├──► BM25 (rank_bm25)      ──► sıralama A                   │
│              └──► dense (e5-base+Chroma) ──► sıralama B                  │
│                          └──► RRF birleştirme ──► top_k chunk + metadata │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         İNDEKS (storage/)                                │
│    chroma/  → vektörler + metadata      bm25.pkl → leksik indeks         │
│    chunks.jsonl → chunk metinleri (lookup_section ve denetim için)       │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ scripts/ingest.py (offline, tek sefer)
┌───────────────────────────────┴──────────────────────────────────────────┐
│                     INGEST BORU HATTI                                    │
│                                                                          │
│  data/*.pdf  ──► pdf_loader   ─┐                                         │
│  data/*.docx ──► docx_loader  ─┼──► chunker ──► normalize ──► embed ──► indeks │
│  data/*.xlsx ──► xlsx_loader  ─┘   (bölüm-farkındalıklı)                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Proje Yapısı

```
rag-demo/
├── data/                              # 6 kaynak belge (AI Engineer/Rag_Agent'ten kopyalanır)
├── src/rag/
│   ├── __init__.py
│   ├── config.py                      # env tabanlı ayarlar (dataclass)
│   ├── normalize.py                   # TR ASCII katlama, whitespace, metin temizleme
│   ├── models.py                      # Chunk, SearchHit, Citation dataclass'ları
│   ├── loaders/
│   │   ├── __init__.py                # load_all(data_dir) -> list[RawSection]
│   │   ├── pdf_loader.py
│   │   ├── docx_loader.py
│   │   └── xlsx_loader.py
│   ├── chunker.py                     # RawSection -> list[Chunk]
│   ├── index.py                       # build_index / load_index (Chroma + BM25)
│   ├── retriever.py                   # hibrit arama + RRF
│   ├── tools.py                       # 3 tool + JSON şemaları
│   ├── llm.py                         # provider soyutlaması
│   ├── prompts.py                     # sistem promptu, red şablonları
│   ├── agent.py                       # tool-calling döngüsü + güvenlik ağı
│   └── cli.py
├── scripts/ingest.py
├── app.py                             # Streamlit
├── notebooks/demo.ipynb
├── tests/
│   ├── test_loaders.py
│   ├── test_normalize.py
│   ├── test_chunker.py
│   └── test_retriever.py
├── storage/                           # .gitignore'da
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 3. Veri Modeli

```python
@dataclass
class RawSection:
    """Loader çıktısı — henüz chunk'lanmamış mantıksal bölüm."""
    source_file: str          # "Aksef 500 mg FKTB_Onaylı KUB.pdf"
    doc_type: str             # "pdf" | "docx" | "xlsx"
    section_id: str | None    # "4.2" | None
    section_title: str | None # "Pozoloji ve uygulama şekli"
    section_path: str | None  # "4. KLİNİK ÖZELLİKLER > 4.2 Pozoloji ..."
    page_start: int | None
    page_end: int | None
    sheet: str | None         # XLSX
    row: int | None           # XLSX
    text: str

@dataclass
class Chunk:
    chunk_id: str             # "aksef__4.2__0"
    text: str                 # gösterilecek orijinal metin
    search_text: str          # ASCII katlanmış, BM25 ve embedding girdisi
    citation_label: str       # "Aksef 500 mg KUB.pdf — Bölüm 4.2 Pozoloji ..., s.2"
    metadata: dict            # RawSection alanları + char_count
```

### 3.1 Chroma metadata şeması
`source_file`, `doc_type`, `section_id`, `section_title`, `page_start`, `page_end`,
`sheet`, `row`, `citation_label`.
> Not: Chroma metadata değerleri skaler olmalı (str/int/float/bool). `None` değerler
> `""` veya `-1` ile değiştirilir.

---

## 4. Modül Tasarımları

### 4.1 `loaders/pdf_loader.py`

**Girdi:** PDF yolu. **Çıktı:** `list[RawSection]`.

**Algoritma:**
1. `pypdf.PdfReader` ile sayfa sayfa metin çıkar; `(page_no, line)` çiftleri üret.
2. Bölüm başlığı regex'i: `^\s*(\d{1,2}(?:\.\d{1,2}){0,2})\.?\s+(\S.{2,70})$`
3. **Yanlış pozitif filtresi** (bulgular §1.2 — Duxet s.15 dipnotları):
   - Bölüm numarası KÜB beyaz listesinde mi? (`1, 2, 3, 4, 4.1…4.9, 5, 5.1…5.3, 6, 6.1…6.6`)
   - Ve numara bir önceki kabul edilen bölümden büyük mü (monoton artış)?
   - İki koşul da sağlanmıyorsa satır normal içerik sayılır.
4. Ardışık başlıklar arası metin o bölümün gövdesi; `page_start` / `page_end` izlenir.
5. Sayfa üstü/altı temizliği: `^\d+/\d+$` (ör. `1/12`) ve tek başına sayfa numarası satırları atılır.

**Fallback:** Hiç bölüm bulunamazsa (KÜB olmayan bir PDF eklenirse) sayfa başına 1 `RawSection`.

**Test:** Aksef'ten ≥20, Duxet'ten ≥20 geçerli bölüm çıkmalı; `4.3` bölümü Aksef'te sayfa 3'te
bulunmalı; Duxet'te `7 Plasebodan...` bölüm olarak **çıkmamalı**.

### 4.2 `loaders/docx_loader.py`

**Algoritma:**
1. `docx.Document(path)` — `document.element.body` üzerinden **paragraf ve tabloları
   belge sırasına göre** dolaş (`CT_P` / `CT_Tbl`). Yalnızca `.paragraphs` kullanmak
   tabloları kaçırır (bulgular §1.3 — 7 ve 9 tablo var).
2. `paragraph.style` `None` olabilir → `getattr(p.style, "name", "") or ""` ile korun
   (ölçümde `AttributeError` alındı).
3. Başlık takibi: `Heading 1` → h1 güncelle, h2 sıfırla; `Heading 2` → h2 güncelle.
   Yeni bölüm açılır, `section_path = f"{h1} > {h2}"`.
4. `List Paragraph` stilindeki paragraflar `- ` öneki ile eklenir (madde yapısı korunur).
5. Tablo → Markdown tablosu, mevcut bölümün metnine eklenir:
   ```
   | Pozisyon Seviyesi | Araç Hakkı | Yakıt Limiti (Ay) | Özel Kullanım |
   | --- | --- | --- | --- |
   | Direktör / Bölüm Başkanı | Tahsisli (üst orta segment) | 1.500 TL/ay | Hafta sonu dahil |
   ```
   Tablo hücreleri hem okunabilir hem BM25 için aranabilir kalır.
6. Başlıktan önceki giriş paragrafları (`TEKNOPARK YAZILIM A.S.`, belge no, versiyon) →
   `section_title="Belge Bilgileri"` altında toplanır.

**Test:** `arac_kullanim_proseduru.docx` çıktısında `1.500 TL/ay` metni bulunmalı;
`ik_surecleri_politikası.docx` için ≥8 farklı `section_path` üretilmeli.

### 4.3 `loaders/xlsx_loader.py`

**Başlık satırı tespiti** (bulgular §1.5 — başlıklar 3. satırda):
```
header_row = ilk satır i (i < 10) öyle ki:
    dolu_hücre_oranı(i) >= 0.6  AND  satır i'deki hücrelerin hiçbiri NaN-heavy başlık değil
```
Pratikte: `pd.read_excel(header=None)` ile oku, ilk 10 satırda en çok dolu hücreye sahip
ve tekrar eden metin içermeyen satırı başlık kabul et. Fallback: `header=0`.

**Sayfa başına strateji:**

| Dosya / Sayfa | Chunk birimi | Chunk metni |
|---|---|---|
| `calisan_sss_rehberi.xlsx` / Genel SSS | 1 satır | `Kategori: X \| Alt Kategori: Y\n{Soru & Cevap hücresi}` |
| / IT Sistem Rehberi | 1 satır | `Sistem: HRPortal \| Açıklama: ... \| Erişim: ... \| Destek: #ik-destek` |
| / Onboarding Kontrol Listesi | 1 satır | `Aşama: Pre-Boarding \| Görev: ... \| Sorumlu: IT \| Süre: ...` |
| `Anonim_Urun_Taksonomi_100Satir.xlsx` | 1 satır | 15 alanın `Alan: Değer` biçiminde birleşimi |

Sayfa üst bilgisi (`Son Guncelleme: Ocak 2025 | Versiyon: 4.1`) her chunk'ın başına
bağlam olarak eklenmez; ayrı bir "belge bilgisi" chunk'ı olur (gürültü artırmamak için).

**Test:** SSS'ten 14 (17−3 başlık/ön bilgi) civarı chunk; taksonomiden tam **100** chunk;
`Vitatin95` metni bir chunk içinde bulunmalı.

### 4.4 `normalize.py`

```python
def fold_tr(s: str) -> str:
    """Türkçe-duyarlı ASCII katlama. Arama alanı üretir, GÖSTERİM için kullanılmaz."""
    # 1) Türkçe özel eşlemeler ÖNCE (unicodedata bunları doğru katlamaz):
    #    İ→I, ı→i, Ş→S, ş→s, Ğ→G, ğ→g, Ç→C, ç→c, Ö→O, ö→o, Ü→U, ü→u
    # 2) unicodedata.normalize("NFKD") + combining karakter temizliği
    # 3) casefold()
    # 4) çoklu boşluk → tek boşluk
```

Neden gerekli: bulgular §1.4 — DOCX `Insan Kaynaklari`, PDF `İnsan Kaynakları`.
`fold_tr` her ikisini de `insan kaynaklari` yapar. Sorgu da aynı fonksiyondan geçer.

⚠️ Python'un varsayılan `str.lower()`'ı `I` → `i` yapar ama `İ` → `i̇` (birleşik nokta)
üretir; bu yüzden Türkçe eşlemeler `casefold()`'dan **önce** uygulanmalı.

**Test:** `fold_tr("İnsan Kaynakları") == fold_tr("Insan Kaynaklari") == "insan kaynaklari"`

### 4.5 `chunker.py`

```
her RawSection için:
    if len(text) <= MAX_CHARS (1200):
        → tek chunk
    else:
        → paragraf sınırlarından (\n\n) böl, MAX_CHARS'a kadar biriktir
        → OVERLAP (150 karakter) ile ardışık chunk'lar örtüşür
        → her parça aynı section metadata'sını ve `chunk_index`'i taşır
XLSX satır chunk'ları ASLA bölünmez (ADR-005).
```

`citation_label` üretimi:
```python
pdf : f"{file} — Bölüm {section_id} {section_title}, s.{page_start}"
docx: f"{file} — {section_path}"
xlsx: f"{file} — {sheet}, satır {row}"
```

### 4.6 `index.py`

```python
def build_index(chunks: list[Chunk], storage_dir: Path) -> None:
    # 1. Chroma PersistentClient(storage/chroma), koleksiyon sıfırlanır (idempotent)
    # 2. embeddings = model.encode(["passage: " + c.search_text for c in chunks])
    #    → e5 önek şeması (ADR-002)
    # 3. collection.add(ids, embeddings, documents=c.text, metadatas=...)
    # 4. BM25Okapi([c.search_text.split() for c in chunks]) → storage/bm25.pkl
    # 5. chunks.jsonl yazılır (lookup_section ve denetim için)
```

Batch boyutu 64. Toplam ~350 chunk → CPU'da ~30–60 sn.

### 4.7 `retriever.py`

```python
def search(query, top_k=5, source_filter=None) -> list[SearchHit]:
    q = fold_tr(query)

    dense_ranking = chroma.query(embed("query: " + q), n_results=20, where=filter)
    bm25_ranking  = bm25.get_top_n(q.split(), n=20)

    # Reciprocal Rank Fusion (k=60, standart)
    score[chunk] = Σ_ranking 1 / (60 + rank_in_that_ranking)

    return top_k hits (score, chunk, citation_label)
```

**Neden RRF:** iki sıralamanın skor ölçekleri farklı (kosinüs benzerliği vs. BM25 skoru);
normalizasyon ve ağırlık ayarı gerektirmeyen, sıra tabanlı, literatürde sağlam bir yöntem.
Ayarlanacak hiperparametre yok → demo kırılganlığı düşük.

**Güven skoru (`RETRIEVAL_MIN_SCORE`):** RRF skoru mutlak anlam taşımadığı için güven
kapısı **iki koşullu**:
1. En iyi sonucun dense kosinüs benzerliği ≥ `MIN_COSINE` (varsayılan 0.72, e5 için kalibre edilecek), **veya**
2. En iyi sonucun BM25 skoru ≥ `MIN_BM25` (varsayılan medyanın 2 katı)

İkisi de sağlanmıyorsa → "bilgi bulunamadı" yolu (ADR-008 katman 1).
Eşikler demo notebook'unda 8 senaryo üzerinde kalibre edilip README'de raporlanır.

### 4.8 `tools.py`

```python
TOOLS = [
  {
    "name": "search_documents",
    "description": "Şirket bilgi tabanında doğal dil sorgusuyla arama yapar. "
                   "İlgili doküman parçalarını kaynak bilgisiyle döndürür.",
    "parameters": {
      "query": "str — arama sorgusu (Türkçe)",
      "top_k": "int — kaç sonuç (varsayılan 5, max 10)",
      "source_filter": "str | None — dosya adı filtresi (ör. 'Aksef')"
    }
  },
  {
    "name": "lookup_section",
    "description": "Belirli bir belgenin belirli bir bölümünü doğrudan getirir. "
                   "Bölüm numarası veya başlığı bilindiğinde arama yerine kullanılır.",
    "parameters": {"document": "str", "section": "str"}
  },
  {
    "name": "list_documents",
    "description": "Bilgi tabanındaki tüm belgeleri, tiplerini ve bölüm başlıklarını listeler.",
    "parameters": {}
  }
]
```

Tool çıktı formatı (LLM'e giden):
```
[1] Aksef 500 mg FKTB_Onaylı KUB.pdf — Bölüm 4.3 Kontrendikasyonlar, s.3
AKSEF, sefalosporin grubu antibiyotiklere karşı aşırı duyarlılığı olan hastalarda ...

[2] ...
```
Numaralandırma, LLM'in atıfları `[1]`, `[2]` ile referanslamasını ve post-check'in
eşleştirme yapmasını kolaylaştırır.

### 4.9 `llm.py` — Provider Soyutlaması

```python
class LLMClient(Protocol):
    def chat(self, messages: list[dict], tools: list[dict] | None) -> LLMResponse: ...

# LLMResponse: .text | .tool_calls (name, arguments, id)

def get_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)
    match provider:
        case "ollama":     return OllamaClient(model=os.getenv("LLM_MODEL", "qwen2.5:7b-instruct"))
        case "anthropic":  return AnthropicClient(model="claude-haiku-4-5-20251001")
        case "openai":     return OpenAIClient(model=os.getenv("LLM_MODEL", "gpt-4o-mini"))
```

Her adaptörün tek sorumluluğu: tool şemasını sağlayıcının formatına çevirmek ve cevabı
`LLMResponse`'a normalize etmek. Ollama için `/api/chat` endpoint'i `tools` parametresini
destekliyor (0.4+). (ADR-007)

### 4.10 `agent.py`

```
answer(question) ->
  1. ön kapı: retriever.search(question, top_k=1) güven eşiğinin altındaysa
       → REFUSAL_TEMPLATE (LLM çağrısı YOK)
  2. messages = [system_prompt, user_question]
  3. döngü (max 3 tur):
       resp = llm.chat(messages, TOOLS)
       if resp.tool_calls: tool'ları çalıştır, sonuçları messages'a ekle, devam
       else: break
  4. post-check: cevapta en az bir geçerli citation_label / [n] referansı var mı?
       yoksa → NO_INFO_TEMPLATE
  5. return Answer(text, citations, tool_trace)
```

Sistem promptu (`prompts.py`) çekirdeği:
- "Yalnızca tool'lardan gelen belge içeriğine dayanarak cevap ver."
- "Her bilgi için `[n]` numarasıyla kaynak göster; cevabın sonunda kaynakları listele."
- "Bağlamda cevap yoksa 'Bu konuda bilgi tabanımda bilgi bulamadım' de. Tahmin yürütme."
- "Şirket bilgi tabanı dışındaki konularda kibarca kapsam dışı olduğunu belirt."
- "Türkçe cevap ver."

---

## 5. Konfigürasyon (`.env.example`)

```ini
LLM_PROVIDER=ollama              # ollama | anthropic | openai
LLM_MODEL=qwen2.5:7b-instruct
OLLAMA_BASE_URL=http://localhost:11434
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

EMBEDDING_MODEL=intfloat/multilingual-e5-base
DATA_DIR=./data
STORAGE_DIR=./storage
CHUNK_MAX_CHARS=1200
CHUNK_OVERLAP=150
TOP_K=5
MIN_COSINE=0.72
MAX_TOOL_TURNS=3
```

---

## 6. Bağımlılıklar (`requirements.txt` taslağı)

| Paket | Amaç |
|---|---|
| `chromadb` | Vektör deposu (ADR-003) |
| `sentence-transformers` | Embedding (ADR-002) |
| `rank-bm25` | Leksik arama (ADR-004) |
| `pypdf` | PDF okuma |
| `python-docx` | DOCX okuma (tablolar dahil) |
| `pandas` + `openpyxl` | XLSX okuma |
| `streamlit` | UI (bonus F9) |
| `python-dotenv` | Konfigürasyon |
| `requests` | Ollama HTTP istemcisi |
| `anthropic` *veya* `openai` | Bulut sağlayıcı (opsiyonel, seçime göre) |
| `pytest` | Testler (dev) |

**11 doğrudan bağımlılık** → NFR-7 (≤12) sağlanıyor.

---

## 7. Docker

```yaml
# docker-compose.yml
services:
  rag:
    build: .
    ports: ["8501:8501"]
    env_file: .env
    volumes: ["./data:/app/data", "./storage:/app/storage"]
    depends_on: [ollama]          # LLM_PROVIDER=ollama ise
  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: ["ollama:/root/.ollama"]
volumes: { ollama: {} }
```

`Dockerfile` build aşamasında embedding modelini önden indirir (ilk çalıştırmada
1,1 GB beklememek için). Entrypoint: ingest yapılmamışsa yapar, sonra Streamlit'i başlatır.

> Bulut sağlayıcı seçilirse `ollama` servisi profil arkasına alınır
> (`profiles: [local]`), böylece `docker compose up` tek servisle kalkar.

---

## 8. Test Stratejisi

| Test | Doğruladığı |
|---|---|
| `test_normalize.py` | `fold_tr` Türkçe/ASCII eşdeğerliği (bulgular §1.4) |
| `test_loaders.py::test_pdf_sections` | Aksef'te 4.3 bölümü s.3'te; Duxet dipnot yanlış pozitifi yok |
| `test_loaders.py::test_docx_tables` | `1.500 TL/ay` chunk metninde geçiyor (US-3'ün kanıtı) |
| `test_loaders.py::test_xlsx_header` | SSS başlık satırı doğru tespit; taksonomiden 100 chunk |
| `test_chunker.py` | XLSX satırları bölünmüyor; PDF bölümleri 1200 karakteri aşmıyor |
| `test_retriever.py` | "İnsan Kaynakları izin" sorgusu ASCII'li DOCX chunk'ını buluyor |

Testler LLM çağırmaz — hızlı ve deterministik. Agent davranışı demo notebook'unda
gösterilir (LLM'e bağlı olduğu için otomatik teste uygun değil).

---

## 9. Bilinen Sınırlılıklar (README'ye taşınacak)

1. **Chunk üstü akıl yürütme yok.** "İK ve araç prosedürlerini karşılaştır" gibi sorularda
   sistem parçaları getirir ama sentez kalitesi LLM'e bağlıdır.
2. **Tablo semantiği kısmi.** Tablolar Markdown olarak metne gömülüyor; çok satırlı
   hesaplama gerektiren sorular (ör. "hangi seviyelerin yakıt limiti toplamı") desteklenmez.
3. **Bölüm tespiti KÜB şablonuna özel.** Farklı formatta bir PDF eklenirse sayfa bazlı
   fallback'e düşer, atıf kalitesi düşer.
4. **Statik indeks.** Belge değişirse `ingest.py` elle çalıştırılmalı.
5. **Güven eşiği korpusa kalibre.** Yeni belge eklenince yeniden kalibrasyon gerekebilir.
6. **Değerlendirme metriği yok.** Retrieval kalitesi 8 senaryolu manuel demo ile gösteriliyor;
   otomatik recall@k ölçümü kapsam dışı.
