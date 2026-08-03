# Docker Uçtan Uca Test Raporu — Bölüm 1 RAG Agent

**Tarih:** 2026-08-02 · **Ortam:** Windows 11 host, Docker 28.3.3, Linux konteynerler
**Kapsam:** Sıfırdan `docker build` → stack ayağa kaldırma → her katmanın uçtan uca testi

Bu doküman test edilen **her özelliği** üç başlıkta ele alır: *kullanılan teknoloji*,
*neden seçildiği*, *nasıl çalıştığı* — ve o özelliğin bu testte üretilen **ölçülmüş
kanıtı**. Rapor sırasında bulunan üç kusur ve çözümleri de belgelenmiştir.

> ℹ️ **Kapsam notu.** Rapor 2026-08-02 tarihli koda aittir; Sağlayıcı Merkezi
> genişletmesinden (LangGraph, çok sayfalı arayüz, metrik deposu, sohbet belleği,
> kaynak ölçümü) **öncesini** ölçer. Bu bölümlerin doğrulaması PROGRESSION.md'deki
> Sağlayıcı Merkezi tablosunda ve testlerdedir. Aşağıdaki Docker ölçümleri
> (imaj boyutu, konteynerde chunk sayısı, ağ) hâlâ geçerlidir.

---

## 0. Yönetici özeti

| Katman | Durum | Kanıt |
|---|---|---|
| Docker imaj derlemesi | ✅ | `rag-demo-rag` built, 7,37 GB |
| Servisler arası ağ | ✅ | `rag` → `http://ollama:11434` → "Ollama is running" |
| Belge yükleme + chunking (konteynerde) | ✅ | 219 bölüm → 276 chunk, host ile **birebir aynı** |
| İndeks kurma (Chroma + BM25) | ✅ | 184 sn, 3 artefakt yazıldı |
| Hibrit retrieval + RRF | ✅ | 7 probe testi konteynerde geçti |
| Güven kapısı (konu dışı / bilmiyorum) | ✅ | 2 konu dışı soru reddedildi, tool çağrılmadı |
| Tool-calling agent döngüsü | ✅ | Model kendi araç çağrısını yaptı, izde görünür |
| Atıflandırma | ✅ | 7/7 geçerli soru atıflı (düzeltme öncesi 6/7) |
| Streamlit arayüzü | ✅ | HTTP 200, `/healthz` = ok |
| Test süiti (konteynerde) | ✅ | **103 test** (77 birim + 26 entegrasyon) |
| Belirlenimlilik | ✅ | 3 ardışık koşu kelimesi kelimesine aynı |

**Bulunan ve düzeltilen kusurlar:** ① örnekleme sıcaklığı ayarlanmamıştı (atıf kaybına yol
açıyordu), ② `.dockerignore` yoktu (imaj 1,6 GB fazla), ③ case arşivi imaja kopyalanıyordu.

---

## 1. Konteynerleştirme

### Kullanılan teknoloji
Docker + Docker Compose. Temel imaj `python:3.11-slim`. İki servis: `rag` (uygulama) ve
`ollama` (LLM sunucusu). Adlandırılmış volume `ollama`, bind mount `./data` ve `./storage`.

### Neden
Case "çalıştırılabilir kod" istiyor ve sistemin iki ayrı çalışan parçası var (Python
uygulaması + model sunucusu). Compose bunları tek komutla ayağa kaldırır ve aralarındaki
ağı DNS ile çözer — değerlendiricinin elle port/IP ayarlaması gerekmez. `slim` tabanı
seçildi çünkü tam `python` imajı ~700 MB fazladan derleme aracı taşır ve bize gerekmez.

### Nasıl çalışır
`docker-compose.yml` `rag` servisine `OLLAMA_BASE_URL: http://ollama:11434` enjekte eder.
Compose'un dahili DNS'i `ollama` adını konteyner IP'sine çözer, böylece `localhost`
varsayımı ortadan kalkar. Model ağırlıkları adlandırılmış volume'de kaldığı için ikinci
`up` çağrısında 4,7 GB yeniden indirilmez. `storage/` bind mount olduğundan host'ta
üretilmiş indeks konteynerde de kullanılabilir; yoksa `CMD` içindeki
`[ -f storage/chunks.jsonl ] || python scripts/ingest.py` kontrolü onu üretir.

