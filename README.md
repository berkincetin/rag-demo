# RAG Agent — Şirket Bilgi Asistanı

Altı şirket belgesi (2 PDF, 2 DOCX, 2 XLSX) üzerinde **Türkçe** doğal dilde soru-cevap
yapan, tool-calling kullanan ve her cevabı **dosya/bölüm/sayfa atfıyla** kaynaklandıran
lokal çalışabilir bir RAG agent'ı.

Bilmediğini söyler, konu dışı soruları kibarca reddeder, hiçbir cevabı kaynaksız vermez.

---

## Kurulum — üç komut

```bash
pip install -r requirements.txt
python scripts/ingest.py
streamlit run app.py
```

`ingest.py` altı belgeyi okur, 276 chunk üretir ve indeksi `storage/` altına yazar
(ilk çalıştırmada embedding modeli ~1,1 GB indirilir). `app.py` arayüzü
`localhost:8501` adresinde açar.

**LLM:** varsayılan sağlayıcı [Ollama](https://ollama.com) (lokal). Önce modeli çekin:

```bash
ollama pull qwen2.5:7b-instruct
```

`.env.example` dosyasını `.env` olarak kopyalayıp ayarları değiştirebilirsiniz.
Bulut sağlayıcıya geçmek için `LLM_PROVIDER=anthropic` (veya `openai`) + API anahtarı
yeterlidir; ilgili SDK'yı ayrıca kurmanız gerekir (`pip install anthropic`).

> ⚠️ **`LLM_MODEL` gerçekten çektiğiniz etiketle birebir aynı olmalı.** `ollama list` ile
> kontrol edin — kuantize sürümler `qwen2.5:7b-instruct-q4_K_M` gibi bir sonek taşır ve
> düz etiket `404` döndürür.

### Terminal arayüzü

```bash
python -m src.rag.cli "Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?"
python -m src.rag.cli          # interaktif mod
```

### Windows notu

Konsol cp1252 kullandığı için Türkçe çıktıda `UnicodeEncodeError` alabilirsiniz:

```powershell
$env:PYTHONIOENCODING="utf-8"
```

---

## Mimari

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
│   1. Skor kapısı (LLM'den ÖNCE) — konu dışıysa hemen reddet              │
│   2. LLM tool-calling döngüsü (max 3 tur)                                │
│   3. Atıf post-check — kaynaksız cevabı "bilgi bulamadım" ile değiştir   │
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
│              ├──► BM25 (rank_bm25)       ──► sıralama A                  │
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

**Ölçülen boyutlar:** 6 belge → 219 bölüm → **276 chunk** (144.365 karakter).
Ingest süresi ~55 sn (CPU, model önbellekteyken).

---

## Teknoloji seçimleri ve gerekçeleri

| Karar | Seçim | Neden |
|---|---|---|
| Framework | **Ham Python + sağlayıcı SDK'sı** (LangChain/LlamaIndex yok) | Demo ölçeğinde soyutlama katmanı fayda değil borç üretir. Retrieval ve agent döngüsü ~200 satır; her davranış açıkça görülebilir ve test edilebilir |
| Embedding | **`intfloat/multilingual-e5-base`** | Türkçe'de güçlü, lokal çalışır (API anahtarı gerektirmez), `query:`/`passage:` önek şeması asimetrik aramada belirgin kazanç sağlar |
| Vektör deposu | **ChromaDB** (`PersistentClient`) | Kurulum gerektirmeyen gömülü depo; 276 chunk için sunucu tabanlı bir çözüm gereksiz |
| Retrieval | **Hibrit BM25 + dense, RRF (k=60)** | İkisi farklı hataları yapıyor: dense `OPS-PRO-003` gibi belge kodlarını yakalayamıyor, BM25 anlamsal yakınlığı göremiyor. RRF **sıra** birleştirdiği için skor normalizasyonu ve ağırlık ayarı gerektirmez |
| LLM | **Takılabilir katman, varsayılan Ollama** | Case lokal çalışabilirliği tercih ediyor. Yerel model yetersiz kalırsa `LLM_PROVIDER` ile buluta geçiş tek satır |

---

## Karşılaşılan zorluklar ve çözümleri

Hepsi gerçek veri üzerinde **ölçülerek** tespit edildi; hiçbiri varsayım değil.

### 1. Türkçe karakter tutarsızlığı formatlar arasında

DOCX'ler ASCII'ye indirgenmiş (`Insan Kaynaklari`), PDF'ler tam Türkçe (`İnsan Kaynakları`) —
hatta aynı cümlede karışık. Doğru yazılmış bir sorgu DOCX'i bulamıyordu.

**Çözüm:** `fold_tr()` — Türkçe harf eşlemeleri `casefold()`'dan **önce** uygulanır.
Python'un `lower()` fonksiyonu `İ` harfini `i` + birleşen nokta (U+0307) yapıyor ve bu
işaret NFKD'den sağ çıkıp eşleşmeyi bozuyor. Hem indeks hem sorgu tarafında uygulanır.

### 2. DOCX tabloları `document.paragraphs` ile görünmüyor

İki DOCX'te 7 ve 9 tablo var ve **en sorgulanabilir bilgi orada**: yakıt limitleri,
oryantasyon takvimi. `1.500 TL/ay` değeri belgede yalnızca bir tablo hücresinde geçiyor.

**Çözüm:** `document.element.body` üzerinden `CT_P` ve `CT_Tbl` düğümleri **belge sırasıyla**
dolaşılır, tablolar Markdown'a çevrilip ait oldukları bölüme eklenir. Ayrıca
`paragraph.style` bazı paragraflarda `None` geliyor — `getattr` ile korunuyor.

### 3. XLSX başlık satırı sabit değil

SSS rehberinde başlıkların üstünde başlık ve alt başlık satırları var. `read_excel(header=0)`
sütun adlarını `Unnamed: 1`, `Unnamed: 2` diye okuyor. Üstelik üç sayfanın başlık satırı
aynı yerde **değil**: 2, 2 ve 1.

**Çözüm:** `detect_header_row()` — ilk 10 satır taranır, doluluk oranı ≥ %60 olan en dolu
satır başlık kabul edilir. Sabit bir satır numarası yazılmaz.

### 4. PDF bölüm tespitinde yanlış pozitifler

Duxet KÜB'ünün 15. sayfasındaki dipnotlar (`7 Plasebodan istatistiksel olarak...`) bölüm
başlığı gibi görünüyor. Ham regex eşleşmesi Aksef'te 28, Duxet'te 33 "başlık" buluyordu.

**Çözüm:** KÜB bölüm numaraları beyaz listesi (1–6.6) **artı** monoton artış kontrolü.
İkisi birlikte çalışıyor: beyaz liste tek başına gövde metnindeki `4.2` referanslarını
elemiyor. Sonuç: her iki belgede de doğru 20 bölüm.

### 5. Dosya adında Türkçe karakter

`ik_surecleri_politikası.docx` — case metni dosya adını ASCII `i` ile yazmış. Sabit yazılmış
bir dosya adı bulunamazdı.

**Çözüm:** Hiçbir kaynak dosya adı koda gömülmez; `glob` ile taranır.

### 6. Bölüm başlıkları aranabilir değildi

KÜB bölüm 4.3'ün **başlığı** "Kontrendikasyonlar" ama bu kelime gövde metninde hiç geçmiyor.
"Aksef kontrendikasyonları" sorgusunda doğru bölüm üçüncü sıraya düşüyordu.

**Çözüm:** Bölüm kimliği/başlığı/yolu yalnızca **arama metnine** eklenir; görüntülenen metin
ve atıf etiketi değişmez.

### 7. BM25 Türkçe eklerde eşleşmiyor

Sorgu `kontrendikasyonlari`, indeks `kontrendikasyonlar` — BM25 tam token eşleşmesi yapar ve
eklemeli bir dilde bu asla tutmaz.

**Çözüm:** `bm25_tokens()` tokenları ilk **6 karaktere** kırpar (sabit uzunlukta kırpma
kökleştirme). 5/6/7/8 uzunlukları demo sorgu setinde ölçüldü; 6 tek çalışan değer.
Bölüm 4.3'ün BM25 skoru 0,00 → **8,31**, sırası 3. → **1.**

---

## "Bilmiyorum" ve konu dışı filtresi — eşik kalibrasyonu

Üç katmanlı güvenlik ağı:

1. **Skor kapısı (LLM'den önce).** Retrieval skorları yetersizse LLM hiç çağrılmaz.
2. **Grounded sistem promptu.** Model yalnızca tool sonucuna dayanmaya yönlendirilir.
3. **Atıf post-check.** Hiçbir `[n]` atfı gerçek bir kaynağa eşleşmiyorsa cevap
   "bilgi bulamadım" ile değiştirilir.

Eşikler **ölçülerek** belirlendi (10 geçerli soru, 6 konu dışı soru):

| | kosinüs (ilk sonuç) | BM25 (ilk sonuç) |
|---|---|---|
| **Geçerli sorular** | 0,811 – 0,874 | 7,51 – 21,55 |
| **Konu dışı sorular** | 0,746 – **0,813** | 0,00 – **8,25** |

🚨 **Bantlar çakışıyor.** Konu dışı "Bana bir şiir yaz" kosinüs **0,813** alıyor — en zayıf
geçerli sorunun (**0,811**) üstünde. Başka bir konu dışı soru BM25 **8,25** alıyor. Yani
**tek sinyalli bir eşik bu veride matematiksel olarak imkânsız**: kosinüs eşiği 0,813'ün
üstünde olmalı, ama o zaman geçerli sorular için BM25 eşiği ≤ 7,55 olmalı ve bu da 8,25'lik
konu dışı soruyu içeri alır.

**Karar: iki sinyalin de desteklemesi gerekir.**

```
güvenilir  ⇔  kosinüs ≥ 0.80  VE  bm25 ≥ 5.0
```

Bu eşiklerle **10 geçerli sorunun 10'u** geçiyor, **6 konu dışı sorunun 6'sı** eleniyor.
Değerler `.env` üzerinden (`MIN_COSINE`, `MIN_BM25`) ayarlanabilir.

---

## Demo

[`notebooks/demo.ipynb`](notebooks/demo.ipynb) — sekiz senaryo, her biri farklı bir yeteneği
kanıtlıyor:

| # | Soru | Kanıtladığı |
|---|---|---|
| 1 | Yıllık izin talebimi nasıl yaparım? | XLSX satır retrieval + çoklu kaynak |
| 2 | İşe alım süreci kaç aşamadan oluşur? | DOCX başlık hiyerarşisi |
| 3 | Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir? | **DOCX tablo desteği** |
| 4 | Havuz aracı nasıl talep edilir? | Prosedür adımları |
| 5 | Aksef 500 mg'ın kontrendikasyonları nelerdir? | **PDF bölüm + sayfa atfı** |
| 6 | Duxet'in gebelikte kullanımı hakkında ne yazıyor? | 24 sayfalık PDF'te doğru bölüm |
| 7 | Vitatin95 ürününün terapötik sistemi ve ürün müdürü kim? | Yapılandırılmış XLSX satırı |
| 8 | Şirketin 2027 kâr hedefi / Bugün hava nasıl? | **"Bilmiyorum"** ve **konu dışı** |

Örnek çıktı (senaryo 3 — değer yalnızca bir DOCX tablosunda geçiyor):

```
$ python -m src.rag.cli "Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?"

Direktör seviyesindeki çalışanların aylık yakıt limiti 1.500 TL/ay'dır.
Bu bilgi [1] numaralı belgeden alındı.

Kaynaklar:
  1. arac_kullanim_proseduru.docx — 3. ARAC TAHSIS POLITIKASI
```

Notebook'u çalıştırmak için `jupyter` gerekir:

```bash
pip install jupyter
jupyter lab notebooks/demo.ipynb
```

---

## Docker

```bash
docker compose up --build
```

`localhost:8501` arayüzü açar; `ollama` servisi ayrı konteynerde çalışır. **İlk kullanımda**
modeli ollama konteynerinin içinde çekmek gerekir:

```bash
docker compose exec ollama ollama pull qwen2.5:7b-instruct
```

---

## Testler

```bash
pytest -q                              # tümü
pytest -q -m "not integration"         # yalnız birim testleri
pytest -q -m integration               # yalnız entegrasyon (gerçek belgeler + indeks)
ruff format . && ruff check .          # biçim + lint
```

**103 test geçiyor, satır kapsamı %95.** Entegrasyon testleri hayali fikstürlerle değil,
`data/` altındaki **gerçek altı belgeyle** çalışır; assertion'lardaki her sayı ölçülmüştür.
LLM çıktısının metni hiçbir zaman test edilmez (deterministik değildir) — agent döngüsünün
kontrol akışı mock'lanmış bir LLM ile test edilir.

---

## Bilinen sınırlılıklar ve geliştirme fikirleri

1. **Chunk üstü akıl yürütme yok.** "İK ve araç prosedürlerini karşılaştır" gibi sorularda
   sistem doğru parçaları getirir ama sentez kalitesi tamamen LLM'e bağlıdır.
2. **Tablo semantiği kısmi.** Tablolar Markdown olarak metne gömülüyor; çok satırlı hesap
   isteyen sorular ("hangi seviyelerin yakıt limiti toplamı") desteklenmiyor.
3. **Bölüm tespiti KÜB şablonuna özel.** Farklı formatta bir PDF eklenirse sayfa bazlı
   fallback'e düşer ve atıf çözünürlüğü kabalaşır.
4. **Statik indeks.** Belgeler değişirse `ingest.py` elle çalıştırılmalı.
5. **Güven eşiği bu korpusa kalibre.** Yeni belge eklenince yeniden kalibrasyon gerekebilir.
6. **Otomatik değerlendirme metriği yok.** Retrieval kalitesi 8 senaryolu demo ve 7 retrieval
   probe testiyle gösteriliyor; `recall@k` ölçümü kapsam dışı bırakıldı.
7. **Yerel 7B modelin tool-calling'i kırılgan.** Ölçüldü: uzun bir sistem promptu tool
   çağrısını tamamen bastırıyor. Bu yüzden sistem promptu kısa tutuldu ve agent, model tool
   çağırmazsa aramayı kendisi yapıp izde `injected: true` olarak işaretliyor. Bulut modelde
   bu sorun görülmez.
8. **Atıf işaretlemesi modele bağlı — ölçülmüş yanlış negatif var.** Demo notebook'unda
   7 geçerli sorunun **6'sı** atıflı cevaplandı. "Duxet'in gebelikte kullanımı" sorusunda
   retrieval doğru çalıştı (kosinüs 0,849 / BM25 7,51, tool 6.255 karakter döndürdü) ama
   model cevabına `[n]` işareti koymadı; atıf post-check'i devreye girip cevabı
   "bilgi bulamadım" ile değiştirdi. Bu **kasıtlı bir tercih**: kaynağı doğrulanamayan bir
   cevabı vermektense reddetmek yeğdir. Yine de yanlış negatif oranı yerel modelde sıfır
   değil. Aynı şekilde atıf *seçimi* de her zaman isabetli değil — Aksef sorusunda cevap
   doğru bölümden geliyor ama model `Bölüm 1` ve `4.2`'yi işaretledi. Bulut sağlayıcıya
   geçmek (`LLM_PROVIDER=anthropic`) her iki davranışı da belirgin şekilde iyileştirir.

**Geliştirme fikirleri:** cross-encoder yeniden sıralama, sorgu genişletme (HyDE), RAGAS ile
otomatik değerlendirme, belge değişikliğini izleyen artımlı ingest, çok turlu sohbet bağlamı.

---

## Teslim notu

`data/` klasörü `.gitignore` içindedir (kaynak belgeler repoya işlenmez). **Teslim ZIP'ine
`data/` elle eklenmelidir** — aksi halde `python scripts/ingest.py` çalıştırılamaz.
