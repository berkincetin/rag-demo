# RAG Agent — Şirket Bilgi Asistanı

Altı şirket belgesi (2 PDF, 2 DOCX, 2 XLSX) üzerinde **Türkçe** doğal dilde soru-cevap
yapan, tool-calling kullanan ve her cevabı **dosya/bölüm/sayfa atfıyla** kaynaklandıran
lokal çalışabilir bir RAG agent'ı.

Bilmediğini söyler, konu dışı soruları kibarca reddeder, hiçbir cevabı kaynaksız vermez.

Aynı agent'ın üstünde **üç giriş noktası** var — hepsi aynı çekirdeği kullanır:

| Katman | Ne | Adres | Dosya |
|---|---|---|---|
| 🌐 **Next.js arayüzü** | React 19 + Tailwind 4, açık/koyu tema | `:3000` | `web/` |
| 🔌 **FastAPI backend** | Next.js'in konuştuğu HTTP API | `:8000` | `src/rag/api.py` |
| 🐍 **Gradio arayüzü** | Python'dan başka bir şey istemez | `:7860` | `gradio_app.py` |

Ek olarak bir **CLI** (`python -m src.rag.cli`) var. Gradio ve CLI agent'ı doğrudan
çağırır; Next.js araya FastAPI'yi koyar. Üçü de aynı `src/rag/` çekirdeğini paylaşır —
iş mantığı hiçbir arayüz katmanında tekrarlanmaz.

---

## Kurulum — üç komut

Üç yol da **en fazla üç komut**. Hangisini seçerseniz seçin sonuç aynı agent'tır.

### A) Docker — tek komut

```bash
docker compose up
```

`:3000` Next.js arayüzü · `:8000` HTTP API · `:7860` Gradio arayüzü.
İndeksleme, model indirme ve üç servisin başlatılması dahil her şeyi kendisi yapar.
`.env` **gerekmez** — yoksa varsayılanlarla çalışır, API anahtarları arayüzden girilebilir.

### B) Next.js arayüzü, Docker'sız — üç komut

```bash
pip install -r requirements.txt
python scripts/ingest.py
python scripts/run_web.py
```

`run_web.py` gerekiyorsa `npm install` çalıştırır, API'yi (`:8000`) ve arayüzü (`:3000`)
birlikte başlatır; Ctrl+C ikisini birden durdurur. Node.js 18+ gerekir.

### C) Gradio arayüzü, Docker'sız — üç komut

```bash
pip install -r requirements.txt
python scripts/ingest.py
python gradio_app.py
```

Node.js gerektirmez; arayüz `localhost:7860` adresinde açılır.

`ingest.py` altı belgeyi okur, 276 chunk üretir ve indeksi `storage/` altına yazar
(ilk çalıştırmada embedding modeli ~1,1 GB indirilir).

> İsteğe bağlı: `python scripts/setup.py` Ollama'yı kontrol edip sohbet modelini çeker.
> Ollama kurulu değilse **kurmaz** — platformunuza uygun kurulum komutunu yazdırıp durur.
> Modeli `ollama pull` ile kendiniz çektiyseniz veya Docker kullanıyorsanız gerekmez.

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

---

## İki arayüz, tek çekirdek

İki arayüz de **tam işlevli** — aynı beş ekranı (sohbet, sağlayıcılar, yerel modeller,
metrikler, değerlendirme) sunar. İstediğinizi kullanın; Docker ikisini birden kaldırır.