### Ölçülen kanıt

```
SERVICE   STATUS         PORTS
ollama    Up 3 seconds   0.0.0.0:11434->11434/tcp
rag       Up 3 seconds   0.0.0.0:8501->8501/tcp

$ docker compose exec rag python -c "...requests.get(OLLAMA_BASE_URL)"
OLLAMA_BASE_URL = http://ollama:11434
Ollama is running
```

### 🔴 Bulunan kusur 1 — `.dockerignore` yoktu

Build bağlamı ölçüldüğünde `.venv` klasörünün **1,52 GB** olduğu ve `COPY . .` adımıyla
imaja kopyalandığı görüldü. Bu, Linux konteynerde **hiç çalışmayacak** bir Windows sanal
ortamıdır: içindeki `python.exe` ve Windows'a derlenmiş `.pyd` dosyaları ölü ağırlıktır.
Ek olarak case arşivi (`AI Engineer/`, korpusun ikinci kopyası + Bölüm 2 veri seti) ve
planlama dokümanları da imajdaydı.

`.dockerignore` eklendikten sonra:

| Ölçüm | Önce | Sonra |
|---|---|---|
| İmaj boyutu | **8,98 GB** | **7,37 GB** |
| `/app` (uygulama katmanı) | ~1,5 GB | **1,4 MB** |
| `COPY . .` süresi | 76,1 sn | 0,3 sn |

Kalan 7,37 GB'ın büyük kısmı PyTorch ve imaja **kasıtlı** olarak gömülen embedding
modelidir (`~/.cache/huggingface` = 2,27 GB) — ilk çalıştırmada 1,1 GB indirmeyi
beklememek için Dockerfile'da önceden çekilir.

---

## 2. Belge yükleme (loaders)

### Kullanılan teknoloji
`pypdf` (PDF), `python-docx` (DOCX), `pandas` + `openpyxl` (XLSX). Format başına ayrı
yükleyici, ortak `RawSection` veri modeli, `glob` ile dosya keşfi.

### Neden
Üç format üç farklı yapısal probleme sahip ve tek bir genel amaçlı ayrıştırıcı hepsini
bozar. LangChain gibi bir çerçevenin hazır yükleyicileri kullanılmadı çünkü bu korpusun
üç somut tuzağı (aşağıda) özel işlem gerektiriyordu ve çerçeve içinde bunları değiştirmek,
sıfırdan yazmaktan daha zahmetliydi.

### Nasıl çalışır

**PDF:** Sayfa sayfa metin çıkarılır, KÜB bölüm numaraları (`4.3`, `6.6` …) regex ile
yakalanır. İki filtre birlikte çalışır: (a) KÜB bölüm beyaz listesi, (b) bölüm
numaralarının **monoton artması** şartı. Dipnotlar (`7 Plasebodan istatistiksel…`) başlık
gibi göründüğü için tek başına regex yetmez — ham eşleşme Aksef'te 28, Duxet'te 33 satır
buluyordu; iki filtre sonrası ikisi de doğru **20 bölüme** indi.

**DOCX:** `document.paragraphs` **tabloları tamamen atlar**. Bunun yerine
`document.element.body` üzerinden `CT_P` (paragraf) ve `CT_Tbl` (tablo) düğümleri **belge
sırasıyla** dolaşılır; tablolar Markdown'a çevrilip ait oldukları bölüme eklenir. Ayrıca
`paragraph.style` bazı paragraflarda `None` döndüğü için `getattr` ile korunur.

**XLSX:** Başlık satırı sabit değildir. `detect_header_row()` ilk 10 satırı tarar, doluluk
oranı ≥ %60 olan en dolu satırı başlık kabul eder. Her satır bölünmeden tek bir chunk olur
— bir SSS satırı zaten kendi içinde tam bir soru-cevaptır.

### Ölçülen kanıt (konteyner içinde)

```
$ docker compose exec -e STORAGE_DIR=/tmp/testidx rag python scripts/ingest.py
Sections: 219  Chunks: 276
    34  Aksef 500 mg FKTB_Onaylı KUB.pdf
   100  Anonim_Urun_Taksonomi_100Satir.xlsx
    63  Duxet 30 mg GRSK_Onaylı KUB.pdf
    15  arac_kullanim_proseduru.docx
    45  calisan_sss_rehberi.xlsx
    19  ik_surecleri_politikası.docx
Completed in 184.3s
```

