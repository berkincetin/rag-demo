# RAG Agent — Şirket Bilgi Asistanı

Altı şirket belgesi (2 PDF, 2 DOCX, 2 XLSX) üzerinde **Türkçe** doğal dilde soru-cevap
yapan, tool-calling kullanan ve her cevabı **dosya/bölüm/sayfa atfıyla** kaynaklandıran
lokal çalışabilir bir RAG agent'ı.

Bilmediğini söyler, konu dışı soruları kibarca reddeder, hiçbir cevabı kaynaksız vermez.

---

## Kurulum — üç komut

```bash
pip install -r requirements.txt
python scripts/setup.py     # Ollama'yı kontrol eder, sohbet modelini çeker
python scripts/ingest.py
streamlit run app.py
```

`setup.py` Ollama kurulu değilse **kurmaz** — platformunuza uygun kurulum komutunu
yazdırıp durur; kurulumu siz çalıştırırsınız. Kuruluysa modeli çeker (kuantize sürüm
zaten varsa tekrar indirmez).

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

---

## Arayüz — beş sayfa

| Sayfa | Ne yapar |
|---|---|
| 💬 **Sohbet** | Soru sorar; cevabın altında **aktif model**, süre, giriş/çıkış token'ı, maliyet ve yerel modelde **tepe CPU / RAM / GPU VRAM** gösterir. Kenar çubuğunda ad alanı ve sohbet belleği vardır. Kaynaklar ve araç izi panelleri korunur |
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

Kenar çubuğundaki ad alanı sistem promptunun sonuna **tek cümle** ekler. Ad boşken prompt
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

Elle `ollama pull` **gerekmez**: `ollama-init` servisi modeli kendisi çeker (ilk `up`
~4,7 GB indirir, uzun sürer) ve `rag` servisi indirme bitene kadar bekler.

> ⚠️ **Yerel Ollama'yı önce durdurun.** Konteyner Ollama'sı ile makinedeki Ollama aynı
> ~4,7 GB modeli aynı anda belleğe alır. 16 GB'lık bir makinede bu ölçüldü: boş RAM
> 1 GB'ın altına indi ve **Docker daemon çöktü**. Docker'ı kullanacaksanız yerel Ollama
> servisini kapatın; yerel kurulumu kullanacaksanız `docker compose down` yapın.

`localhost:8501` arayüzü açar; `ollama` ayrı konteynerde çalışır ve `rag` servisi ona
`http://ollama:11434` üzerinden erişir. Model, adlandırılmış `ollama` volume'ünde kalıcıdır;
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
kırılmaz. Testle korunuyor: `test_mf_olcek_tespiti_yalnizca_b_pazarini_yuzde_kabul_eder`.

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

## Teslim notu

`data/` klasörü `.gitignore` içindedir (kaynak belgeler repoya işlenmez). **Teslim ZIP'ine
`data/` elle eklenmelidir** — aksi halde `python scripts/ingest.py` çalıştırılamaz.
Aynı şey Bölüm 2 için de geçerli: `AI Engineer/bolum2_veriseti.xlsx` repoda değil,
ZIP'e elle konmalı, yoksa notebook çalışmaz.