| Arayüz | Komut | Adres | Gerektirdiği |
|---|---|---|---|
| **Next.js** | `python scripts/run_web.py` | `localhost:3000` | Node.js 18+ (API'yi de o başlatır) |
| **Gradio** | `python gradio_app.py` | `localhost:7860` | Yalnızca Python |

```
Next.js (:3000) ──HTTP/JSON──► FastAPI (:8000) ──┐
                               src/rag/api.py    │
                                                 ├──► Agent (LangGraph)
Gradio  (:7860) ─────────────────────────────────┤     └─► Tools ─► Retriever ─► Chroma/BM25
gradio_app.py                                    │
                                                 │
CLI  (src/rag/cli.py) ───────────────────────────┘
```

Neden bu ayrım: **karar mantığı hiçbir arayüze girmez.** Model seçimi, anahtar durumu,
maliyet hesabı, atıf biçimlendirmesi — hepsi `src/rag/ui_state.py` içindedir ve hiçbir
arayüz kütüphanesi import etmez (oturum sıradan bir `MutableMapping`'tir). Gradio da
FastAPI da aynı fonksiyonları çağırır. Bu yüzden ikinci arayüzü eklemek iş mantığını
tekrarlamadı ve `ui_state` düz sözlüklerle test edilebiliyor.

### 🔌 FastAPI backend (`src/rag/api.py`)

Yalnızca **yönlendirme ve bağlantı**; hiçbir JSON şeklini kendisi üretmez. Her yanıt
gövdesi `src/rag/serialize.py` içindeki saf fonksiyonlardan gelir ve doğrudan test edilir
(`tests/test_api_serialization.py`, 9 test). Böylece `api.py` kapsam dışı bırakılabiliyor —
`gradio_app.py` ile aynı gerekçe: içinde test edilecek karar yok.

| Uç | Metot | Ne yapar |
|---|---|---|
| `/api/ask` | POST | Soru sorar; cevap + atıflar + araç izi + süre/token/maliyet/kaynak döner |
| `/api/chat/clear` | POST | Oturum belleğini ve transkripti temizler |
| `/api/models` | GET | Kullanılabilir modeller + aktif model + Ollama durumu |
| `/api/keys` | GET · POST | Sağlayıcı anahtarı durumu (maskeli) · anahtar kaydı |
| `/api/models/active` | POST | Aktif modeli değiştirir |
| `/api/ollama` | GET | Yerel modelleri listeler |
| `/api/ollama/pull` · `/delete` | POST | Model indirir · siler |
| `/api/metrics` | GET · DELETE | Model bazında özet + koşu geçmişi · sıfırlar |
| `/api/evaluation/cases` · `/estimate` · `/run` | GET · POST | 13 soruluk set · maliyet tahmini · karşılaştırmalı koşu |
| `/api/health` | GET | `{"ok": true}` |

**Oturum modeli:** tarayıcı her istekte `X-Session-Id` başlığı gönderir (ilk açılışta
`crypto.randomUUID()` ile üretilip `sessionStorage`'a yazılır). Sunucu bu kimliği bellekteki
bir sözlüğe eşler. API anahtarları **yalnızca o sözlükte** yaşar — diske yazılmaz, log'a
düşmez (ADR-012), tıpkı Gradio tarafındaki gibi.

**Agent önbelleği:** agent `(model, anahtarı olan sağlayıcılar)` çiftine göre önbelleklenir.
Her soruda yeniden kurulsaydı 1,1 GB'lık embedding modeli her seferinde yüklenirdi.

**CORS:** varsayılan olarak `localhost:3000` ve `127.0.0.1:3000`'e izin verilir. Docker'da
da aynısı geçerlidir — tarayıcı her iki servise de **host'tan** eriştiği için konteyner
adları buraya hiç girmez. Başka bir adresten sunacaksanız `CORS_ORIGINS` ortam değişkeni
ile değiştirin.

### 🌐 Next.js arayüzü (`web/`)

Next.js 16 (App Router) + React 19 + Tailwind CSS 4. Kalıcı sol kenar çubuğu ile beş görünüm
arasında geçiş yapılır; sekme yığını yoktur.

| Dosya | Sorumluluk |
|---|---|
| `web/app/page.tsx` | Kabuk: kenar çubuğu, görünüm yönlendirme, açık/koyu tema düğmesi |
| `web/components/Chat.tsx` | Sohbet — kaynaklar, araç izi ve metrikler **cevabın kendi kartında** |
| `web/components/Providers.tsx` | Anahtar girişi ve aktif model seçimi |
| `web/components/LocalModels.tsx` | Ollama modellerini listeler / indirir / siler |
| `web/components/Metrics.tsx` | Model bazında özet + satır içi çubuk grafik + koşu geçmişi |
| `web/components/Evaluation.tsx` | Çoklu model karşılaştırması, öncesinde maliyet tahmini |
| `web/components/ui.tsx` | Card / Button / Badge / Input / Select / tablo ilkelleri |
| `web/lib/api.ts` | Tipli API istemcisi, oturum kimliği yönetimi |
| `web/lib/format.ts` | Türkçe sayı/süre/maliyet biçimlendirme (`ui_state` kurallarının aynısı) |

Tema tercihi `localStorage`'da tutulur; ilk açılışta işletim sistemi tercihine
(`prefers-color-scheme`) düşer.

---

### 🐍 Gradio arayüzü (`gradio_app.py`)

[Gradio](https://gradio.app) 5.x ile yazılmıştır; sohbet için `gr.ChatInterface` kullanır.
Node.js istemediği için "yalnızca Python" ile çalışmak isteyenlerin yolu budur.

---

## Beş ekran

Her iki arayüz de aynı beş ekranı sunar (Next.js'te kenar çubuğu, Gradio'da sekme):

| Ekran | Ne yapar |
|---|---|
| 💬 **Sohbet** | Soru sorar; her cevabın yanında kaynaklar, araç izi, süre, giriş/çıkış token'ı, maliyet ve yerel modelde **tepe CPU / RAM / GPU VRAM** durur |
| ⚙️ **Sağlayıcılar** | Anthropic / OpenAI / Gemini anahtarı girilir, aktif model seçilir |
| 📦 **Yerel Modeller** | Ollama modellerini listeler, ilerleme çubuğuyla indirir, siler |
| 📊 **Metrikler** | Model bazında koşu sayısı, ortalama süre, toplam giriş/çıkış token'ı, atıf, kapı isabeti, tepe kaynak tüketimi ve maliyet; geçmiş tablosu |
| 🎯 **Değerlendirme** | Seçilen modelleri 13 soruluk sabit setle karşılaştırır |

### 🧠 Sohbet belleği ve kullanıcı adı

Sohbet **son 5 turu** hatırlar, böylece *"peki ya müdür seviyesinde?"* gibi takip soruları
çalışır. Buradaki incelik şu: bu metin tek başına hiçbir belgeye benzemediği için skor
kapısı onu konu dışı sayıp **reddederdi**. Bu yüzden yalnızca **arama sorgusu** bir önceki
soruyla genişletilir; modele giden mesajlarda kullanıcının kendi yazdığı cümle durur.
Reddedilen cevaplar belleğe **girmez** — girseydi bir sonraki aramayı kirletirlerdi.

Sohbet ekranındaki ad alanı sistem promptunun sonuna **tek cümle** ekler. Ad boşken prompt
birebir eski hâlindedir (bunu bir test korur), çünkü prompta eklenen her fazladan cümlenin
yerel 7B modelde araç çağrısını bastırabildiği daha önce ölçüldü. Ad **oturumda** kalır;
ölçüm veritabanına yazılmaz.

### 🖥️ Kaynak tüketimi

Yerel modellerde her cevap için **tepe CPU %**, **tepe RAM** ve Ollama'nın `/api/ps`
ucundan okunan **GPU VRAM** kaydedilir. Ölçülemeyen değer `—` olarak gösterilir; `0`
**yazılmaz**. `GPU 0 MB` ile "ölçülemedi" farklı iki bilgidir: birincisi modelin CPU'da
çalıştığı anlamına gelir.

### 🔒 Anahtarlar nerede tutuluyor

Arayüzden girilen API anahtarları **yalnızca o oturumun belleğinde** tutulur: diske
yazılmaz, log'a düşmez, metrik veritabanına girmez, ekranda yalnız son 4 karakteri
görünür. Sekmeyi kapattığınızda kaybolurlar. `credentials.py` modülünde hiçbir kalıcılık
çağrısı bulunmadığı bir testle korunur (ADR-012).

CLI ve Docker için ortam değişkenleri (`ANTHROPIC_API_KEY` vb.) **okuma yönünde** yedek
olarak çalışmaya devam eder.

### 💵 Maliyet ve fiyat tablosu

Fiyatlar `config/model_prices.json` dosyasında, kaynak ve tarihiyle tutulur ve **elle**
güncellenir. Şu an yalnız **Anthropic fiyatları doğrulanmış kaynaktan** girilidir;
OpenAI ve Gemini `null`'dur — bu modellerde arayüz **"fiyat girilmedi"** yazar,
`$0` **yazmaz**. Toplamların yanında kaç koşunun fiyatının bilindiği (`2/4 koşu`)
ayrıca gösterilir (ADR-013).

### 📊 Ölçüm verisi hakkında

Her soru — reddedilenler dahil — `storage/metrics.db` içine kaydedilir: model, süre,
token, maliyet, atıf sayısı, kapı kararı. Reddedilenlerin de kaydedilmesi kasıtlıdır;
"konu dışı filtresi ne kadar isabetli" sorusu ancak böyle cevaplanabilir.
⚠️ **Soru metinleri de kaydedilir** — gerçek bir dağıtımda bu kişisel veri içerebilir.

---

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
│                                                                          │
│   Next.js (web/)          Gradio               CLI                       │
│   React 19 + Tailwind     (gradio_app.py)      (src/rag/cli.py)          │
│   :3000                   :7860                stdout                    │
│        │                       │                    │                    │
│        │ HTTP + X-Session-Id   │                    │                    │
│        ▼                       │                    │                    │
│   ┌─────────────────────┐      │                    │                    │
│   │ FastAPI :8000       │      │                    │                    │
│   │ src/rag/api.py      │      │                    │                    │
│   │ ├ serialize.py JSON │      │                    │                    │
│   │ └ ui_state.py karar │◄─────┘  (aynı fonksiyonlar, HTTP'siz)          │
│   └──────────┬──────────┘                           │                    │
└──────────────┼──────────────────────────────────────┼────────────────────┘
               └──────────────────┬───────────────────┘
                                  │ soru (Türkçe, doğal dil)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│         AGENT — LangGraph durum makinesi (src/rag/graph.py)               │
│         agent.py yalnızca ince bir cephe (facade)                        │
│                                                                          │
│   score_gate ──(güvensiz)──► refuse            ① LLM'den ÖNCE kapı       │
│       │ (güvenli)                                                        │
│       ▼                                                                  │
│   llm_turn ──(tool çağrısı)──► run_tools ──┐   ② max 3 tur               │
│       │  ▲                                  │                            │
│       │  └──────────────────────────────────┘                            │
│       │ (hiç araca danışmadan cevapladı) ──► inject_context ──┘          │
│       ▼                                                                  │
│   citation_check ──(atıf yok)──► repair ──► citation_check ──► no_info   │
│       │ (atıflı)                                ③ atıf post-check         │
│       ▼                                                                  │
│     finish                                                               │
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
| Agent akışı | **LangGraph durum makinesi** (`src/rag/graph.py`) | Dallanma gerçek: atıf onarım turu, bağlam enjeksiyonu, çok sağlayıcılı yönlendirme. Her adım ayrı düğüm olduğu için akış denetlenebiliyor ve düğüm başına ölçüm alınabiliyor |
| Retrieval / chunking | **Ham Python** (LangChain/LlamaIndex retriever'ı yok) | Bölüm-sayfa metadata'sını chunk'a iliştirip atıfta göstermek bu case'in çekirdeği; hazır retriever'ların varsayılan metadata'sı bunu vermiyor, override etmek yazmaktan uzun sürüyordu |
| Embedding | **`intfloat/multilingual-e5-base`** | Türkçe'de güçlü, lokal çalışır (API anahtarı gerektirmez), `query:`/`passage:` önek şeması asimetrik aramada belirgin kazanç sağlar |
| Vektör deposu | **ChromaDB** (`PersistentClient`) | Kurulum gerektirmeyen gömülü depo; 276 chunk için sunucu tabanlı bir çözüm gereksiz |
| Retrieval | **Hibrit BM25 + dense, RRF (k=60)** | İkisi farklı hataları yapıyor: dense `OPS-PRO-003` gibi belge kodlarını yakalayamıyor, BM25 anlamsal yakınlığı göremiyor. RRF **sıra** birleştirdiği için skor normalizasyonu ve ağırlık ayarı gerektirmez |
| LLM | **Takılabilir katman, varsayılan Ollama** | Case lokal çalışabilirliği tercih ediyor. Yerel model yetersiz kalırsa `LLM_PROVIDER` ile buluta geçiş tek satır |

> 📌 **Bu karar bir kez değişti.** İlk sürüm agent döngüsünü de ham Python ile yazmıştı
> ([ADR-001](docs/02-karar-kaydi.md)) ve o ölçekte gerekçesi doğruydu: tek sağlayıcı, tek
> düz akış. Sağlayıcı Merkezi genişlemesi bu varsayımı bozunca döngü LangGraph'a taşındı
> ([ADR-011](docs/02-karar-kaydi.md), ADR-001'i geçersiz kılar). **Retrieval, chunking ve
> loader'lar hâlâ tamamen kendi kodumuz** — framework yalnızca agent akışını yönetiyor.
>
> Migrasyonun kabul kriteri sertti: `tests/test_agent.py` **tek karakter değişmeden**
> geçmek zorundaydı. Geçti (dosya hash'i birebir aynı), yani dışarıdan görünen davranış
> korundu. Bedeli iki bağımlılık: `langgraph` ve `langchain-core`.

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

Üç katmanlı güvenlik ağı — her katman grafikte ayrı bir düğüm:

1. **Skor kapısı** (`score_gate`, LLM'den önce). Retrieval skorları yetersizse LLM hiç
   çağrılmaz.
2. **Grounded sistem promptu** (`llm_turn`). Model yalnızca tool sonucuna dayanmaya
   yönlendirilir.
3. **Atıf post-check** (`citation_check`). Hiçbir `[n]` atfı gerçek bir kaynağa
   eşleşmiyorsa önce `repair` bir kez daha dener, o da tutmazsa cevap "bilgi bulamadım"
   ile değiştirilir.

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

Altı servis kalkar:

| Servis | Port | İmaj | Ne yapar |
|---|---|---|---|
| `web` | **3000** | `node:22-alpine` (229 MB) | Next.js arayüzü |
| `api` | **8000** | Python (7,4 GB) | FastAPI backend |
| `rag` | **7860** | Python (aynı imaj) | Gradio arayüzü |
| `ingest` | — | Python (aynı imaj) | İndeksi bir kez üretip çıkar; diğerleri bunu bekler |
| `ollama` | — | `ollama/ollama` | Yerel LLM sunucusu |
| `ollama-init` | — | `ollama/ollama` | Sohbet modelini çeker, sonra çıkar |

`ingest`, `api` ve `rag` **aynı Python imajını** paylaşır — yalnızca `command` satırları
farklı. Üçü için ayrı imaj derlemek 7,4 GB'ı üçe katlardı. `ingest`'in ayrı servis olması
kasıtlı: üç servisin aynı anda `ingest.py` çalıştırıp `storage/` üstüne yazma yarışı bu
sayede oluşmuyor — diğerleri `service_completed_successfully` koşuluyla onu bekliyor.

**Next.js tarafında iki incelik var:**

`NEXT_PUBLIC_API_URL` **derleme argümanıdır**, çalışma zamanı değişkeni değil. `NEXT_PUBLIC_*`
değişkenleri derleme sırasında JS paketinin içine gömülür; `environment:` altına yazmak
hiçbir işe yaramaz. Bu yüzden `docker-compose.yml` içinde `build.args` altında duruyor.

`web/.dockerignore` **zorunlu**. Olmadığında `node_modules` ve `.next` derleme bağlamına
giriyor ve daemon'a 287 MB gönderiliyordu — üstelik imaj onları `COPY --from=deps` ile zaten
yeniden üretiyor, yani tamamı boşa. Dosya eklenince bağlam ihmal edilebilir boyuta indi.

Elle `ollama pull` **gerekmez**: `ollama-init` servisi modeli kendisi çeker (ilk `up`
~4,7 GB indirir, uzun sürer) ve diğer servisler indirme bitene kadar bekler.

> ⚠️ **Yerel Ollama'yı önce durdurun.** Konteyner Ollama'sı ile makinedeki Ollama aynı
> ~4,7 GB modeli aynı anda belleğe alır. 16 GB'lık bir makinede bu ölçüldü: boş RAM
> 1 GB'ın altına indi ve **Docker daemon çöktü**. Docker'ı kullanacaksanız yerel Ollama
> servisini kapatın; yerel kurulumu kullanacaksanız `docker compose down` yapın.

`ollama` ayrı konteynerde çalışır; `api` ve `rag` ona `http://ollama:11434` üzerinden erişir. Model, adlandırılmış `ollama` volume'ünde kalıcıdır;
ikinci `up` çağrısında tekrar indirilmez.

Konteynerdeki Ollama'nın portu **bilerek host'a açılmıyor**: makinede yerel bir Ollama
kuruluysa (kurulum betiği zaten onu öneriyor) 11434 portu doluydu ve `docker compose up`
hiç başlamıyordu. Konteynere host'tan erişmek gerekirse `docker compose exec ollama …`
kullanılabilir.

`.dockerignore` sanal ortamı, indeksi ve planlama dokümanlarını build bağlamının dışında
tutar — imaj **8,98 GB → 7,37 GB** küçülür, uygulama katmanı 1,4 MB'a iner. Kalan boyut
büyük ölçüde PyTorch ve imaja önceden gömülen embedding modelidir (2,27 GB); bu kasıtlıdır,
ilk çalıştırmada 1,1 GB'lık indirmeyi bekletmemek için.

Dağıtımı doğrulamak için:

```bash
docker compose exec rag python scripts/smoke_test.py
```

Sabit bir soru setini çalıştırır; her soru için skor kapısı, atıf ve tool izini kontrol
edip `Başarısız kontrol sayısı: 0` bekler.

---

## Testler

```bash
pytest -q                              # tümü
pytest -q -m "not integration"         # yalnız birim testleri
pytest -q -m integration               # yalnız entegrasyon (gerçek belgeler + indeks)
ruff format . && ruff check .          # biçim + lint
```

**329 test geçiyor, satır kapsamı %95.** Entegrasyon testleri hayali fikstürlerle değil,
`data/` altındaki **gerçek altı belgeyle** çalışır; assertion'lardaki her sayı ölçülmüştür.
LLM çıktısının metni hiçbir zaman test edilmez (deterministik değildir) — agent döngüsünün
kontrol akışı mock'lanmış bir LLM ile test edilir.

Kapsam dışı bırakılan üç dosya var ve gerekçeleri aynı: içlerinde test edilecek karar yok.
`llm.py` sağlayıcı SDK'larını sarar, `gradio_app.py` yerleşimdir, `api.py` yönlendirmedir —
her birinin karar mantığı test edilen bir modüle çekilmiştir (`ui_state.py`, `serialize.py`).

Next.js tarafı için:

```bash
cd web
npm run lint          # ESLint (React 19 kuralları dahil)
npx tsc --noEmit      # tip kontrolü
```

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
8. **Atıf *seçimi* her zaman isabetli değil.** Aksef sorusunda cevap doğru bölümden
   geliyor ama model `Bölüm 1` ve `4.2`'yi işaretleyebiliyor. Retrieval sıralaması doğru;
   hangi kaynağı işaretleyeceği modele kalmış. Bulut sağlayıcıya geçmek
   (`LLM_PROVIDER=anthropic`) bunu belirgin şekilde iyileştirir.
9. **Retrieval, eşiğe çok yakın skorlarda tam belirlenimci değil.** Chroma'nın HNSW
   yaklaşık komşuluk araması, skorların neredeyse eşit olduğu (tipik olarak konu dışı)
   sorgularda ilk sırayı değiştirebiliyor: ölçülen örnek, aynı konu dışı soru için
   `0,781 / 0,00` ve `0,782 / 3,64`. Alan içi sorularda skorlar koşular arasında birebir
   aynı çıktı ve kapı kararı her iki durumda da değişmedi.

### Belirlenimlilik: `temperature=0` neden zorunlu

İlk sürümde `OllamaClient` örnekleme sıcaklığı ayarlamıyordu; Ollama varsayılanı **0.8**.
Sonuç, aralıklı ve teşhisi zor bir hataydı: **aynı** soru, **aynı** indeks, bazen atıflı
doğru cevap, bazen "bilgi bulamadım". Ölçüm sırasında yakıt limiti sorusu bir koşuda
`1.500 TL/ay` cevabını verdi, bir sonraki koşuda elendi — çünkü model o üretimde `[n]`
işaretini atlamıştı ve atıf post-check'i (3. katman) cevabı doğru şekilde reddetti.
0.8'de üretilen metinlerde bozuk Türkçe de görüldü (`"[1] kayieńde belirtilen..."`).

`LLM_TEMPERATURE=0` ile aynı istem her seferinde **birebir aynı** cevabı veriyor; smoke
test üç ardışık koşuda kelimesi kelimesine aynı çıktıyı üretti. Ayrıca cevap hâlâ atıfsız
kalırsa agent **bir kez** açık bir talimatla yeniden soruyor (`CITATION_REPAIR`); o da
başarısız olursa cevap "bilgi bulamadım" ile değiştiriliyor. Yani doğru cevabı kaybetme
riski azaltıldı, ama kaynaksız cevap verme riski hiç alınmadı.

**Geliştirme fikirleri:** cross-encoder yeniden sıralama, sorgu genişletme (HyDE), RAGAS ile
otomatik değerlendirme, belge değişikliğini izleyen artımlı ingest, çok turlu sohbet bağlamı.

---

## Bölüm 2 — Satış ve Talep Analizi

Dört pazar × 124 ay (2016-01 → 2026-04) ilaç satış verisi üzerinde case'in yedi analiz
sorusu. Hesaplar test edilmiş modüllerde, notebook onları çağırıp yorumluyor.

```bash
pip install -r requirements-analysis.txt
jupyter lab notebooks/analiz.ipynb        # Restart & Run All ≈ 1,5 dk
```

| Dosya | Sorumluluk |
|---|---|
| `src/analysis/load.py` | Üç satırlık hiyerarşik başlığı tidy çerçeveye çevirir (374 seri × 124 ay) |
| `src/analysis/clean.py` | Yedi ölçülmüş veri sorununu düzeltir, kalite raporu döndürür |
| `src/analysis/metrics.py` | Net Kutu, birim fiyat, pazar payı, HHI, STL mevsimselliği |
| `src/analysis/forecast.py` | `naive`/`snaive`/`ma3`/global LightGBM + walk-forward |
| `src/analysis/plots.py` | Ortak Türkçe grafik stili, `figures/` PNG yazıcı |
| `notebooks/analiz.ipynb` | A1–A7, her görevde grafik + teknik yorum + iş yorumu |

### 🚨 En kritik adım: MF ölçek düzeltmesi

`MF Oran` kolonu **B Pazarı'nda yüzde (0–100)**, diğer üç pazarda oran (0–1)
ölçeğinde. Düzeltilmezse case'in `Net Kutu = Brüt Kutu × (1 − MF Oran)` tanımı
negatif sonuç veriyor:

| B Pazarı / Şirket 1 / Ürün-FR, 2016-01 | Değer |
|---|---|
| Ham `MF Oran` | 9,54 |
| Oran olarak okunursa birim fiyat | **−0,88 TL** ❌ |
| 100'e bölününce birim fiyat | **8,32 TL** ✔ |

Karşılaştırma: A Pazarı/Ürün-A aynı dönemde 10,28 TL. Düzeltme yapılmadan **A4, A6 ve
A7 görevlerinin tamamı yanlış sonuç verir**. Kural sabit "B Pazarı" kontrolüyle değil,
**grup medyanı > 1 ⇒ yüzde ölçekli** program tespitiyle uygulanıyor; veri değişirse
kırılmaz. Testle korunuyor: `test_only_market_b_is_detected_as_percent_scaled`.

### Bilinen sınırlılıklar (Bölüm 2)

1. **Kısa seriler.** `C Pazarı/Ürün 1` yalnız **bir** ayında satış görmüş,
   `D Pazarı/Ürün 78` on bir ayında. Bu iki seri için mevsimsellik ve tahmin
   matematiksel olarak mümkün değil — gizlenmiyor, "yetersiz geçmiş" etiketiyle
   ayrı tabloda raporlanıyor. Global LightGBM'in eğitim havuzunda kalıyorlar.
2. **Ürün setleri pazarlar arası ayrık.** Şirket 1'in hiçbir ürünü birden fazla
   pazarda yok (A'da Ürün-A…J, B'de FP…FS, C'de 1–2, D'de 77–78). Case'in "aynı
   ürünün farklı pazarlardaki örüntüsü" sorusu bu veriyle **ürün seviyesinde
   cevaplanamıyor**; karşılaştırma pazar seviyesine taşındı.
3. **Fiyatlar nominal.** Veri setinde TÜFE yok, reel fiyat karşılaştırması yapılmadı.
4. **A4 korelasyondur, nedensellik değil.** Yüksek MF satışı düşürüyor olabileceği
   gibi, düşeceği bilinen aylarda MF artırılıyor da olabilir.
5. **Mevsimsellik eşiği satış görülen aya bakar**, satır sayısına değil. Satır
   sayısına bakan bir eşik `C/Ürün 1` için "mevsimsellik gücü 0,99" uyduruyordu.

---

## Proje yapısı

```
rag-demo/
├── src/rag/                 Bölüm 1 çekirdeği
│   ├── agent.py graph.py    agent döngüsü + LangGraph durum makinesi
│   ├── retriever.py index.py chunker.py normalize.py
│   ├── loaders/             pdf / docx / xlsx okuyucuları
│   ├── tools.py prompts.py models.py config.py
│   ├── llm.py catalog.py    sağlayıcı soyutlaması + model kataloğu
│   ├── credentials.py       oturum içi anahtar saklama (diske yazmaz)
│   ├── memory.py metrics.py pricing.py resources.py evaluation.py
│   ├── ollama_admin.py      yerel model listele/indir/sil
│   ├── ui_state.py          ⭐ arayüzden bağımsız karar mantığı
│   ├── serialize.py         ⭐ API JSON şekilleri (test edilir)
│   ├── api.py               ⭐ FastAPI backend  (:8000)
│   └── cli.py               terminal arayüzü
├── src/analysis/            Bölüm 2: load, clean, metrics, forecast, plots
├── web/                     ⭐ Next.js arayüzü (:3000)
│   ├── app/  components/  lib/
│   └── Dockerfile  .dockerignore  package.json
├── gradio_app.py            ⭐ Gradio arayüzü (:7860)
├── scripts/                 ingest · setup · run_web · smoke_test · package
├── tests/                   36 dosya, 329 test
├── config/                  model_prices.json · eval_set.json
├── notebooks/               demo.ipynb (Bölüm 1) · analiz.ipynb (Bölüm 2)
├── data/                    kaynak belgeler (git'te yok, ZIP'te var)
├── docs/                    PRD / TRD / ADR / veri keşif bulguları
├── Dockerfile               Python imajı (ingest + api + rag ortak)
└── docker-compose.yml       altı servis
```

---

## Teslim notu

`data/` klasörü ve `AI Engineer/` `.gitignore` içindedir (kaynak belgeler repoya
işlenmez), ama **teslim ZIP'inde ikisi de vardır** — aksi halde `ingest.py`
çalıştırılamaz ve Bölüm 2 notebook'u açılamaz.

ZIP'te `web/node_modules` **yoktur** (yüzlerce MB, platforma özgü ikililer içerir).
Next.js arayüzü ilk çalıştırmada bağımlılıkları kendisi kurar: `scripts/run_web.py`
`node_modules` yoksa `npm install` çağırır. Docker yolunda buna hiç gerek yoktur.
`web/package-lock.json` pakette olduğu için kurulum yeniden üretilebilir.

Paketi yeniden üretmek için:

```bash
python scripts/package.py     # → rag-demo.zip
```

⚠️ **`git archive` kullanmayın.** Önceki paketin bayatlamasının sebebi buydu: `web/`,
`gradio_app.py` ve `api.py` hâlâ untracked olduğu için sessizce dışarıda kalıyorlardı;
`data/` ve `AI Engineer/` ise bilerek gitignore'da ama teslimde bulunmak zorunda.
`scripts/package.py` çalışma ağacından açık bir dışlama listesiyle paketler.

Paketi doğrulamanın tek geçerli yolu **açıp içinden test çalıştırmaktır** — dosya listesine
bakmak korpusun kullanılabilir olduğunu kanıtlamaz:

```bash
cd /tmp/kontrol && unzip …/rag-demo.zip && pytest -q
```