Host'ta (Windows/Python 3.10) ölçülen değerlerle **birebir aynı**. Bu, ayrıştırma
mantığının platform ve Python sürümünden bağımsız olduğunu kanıtlar. Türkçe karakterli
dosya adı (`ik_surecleri_politikası.docx`) Linux'ta da doğru bulundu.

---

## 3. Türkçe normalizasyon

### Kullanılan teknoloji
Elle yazılmış `fold_tr()` — Türkçe harf eşlem tablosu + `unicodedata.normalize("NFKD")` +
birleşen işaret temizliği. Ayrıca BM25 için `bm25_tokens()`, 6 karakterlik önek kırpma.

### Neden
Korpusta DOCX'ler ASCII'ye indirgenmiş (`Insan Kaynaklari`), PDF'ler tam Türkçe
(`İnsan Kaynakları`) yazılmış — bazen aynı cümlede karışık. Doğru yazılmış bir sorgu
DOCX'i bulamıyordu. Hazır bir Türkçe stemmer eklemek yeni bağımlılık demekti; bu korpus
için önek kırpma ölçülerek yeterli bulundu.

### Nasıl çalışır
Türkçe eşlemeler **`casefold()`'dan önce** uygulanır. Sıra kritiktir: Python'un `lower()`
fonksiyonu `İ` harfini `i` + U+0307 (birleşen nokta) yapar ve bu işaret NFKD ayrıştırmasından
sağ çıkarak eşitliği bozar. Önce `İ → I` eşlenirse bu hiç oluşmaz.

BM25 tarafında ayrı bir problem var: BM25 **tam token eşleşmesi** yapar. Sorgudaki
`kontrendikasyonlari` ile indeksteki `kontrendikasyonlar` eklemeli bir dilde asla eşleşmez.
Tokenlar ilk 6 karaktere kırpılarak (sabit uzunlukta kırpma kökleştirme) bu kapatıldı.
Uzunluk ölçülerek seçildi:

| Önek | Aksef §4.3 doğru mu? | Duxet §4.6 doğru mu? |
|---|---|---|
| kırpma yok | ✗ | ✓ |
| 5 | ✗ | ✓ |
| **6 (seçilen)** | **✓** | **✓** |
| 7 | ✓ | ✗ |

Etkisi: §4.3'ün BM25 skoru **0,00 → 8,31**, sıralaması **3. → 1.**

---

## 4. Chunking ve atıf etiketleri

### Kullanılan teknoloji
Bölüm-farkındalıklı özel chunker; `max_chars=1200`, `overlap=150`.

### Neden
Sabit boyutlu kaydırmalı pencere, bir tabloyu veya bir soru-cevap satırını ortadan böler ve
atıf çözünürlüğünü yok eder. Bölüm sınırlarına saygı duyan bir bölme, her chunk'ın
"hangi belgenin hangi bölümünün kaçıncı sayfası" bilgisini taşımasını sağlar.

### Nasıl çalışır
XLSX satırları **asla bölünmez**. PDF/DOCX bölümleri önce paragraf sınırında bölünür; bir
paragraf tek başına sınırı aşıyorsa `_hard_split()` devreye girer ve satır sonu / cümle
sonu tercih ederek keser, `start += max(cut - overlap, 1)` hem örtüşmeyi hem ilerlemeyi
(sonsuz döngü yok) garanti eder.

Ayrıca bölüm başlığı yalnızca **arama metnine** eklenir, görüntülenen metne değil. Sebep
ölçüldü: KÜB §4.3'ün başlığı "Kontrendikasyonlar" ama bu kelime gövde metninde **hiç
geçmiyor**; başlık aranabilir olmadan o bölüm hiçbir ranker tarafından ayırt edilemiyordu.

### Ölçülen kanıt
219 bölüm → **276 chunk**. `max_chars` sınırını aşan chunk sayısı: **0**. (İlk uygulamada
232 chunk vardı ve 12'si sınırı aşıyordu, en büyüğü 9.681 karakterdi — `_hard_split`
eklenmeden önce KÜB'ün boş satır içermeyen uzun paragrafları hiç bölünmüyordu.)

---

## 5. İndeks: Chroma + BM25

### Kullanılan teknoloji
ChromaDB `PersistentClient` (kosinüs uzayı) + `rank_bm25.BM25Okapi` (pickle) +
`chunks.jsonl` (düz metin kayıtları). Embedding: `intfloat/multilingual-e5-base`.

### Neden
Chroma gömülü çalışır — 276 chunk için ayrı bir vektör veritabanı sunucusu işletmek
gereksiz karmaşıklıktır. e5-base Türkçe'de güçlüdür ve **lokal** çalışır (case lokal
çalışabilirliği tercih ediyor, API anahtarı gerektirmez). `chunks.jsonl` üçüncü artefakt
olarak tutulur çünkü `lookup_section` aracı ve denetim, vektör aramasından bağımsız olarak
ham metne erişmek zorundadır.

### Nasıl çalışır
e5 **asimetrik önek şeması** kullanır: belgeler `passage: ` , sorgular `query: ` önekiyle
gömülür. Bu şema modelin eğitildiği biçimdir; önek atlanırsa benzerlik skorları sistematik
olarak düşer. Gömme vektörleri normalize edilir, Chroma kosinüs uzaklığı döndürür,
retriever bunu `1 - distance` ile benzerliğe çevirir. Toplu işleme 64'lük gruplarla yapılır.

`build_index` her çağrıda koleksiyonu silip yeniden yaratır — idempotent, iki kez
çalıştırınca chunk sayısı iki katına çıkmaz (test ile korunuyor).

### Ölçülen kanıt
Üç artefakt da yazıldı (`chroma/`, `bm25.pkl`, `chunks.jsonl`); konteynerde 184,3 sn,
host'ta 55–120 sn. Embedding modeli imajda önceden mevcut (2,27 GB), bu yüzden ilk
çalıştırmada indirme beklemesi yok.

---

## 6. Hibrit retrieval ve RRF

### Kullanılan teknoloji
BM25 (leksik) + dense (anlamsal) paralel arama, **Reciprocal Rank Fusion** (k=60) ile
birleştirme. Her ranker'dan 20 aday alınır, füzyon sonrası `top_k` döndürülür.

### Neden
İki yöntem **farklı hatalar** yapar ve birbirini kurtarır:
- Dense arama `OPS-PRO-003` gibi belge kodlarını yakalayamaz (kod, anlamsal uzayda
  anlamsızdır) — BM25 yakalar.
- BM25 eşanlamlıyı ve yeniden ifade edilmiş soruyu göremez — dense görür.

RRF seçildi çünkü **sıra** birleştirir, skor değil. Kosinüs (0–1) ile BM25 (0–∞) farklı
ölçeklerdedir; skor birleştirmek normalizasyon ve ağırlık ayarı gerektirir, RRF ikisini de
gerektirmez.

### Nasıl çalışır
Her chunk için `score = Σ 1/(k + sıra)` hesaplanır. İki ranker'ın da üst sıralarda gördüğü
bir chunk, tek ranker'ın birinci sıraya koyduğu bir chunk'ı geçer. `k=60` büyük seçilir ki
ilk sıralar arasındaki fark yumuşasın ve tek bir ranker'ın aşırı güveni baskın olmasın.

**Önemli sınırlılık (ölçüldü):** RRF sıralamayı dense'ten devralmaz. KÜB §4.3 en yüksek
kosinüse sahipken (0,828) bile BM25 desteği olmadığı için 3. sıraya düşüyordu. Bir ranker
tamamen kör kalırsa füzyon onu kurtarmaz — bu yüzden §3'teki BM25 kökleştirme düzeltmesi
gerekti.

### Ölçülen kanıt (konteynerde çalıştırılan 7 probe testi)

| Probe | Neyi kanıtlıyor | Sonuç |
|---|---|---|
| `İnsan Kaynakları yıllık izin` | `fold_tr` — doğru yazılmış sorgu ASCII belgeyi buluyor | ✅ |
| `OPS-PRO-003` | BM25 katkısı — dense kodları bulamaz | ✅ |
| `Aksef kontrendikasyonları` → §4.3 | Başlık aranabilirliği + kökleştirme | ✅ |
| `Vitatin95 ürün müdürü` | XLSX satır retrieval | ✅ |
| `source_filter="Duxet"` | Belge filtresi | ✅ |
| Konu dışı soru güvensiz | Skor kapısı | ✅ |
| Alan içi soru güvenli | Skor kapısı | ✅ |

---

## 7. Güven kapısı — "bilmiyorum" ve konu dışı filtresi

### Kullanılan teknoloji
Üç katmanlı güvenlik ağı: (1) LLM'den **önce** deterministik skor kapısı, (2) temellendirilmiş
sistem promptu, (3) LLM'den **sonra** atıf post-check.

### Neden
Tek bir katman yetmez. Prompt'a "uydurma" demek bir *rica*dır, model uyabilir de uymayabilir
de. Skor kapısı ve atıf kontrolü ise **kod**tur — model ne yaparsa yapsın devreye girer.
Ayrıca skor kapısı LLM'i hiç çağırmadığı için konu dışı sorular anında ve bedavaya reddedilir.

### Nasıl çalışır ve eşikler neden böyle

Eşikler 10 geçerli + 6 konu dışı soruyla **ölçülerek** belirlendi:

| | kosinüs (ilk sonuç) | BM25 (ilk sonuç) |
|---|---|---|
| Geçerli sorular | 0,811 – 0,874 | 7,51 – 21,55 |
| Konu dışı sorular | 0,746 – **0,813** | 0,00 – **8,25** |

🚨 **Bantlar çakışıyor.** Konu dışı "Bana bir şiir yaz" kosinüs **0,813** alıyor — en zayıf
geçerli sorunun (**0,811**) üstünde. Yani **tek sinyalli bir eşik bu veride matematiksel
olarak imkânsızdır**: kosinüs eşiği 0,813'ün üstünde olmalı, ama o zaman geçerli sorular
için BM25 eşiği ≤ 7,55 olmalı ve bu da 8,25'lik konu dışı soruyu içeri alır.

Bu yüzden kapı **iki sinyalin birden** desteklemesini şart koşar:

```
güvenilir  ⇔  kosinüs ≥ 0.80  VE  bm25 ≥ 5.0
```

Not: e5 kosinüs değerlerini dar bir banda sıkıştırır (alakasız metinler bile 0,75+ alır).
Planın başlangıçtaki `MIN_COSINE=0.72` değeri bu yüzden **her** konu dışı soruyu içeri
alıyordu.

### Ölçülen kanıt
Notebook'un kalibrasyon hücresi: **7/7 geçerli soru geçti, 6/6 konu dışı soru elendi.**
PRD 8a ("Şirketin 2027 kâr hedefi" — alan içi ama belgede yok) kosinüs 0,778 ile doğru
şekilde elendi ve LLM hiç çağrılmadı (`tool=0`).

---

## 8. Tool-calling agent döngüsü

### Kullanılan teknoloji
Ham Python döngü + sağlayıcı SDK'sı. Üç tool: `search_documents`, `lookup_section`,
`list_documents`. Maksimum 3 tur.

### Neden
LangChain/LlamaIndex kullanılmadı: demo ölçeğinde soyutlama katmanı fayda değil borç üretir.
Döngü ~50 satırdır; her davranış açıkça görülebilir, test edilebilir ve — aşağıda görüleceği
gibi — hata ayıklanabilir. Çerçeve içinde prompt sırası veya tool şeması davranışını
değiştirmek çok daha zordu.

### Nasıl çalışır
Sistem promptu **kasıtlı olarak 3 satırdır**. Ölçüm (bkz. §10) uzun bir numaralı kural
listesinin qwen2.5-7b'de tool çağrısını **tamamen bastırdığını** gösterdi. Bu yüzden
atıf/temellendirme talimatı sistem promptundan çıkarıldı ve **tool sonucunun yanına**
(`CITATION_REMINDER`) taşındı: tool zaten çalıştıktan sonra gelen talimat çağrıyı bastıramaz.

Model yine de tool çağırmazsa agent aramayı **kendisi** yapar ve tool izine
`injected: true` diye **dürüstçe** kaydeder — böylece sistem model kaprisinden bağımsızdır
ve izleyici neyin otomatik olduğunu görür.

### Ölçülen kanıt

```
[GEÇTİ] Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?
        kosinüs=0.833 bm25=12.01 kapı=True
        atıf=1 tool=1
        cevap: ... 1.500 TL/ay'dır. Bu bilgi [1] numaralı arac kullanım prosedürü ...
```

Trace: `search_documents({'query': 'direktör seviyesindeki çalışan aylık yakıt limiti',
'top_k': 5}) -> 4916 karakter, otomatik=False` — yani modelin **kendi** çağrısı.

Bu tek çıktı zincirin tamamını kanıtlar: DOCX tablo çıkarımı → chunking → hibrit retrieval
→ tool çağrısı → temellendirilmiş üretim → atıf eşleştirme.

---

## 9. Atıf eşleştirme

### Kullanılan teknoloji
Tool çıktısı `[1]`, `[2]` diye numaralanır; cevaptaki `[n]` işaretleri regex ile bu
numaralara geri eşlenir.

### Neden
"Kaynak göster" talimatı tek başına doğrulanamaz. Numaralı eşleştirme, modelin gösterdiği
her atfın **gerçekten getirilen bir kaynağa** karşılık geldiğini kanıtlanabilir kılar.
Eşleşmeyen numara sessizce atılır — model olmayan bir `[7]` uydurursa atıf listesine girmez.

### Nasıl çalışır
`extract_citations(text, tool_outputs)` önce tool çıktılarındaki `^\[n\] <etiket>`
satırlarından bir numara→etiket sözlüğü kurar, sonra cevaptaki `[n]` işaretlerini bu
sözlükte arar. Hiçbir atıf eşleşmezse cevap `NO_INFO_TEMPLATE` ile değiştirilir:
kaynağı doğrulanamayan cevabı vermektense reddetmek yeğdir.

### Ölçülen kanıt
Notebook: **9 soru-cevap çifti, 7 geçerli sorunun 7'si atıflı**, 2 reddin ikisi de doğru
şekilde atıfsız, **0 hata hücresi**. Atıf etiketleri gerçek dosya/bölüm/sayfa taşıyor:
`Duxet 30 mg GRSK_Onaylı KUB.pdf — Bölüm 4.6 Gebelik ve laktasyon, s.10`.

---

## 10. 🔴 Bulunan kusur 2 — Örnekleme sıcaklığı ayarlanmamıştı

Bu, raporun en önemli bulgusudur ve testin ilk turunda **gerçek bir hata** olarak ortaya
çıktı.

### Belirti
Docker smoke testinde yakıt limiti sorusu elendi:

```
[HATA(atıf,içerik)] Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?
          kosinüs=0.833 bm25=12.01 kapı=True
          atıf=0 tool=1
          cevap: Bu konuda bilgi tabanımda bilgi bulamadım...
```

Retrieval doğruydu, kapı geçmişti, tool çağrılmıştı — ama atıf yoktu. **Aynı soru host'ta
daha önce `1.500 TL/ay` cevabını doğru vermişti.**

### Kök neden arayışı (yanlış hipotezler dahil)

| # | Hipotez | Test | Sonuç |
|---|---|---|---|
| 1 | Atıf hatırlatması yanlış yerde | Hatırlatma önce / sonra / ikisi | ❌ Üçü de atıf üretti |
| 2 | Son turda tool şeması göndermek bozuyor | tools var/yok × 2 soru × 3 koşu | ❌ **12/12** atıf üretti |
| 3 | **Örnekleme belirlenimsizliği** | temp 0.8 vs 0, 5'er koşu | ✅ **Doğrulandı** |

Kritik gözlem: `temperature=0`'da 5 çıktının **beşi de birebir aynıydı**; varsayılan
0.8'de her koşu farklı ifade üretti ve biri bozuk Türkçe içeriyordu
(`"[1] kayieńde belirtilen..."`).

`OllamaClient` hiçbir zaman `options.temperature` göndermiyordu → **Ollama varsayılanı
0.8**. Temellendirilmiş soru-cevapta örnekleme rastgeleliği istenmez; üstelik atıf kapısı
sert bir eşik olduğu için modelin `[n]` işaretini atladığı her üretim **doğru bir cevabı
çöpe atıyordu**. Hata oranı düşük (~%10) olduğu için aralıklı ve teşhisi zordu — ilk 12
örneğim hatayı hiç yakalayamadı.

### Çözüm (iki katman)

1. **`LLM_TEMPERATURE=0` varsayılan.** Aynı istem her seferinde aynı cevabı verir.
2. **`CITATION_REPAIR` onarım turu.** Cevap yine de atıfsız kalırsa agent **bir kez** açık
   talimatla yeniden sorar. Yalnızca gerçekten cevap üretilmişse tetiklenir; tur limiti
   dolduğunda tetiklenmez (mevcut `max_tool_turns` testi bu regresyonu yakaladı).

Otomatik atıf iliştirme **bilinçli olarak yapılmadı** — modelin kullanmadığı bir kaynağı
göstermek atıf uydurmak olurdu.

### Doğrulama

| Ölçüm | Düzeltme öncesi | Düzeltme sonrası |
|---|---|---|
| Docker smoke test | 2 başarısız kontrol | **0 başarısız** |
| Notebook atıflı cevap | 6/7 | **7/7** |
| Notebook'ta "bilgi bulamadım" | Duxet sorusunda vardı | **hiç yok** |
| 3 ardışık koşu | ifadeler değişiyordu | **kelimesi kelimesine aynı** |

Duxet sorusu artık doğru bölümü atfediyor:
`Duxet 30 mg GRSK_Onaylı KUB.pdf — Bölüm 4.6 Gebelik ve laktasyon, s.10`.

---

## 11. LLM sağlayıcı katmanı

### Kullanılan teknoloji
`Protocol` tabanlı arayüz + üç istemci: Ollama (varsayılan), Anthropic, OpenAI.
`LLM_PROVIDER` ortam değişkeniyle seçilir.

### Neden
Case lokal çalışabilirliği tercih ediyor, ama yerel 7B modelin tool-calling'i kırılgan
(bkz. §8, §10). Takılabilir katman, yerel model yetersiz kaldığında tek satır ayarla buluta
geçmeyi mümkün kılar. Bulut SDK'ları `requirements.txt`'e **eklenmedi** — varsayılan kurulum
hafif kalsın diye; testleri `pytest.importorskip` ile koşullu atlanır, yönlendirme mantığı
ise SDK'sız da test edilir.

### Nasıl çalışır
Üç istemci de aynı `chat(messages, tools) -> LLMResponse` sözleşmesini uygular ve
sağlayıcıya özgü tool-calling biçimlerini ortak `ToolCall` yapısına normalize eder.
Ollama istemcisi `options.temperature` ve yapılandırılabilir zaman aşımı gönderir.

### Ölçülen kanıt
```
model: qwen2.5:7b-instruct-q4_K_M
temperature: 0.0
timeout: 600
```

**Zaman aşımı notu:** varsayılan 120 sn yetmiyordu — tool sonucu bağlama girdiğinde CPU'daki
7B model bunu aşıp `ReadTimeout` veriyordu. 600 sn'ye çıkarıldı ve
`LLM_TIMEOUT_SECONDS` ile ayarlanabilir yapıldı.

---

## 12. Arayüzler

### Kullanılan teknoloji
Streamlit (web) ve `argparse`'sız basit bir CLI (`python -m src.rag.cli`).

### Neden
Case görsel arayüzü bonus olarak istiyor. Streamlit, Python'dan çıkmadan kaynak paneli ve
tool izi tablosu göstermeyi sağlar; ayrı bir frontend yığını demo kapsamını aşardı.
CLI ise otomatik testler ve hızlı doğrulama için gereklidir.

### Nasıl çalışır
`build_agent()` ikisi tarafından da paylaşılır: indeksi yükler, retriever'ı **config'teki
eşiklerle** kurar (`min_cosine` ve `min_bm25` — ikincisi geçirilmezse `.env` ayarı sessizce
yok sayılırdı), tool kutusunu ve LLM istemcisini bağlar. Streamlit'te `@st.cache_resource`
indeksi ve embedding modelini bir kez yükler; ilk soru ~20 sn ek gecikme yaşar, sonrakiler
hızlıdır.

### Ölçülen kanıt
```
$ curl -o /dev/null -w "%{http_code}" http://localhost:8501   →  200
$ curl http://localhost:8501/healthz                          →  ok
```
Tarayıcıda elle doğrulandı: konu dışı soru → red metni + `Kaynaklar (0)` + `Araç çağrıları (0)`;
`Vitatin95` → cevap + `Kaynaklar (1)` + trace tablosu (`search_documents`, 1763 karakter,
`injected: false`). Türkçe karakterler doğru render ediliyor.

---

## 13. Test süiti

### Kullanılan teknoloji
pytest + pytest-cov, `integration` işaretiyle ayrılmış iki katman. ruff (format + lint).

### Neden
Entegrasyon testleri **gerçek altı belgeyle** çalışır, uydurma fikstürlerle değil —
assertion'lardaki her sayı ölçülmüştür. LLM çıktısının **metni asla test edilmez** çünkü
deterministik değildir; agent döngüsünün kontrol akışı mock'lanmış LLM ile test edilir.

### Nasıl çalışır
`pytest -m "not integration"` yalnız birim testlerini koşar (saniyeler); `-m integration`
gerçek belgeleri yükler ve indeksi sorgular. Kapsam eşiği %70, `llm.py` ve `app.py` hariç
tutulur (dış servis sarmalayıcıları).

### Ölçülen kanıt (konteyner içinde)
```
$ docker compose exec rag python -m pytest -q -m "not integration"
77 passed, 2 skipped, 26 deselected in 1.80s

$ docker compose exec rag python -m pytest -q -m integration
26 passed, 79 deselected in 87.04s
```
Toplam **103 test**, host'ta ölçülen kapsam **%95,10**. Linux/Python 3.11'de tamamı geçmesi,
Windows/Python 3.10'da geliştirilen kodun platform bağımsız olduğunu kanıtlar.

---

## 14. Dağıtım doğrulama betiği

Bu test sırasında `scripts/smoke_test.py` eklendi: sabit bir soru setini canlı agent'a
sorar ve her soru için skor kapısı, atıf varlığı, tool izi ve (mümkünse) içerik kontrolü
yapar. Amaç, bir dağıtımın gerçekten cevap verdiğini tek komutla kanıtlamaktır.

```bash
docker compose exec rag python scripts/smoke_test.py
```

Son çalıştırma: **Başarısız kontrol sayısı: 0** (5 senaryo), üç ardışık koşuda aynı çıktı.

---

## 15. Bilinen sınırlılıklar (bu testte doğrulananlar)

1. **Atıf *seçimi* her zaman isabetli değil.** Aksef sorusunda cevap doğru ama model
   `Bölüm 4.2` ve `4.6`'yı işaretledi (`4.3` yerine). Retrieval sıralaması doğru; hangi
   kaynağın işaretleneceği modele kalmış.
2. **Retrieval, eşiğe çok yakın skorlarda tam belirlenimci değil.** Chroma'nın HNSW
   yaklaşık araması, skorlar neredeyse eşitken (tipik olarak konu dışı sorularda) ilk sırayı
   değiştirebiliyor: aynı soru iki koşuda `0,781 / 0,00` ve `0,782 / 3,64` verdi. Alan içi
   sorularda skorlar koşular arasında birebir aynı çıktı, kapı kararı hiç değişmedi.
3. **CPU'da yavaş.** Tek soru 40–460 saniye; demo notebook'unun tamamı ~25 dakika. GPU veya
   bulut sağlayıcı bunu saniyelere indirir.
4. **Docker imajı 7,37 GB.** `.dockerignore` ile 1,6 GB kazanıldı ama PyTorch + gömülü
   embedding modeli kaçınılmaz. CPU-only PyTorch tekerleği kullanmak birkaç GB daha
   kazandırabilir — denenmedi.
5. **Model konteyner içinde elle çekilmeli** (`ollama pull`, ~4,7 GB). Compose bunu otomatik
   yapmaz; adlandırılmış volume sayesinde yalnız bir kez gerekir.

---

## 16. Bu testte yapılan değişiklikler

| Değişiklik | Commit |
|---|---|
| `.dockerignore` (imaj 8,98 → 7,37 GB) | `de6c87f` |
| `LLM_TEMPERATURE=0` varsayılan + yapılandırılabilir | `de6c87f` |
| `CITATION_REPAIR` onarım turu | `de6c87f` |
| `scripts/smoke_test.py` dağıtım doğrulama betiği | `de6c87f` |
| 4 yeni test (sıcaklık, onarım turu) | `de6c87f` |
| README: belirlenimlilik bölümü + Docker doğrulama | `de6c87f` |

Kalite kapısı değişiklik sonrası: **107 test geçti, 2 atlandı, kapsam %95,10**, ruff temiz.
