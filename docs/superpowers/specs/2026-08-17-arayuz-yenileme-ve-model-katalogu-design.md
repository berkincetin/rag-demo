# Arayüz Yenileme, Sohbet Yetenekleri ve Model Katalogu — Tasarım

**Tarih:** 2026-08-17
**Kapsam:** yalnızca `azure/rag/` (backend) ve `azure/web/` (ön yüz) — yani canlıdaki dağıtım.
`src/rag/` ve `web/` bu çalışmanın dışındadır ve değiştirilmeyecektir.

> Bu belge, vaka çalışmasının zorunlu kapsamının **dışına** çıkan bir genişletmedir.
> Kullanıcı bunu açıkça talep etti; CLAUDE.md'nin "demo kapsamını genişletme" kuralı
> bu belgeyle bilinçli olarak esnetiliyor.

---

## 1. Amaç

Canlıdaki uygulamayı beş eksende ilerletmek:

1. Referans projedeki (`C:\Users\Polinity\Desktop\azure-rag`) sohbet arayüzünün düzenini
   benimsemek, kullanıcının verdiği yeni renk paletiyle.
2. Cevabı kelime kelime akıtmak (SSE).
3. Konuşma başına doküman yükleme — vektör aramalı, sunucuda kalıcı olmayan.
4. 10 mesaj hatırlama + 11. mesajda ilk 10'u özetleme mekanizması.
5. Notebook'taki Bölüm 2 analizini statik bir sayfada göstermek.
6. LLM / embedding / reranking seçimi yapılabilen bir ayar menüsü.

---

## 2. Ölçülen gerçekler

Tasarımı kısıtlayan, **varsayım değil ölçüm** olan veriler:

| Ölçüm | Değer | Kaynak |
|---|---|---|
| Korpus parça sayısı | 276 | `wc -l azure/storage/chunks.jsonl` |
| Mevcut Chroma indeksi | 11 MB | `du -sh azure/storage/chroma` |
| Container belleği / geçici disk | 2 GiB / 4 GiB | `az containerapp show` |
| Mevcut kapı eşikleri | `min_cosine=0.25`, `min_bm25=4.22` | `azure/.env` |
| Dağıtılmış modeller | `gpt-4.1-mini`, `text-embedding-3-small` | `az cognitiveservices account deployment list` |
| Notebook hücreleri | 60 hücre, 10 PNG figür | `notebooks/analiz_full.ipynb` |

Üç embedding indeksinin toplam disk maliyeti ≈ 40 MB (1536 + 3072 + 1536 boyut × 276 parça,
artı Chroma/sqlite ek yükü). 2 GiB bellek ve 4 GiB geçici disk için önemsiz.

Yeniden indeksleme maliyeti model başına ≈ 138 bin token → 0,02 USD altı.

### Dağıtılabilir ama henüz dağıtılmamış modeller

`az cognitiveservices account list-models` çıktısına göre hepsi mevcut ve hepsi
`GlobalStandard` (token başına ücret, boşta maliyet yok):

| Rol | Azure'daki ad | Format |
|---|---|---|
| LLM (alternatif) | `gpt-5-mini` | OpenAI |
| LLM (bütçe) | `Phi-4-mini-instruct` | Microsoft |
| LLM (OpenAI dışı) | `cohere-command-a` | Cohere |
| Embedding | `text-embedding-3-large` | OpenAI |
| Embedding | `embed-v-4-0` | Cohere |
| Reranking | `Cohere-rerank-v4.0-fast` | Cohere |

**Bunların dağıtılması ücret doğurur ve kullanıcının açık onayı olmadan yapılmayacaktır.**

---

## 3. Mimari kararlar

### A. Akış (SSE) — grafiğe dokunmadan

**Problem.** Kullanıcıya ulaşan metin tek bir LLM çağrısından çıkmıyor. `graph.py` akışında
`llm_turn` bir aday üretir; ardından `citation_check` bu adayı reddedip `repair`'e (ikinci
LLM çağrısı) veya `no_info`'ya (metni tamamen değiştirir) yönlendirebilir. `score_gate`
hiç LLM çağırmadan `REFUSAL_TEMPLATE` döndürebilir. Dolayısıyla "son çağrının token'larını
akıt" yaklaşımı, kullanıcıya nihai cevabı olmayan bir metin gösterir.

**Karar.** Akış bir *kontrol akışı* değişikliği değil, bir *gözlem katmanı* olacak.

- `AzureOpenAIClient.chat()` içeride `stream=True` ile çalışır, delta'ları biriktirir ve
  bugünkü ile aynı `LLMResponse` nesnesini döndürür. Fark: yolda metin delta'larını bir
  kuyruğa yayınlar.
- Kuyruk, bir `contextvar` üzerinden taşınan isteğe bağlı bir "token alıcısı"dır. Alıcı
  yoksa davranış bugünküyle bit düzeyinde aynıdır.
- Grafik bir çalışan iş parçacığında koşar; SSE üreteci kuyruğu boşaltır.

**Sonuç: `graph.py`, `agent.py` ve mevcut testleri hiç değişmez.** Notlandırılan RAG
çekirdeği riske girmez.

**Olay sözleşmesi** (`POST /api/ask/stream`, `text/event-stream`):

| Olay | Yükü | Anlamı |
|---|---|---|
| `start` | `{}` | Yeni bir aday cevap başlıyor — arayüz balonu temizler |
| `token` | `{"content": "..."}` | Metin parçası |
| `meta` | `{citations, grounded, inputTokens, outputTokens, costUsd, latencyMs, modelId, toolTrace}` | Cevap tamamlandı |
| `replace` | `{"content": "..."}` | Nihai metin akandan farklı (reddetme / `no_info` / `repair`) |
| `error` | `{"detail": "..."}` | Hata |

**Kritik detay:** `stream=True` varsayılan olarak `usage` döndürmez.
`stream_options={"include_usage": True}` gönderilmezse token sayıları ve maliyet
sessizce `None` olur ve metrikler bozulur.

**Proxy.** `azure/web/app/api/proxy/[...path]/route.ts` bugün gövdeyi `response.text()`
ile tamponluyor — bu akışı öldürür. Akış yolları için gövde `ReadableStream` olarak
aktarılacak, `Content-Type` korunacak, tamponlama yapılmayacak.

### B. Konuşma durumu ve özetleme — istemcide

**Karar.** Konuşmalar tarayıcının `localStorage`'ında durur; sunucu konuşma durumu tutmaz.

Gerekçe: kenar çubuğunda N konuşma var ama sunucu oturumu tek. Ayrıca container yeniden
başladığında sunucu belleği uçar, istemcininki kalır.

Her konuşma kaydı: `id`, `title`, `createdAt`, `updatedAt`, `messages[]`, `summary`,
`summarizedUpTo`, `documents[]`.

**Özetleme.** `SUMMARY_BLOCK = 10`. Özetlenmemiş mesaj sayısı 10'a ulaştığında, arka planda
`POST /api/summarize` çağrılır; önceki özet ve yeni 10 mesaj tek bir bütünleşik özette
birleştirilir, `summarizedUpTo` 10 artar. Başarısız olursa sessizce geçilir ve bir sonraki
blokta yeniden denenir — kullanıcı beklemez.

**Soru gönderimi.** İstemci her soruda `summary` + özetlenmemiş `history` gönderir. Backend
bunlardan geçici bir `ConversationMemory` kurar; `retrieval_query` sohbeti genişletmek için
bu belleği kullanmaya devam eder. Özet, geçmişten önce ayrı bir sistem mesajı olarak
enjekte edilir.

### C. Yükleme — vektörlü, TTL'li, disksiz

**Karar.** Yüklenen belgeler sunucuda **yalnızca bellekte** ve **süreli** tutulur.

Akış:

1. `POST /api/documents/upload` (multipart) → sunucu dosyayı istek içinde ayrıştırır,
   parçalara böler, konuşmanın seçili embedding modeliyle vektörler.
2. Sonuç, `(oturum, konuşma)` anahtarlı bellekteki TTL deposuna yazılır. **Diske hiçbir şey
   yazılmaz**; dosyanın kendisi ayrıştırmadan sonra atılır.
3. Her erişimde süpürücü çalışır: **60 dakika işlem görmemiş** girdiler silinir.
4. Sert sınırlar: konuşma başına en fazla **5 belge** ve **300 parça**; dosya başına
   **10 MB**. Aşıldığında 413 döner.
5. Çıkışta (`POST /api/auth/logout`) ve konuşma silindiğinde istemci
   `DELETE /api/documents` çağırır; TTL ise terk edilmiş oturumları yakalar.

Kabul edilen tipler: `.pdf`, `.txt`, `.docx`, `.xlsx` — projenin yükleyicileri zaten bunları
destekliyor.

**Arama.** Yüklenen parçalar korpusla aynı hibrit yöntemden geçer: seçili embedder ile yoğun
arama + o parçalar üzerinde anlık kurulan BM25, RRF ile birleştirilir. Korpus isabetleriyle
birleştirilirken alıntı etiketleri kaynağı ayırır (yüklenen dosya adı görünür).

**Skor kapısı.** Yüklenen parçalar kapıya da girer. Aksi hâlde yalnızca yüklenen dosyadan
cevaplanabilecek bir soru, LLM'e hiç ulaşmadan reddedilir. Grafiği değiştirmemek için, aktif
yükleme deposunu `contextvar`'dan okuyan bir retriever sarmalayıcısı kullanılır — token
alıcısıyla aynı mekanizma, tek bir "istek bağlamı" modülünde toplanır.

**Embedding modeli değişirse** yüklenen parçaların vektörleri geçersizleşir (farklı vektör
uzayı). O konuşmanın parçaları bir sonraki kullanımda yeni modelle yeniden vektörlenir;
metinler zaten bellekte olduğu için yeniden yükleme gerekmez.

### D. Üç embedding indeksi

**Problem.** Farklı embedding modelleri farklı vektör uzayları üretir. `text-embedding-3-small`
ile kurulmuş Chroma koleksiyonunu Cohere vektörüyle sorgulamak bozuk değil, **sessizce
yanlış** sonuç verir.

**Karar.** Üç ayrı Chroma koleksiyonu, tek bir parça kümesi üzerinde:

| Model | Anahtar | Boyut | Dizin |
|---|---|---|---|
| `text-embedding-3-small` (varsayılan) | `3-small` | 1536 | `azure/storage/chroma-3-small/` |
| `text-embedding-3-large` | `3-large` | 3072 | `azure/storage/chroma-3-large/` |
| `embed-v-4-0` (Cohere) | `cohere-v4` | 1536 | `azure/storage/chroma-cohere-v4/` |

`chunks.jsonl` ve `bm25.pkl` **paylaşılır**: BM25 embedding'den bağımsızdır (aynı parçalar,
aynı tokenizasyon). Yalnızca yoğun taraf modele göre değişir.

`scripts/ingest.py` ve `scripts/calibrate.py` bir `--embedding-model` argümanı alır.

**Kalibrasyon.** `min_cosine` her model için ayrı ölçülür — kosinüs dağılımları farklıdır ve
mevcut 0.25 değeri yalnızca `3-small` için geçerlidir. `min_bm25` (4.22) üç modelde de aynı
kalır, çünkü BM25 tarafı değişmiyor. Eşikler `azure/config/embedding_models.json` içinde
model anahtarına göre tutulur.

**Çalışma zamanı.** Üç `LoadedIndex`/`Retriever` üçlüsü açılışta kurulur ve istek başına
seçilen model anahtarına göre seçilir. Toplam ek bellek ~40 MB.

### E. Çoklu LLM sağlayıcısı

`LLMClient` protokolü (`chat(messages, tools) -> LLMResponse`) korunur; iki uygulama olur:

- **`AzureOpenAIClient`** — OpenAI formatındaki dağıtımlar (`gpt-4.1-mini`, `gpt-5-mini`),
  mevcut Azure OpenAI ucundan.
- **`AzureInferenceClient`** — Microsoft ve Cohere formatındaki dağıtımlar
  (`Phi-4-mini-instruct`, `cohere-command-a`), Azure AI Model Inference ucundan,
  `azure-ai-inference` paketiyle.

  Uç adresleri `az cognitiveservices account show --query properties.endpoints` ile
  doğrulandı: "Azure AI Model Inference API" ve "Cohere AI API" aynı tabanı paylaşıyor
  (`https://foundry-lab-hbc26.services.ai.azure.com/`), Azure OpenAI ise ayrı bir tabanda
  (`https://foundry-lab-hbc26.openai.azure.com/`). Yani iki istemci iki farklı uca gider;
  tek bir taban adresi varsaymak hatalı olur.

**GPT-5 ailesi farkları** (sessizce patlayan türden):
- `temperature=0` desteklenmez → yalnızca varsayılan sıcaklıkla çağrılır.
- `max_tokens` yerine `max_completion_tokens` beklenir.

Bu farklar model tanımında bayrak olarak taşınır, istemcide `if model_id ==` zinciriyle değil.

**Phi-4-mini riski.** Ajanın tamamı araç çağırma üzerine kurulu; Phi-4-mini'nin araç çağırma
güvenilirliği düşük olabilir. Mimari bunu zaten kaldırıyor: model araç çağırmazsa
`inject_context` düğümü devreye girip aramayı onun adına yapıyor (aynı geri dönüş
`qwen2.5-7b` için yazılmıştı). Yine de "Budget" seçeneğinin kalitesi ölçülmeden
garanti edilemez — değerlendirme sonucu ne çıkarsa dürüstçe raporlanacak.

`catalog.py` dört modeli sağlayıcı ailesi ve yetenek bayraklarıyla listeler.

### F. Reranking

`Cohere-rerank-v4.0-fast` ile, **kapıdan sonra** çalışır:

```
hibrit arama (yoğun + BM25, RRF)
        ↓
   skor kapısı        ← füzyon skorlarını okur, kalibrasyon burada geçerli
        ↓
    reranking         ← yalnızca sıralamayı ve top_k seçimini değiştirir
        ↓
   LLM'e bağlam
```

Sıra kritik: rerank kapıdan önce çalışırsa `hits[0]`'ın kosinüs/BM25 değerleri değişir ve
ölçülmüş eşikler geçersizleşir.

Rerank kapalıyken davranış bugünküyle aynıdır. Rerank çağrısı başarısız olursa füzyon
sıralaması korunur ve cevap üretilmeye devam edilir — sessizce degrade olur, hata vermez.

### G. Ayarlar menüsü

Tarayıcı genelinde bir tercih (`localStorage`), her istekle gönderilir:

```
LLM
├── GPT-4.1-mini        (varsayılan)
├── GPT-5-mini          (alternatif)
├── Phi-4-mini-instruct (bütçe)
└── Cohere Command A    (OpenAI dışı)

Embedding
├── text-embedding-3-small (varsayılan)
├── text-embedding-3-large
└── Cohere Embed v4

Reranking
└── Cohere Rerank v4 Fast  (açık/kapalı)
```

Sunucu, gelen seçimi kataloğa karşı doğrular; tanınmayan bir değer 400 döner (istemciden
gelen model adı doğrudan dağıtım adı olarak kullanılmaz).

Menü, o an dağıtılmamış modelleri devre dışı ve sebebiyle birlikte gösterir — sessizce
başarısız olan bir seçim bırakılmaz.

### H. Arayüz ve palet

Referans projedeki düzen benimsenir: solda konuşma listesi (arama, gruplama, yeniden
adlandırma, silme, daraltma), ortada mesaj akışı (markdown, kopyala, düzenle, yeniden üret,
kaynak açılır paneli), altta besteci (doküman çipleri, sürükle-bırak, otomatik büyüyen
metin alanı).

Renk simgeleri tek bir token setinde toplanır; bileşenler yalnızca değişkenlere bakar, böylece
iki tema yapı gereği senkron kalır:

| Simge | Açık | Koyu |
|---|---|---|
| Arka plan | `#F8FAFC` | `#0F172A` |
| Kart / yüzey | `#FFFFFF` | `#1E293B` |
| Ana renk | `#005AA9` | `#3B82F6` |
| Vurgu | `#38A169` | `#22C55E` |

### I. Analiz sayfası

`scripts/export_analysis.py`, `notebooks/analiz_full.ipynb` dosyasını okuyup üretir:

- markdown hücreleri → anlatı bölümleri
- `execute_result` HTML tabloları → başlık + satır JSON'u
- `display_data` PNG çıktıları → `azure/web/public/analiz/*.png`
- `stream` çıktıları → önbiçimli metin blokları
- kod hücreleri → bölüm başına katlanabilir blok (değerlendiren doğrulayabilsin)

Çıktı: `azure/web/lib/analysis.json` + PNG dosyaları. `/analiz` rotası bunları uygulamanın
kendi bileşenleriyle render eder. **Excel görüntüleyici yoktur** — kullanıcı kapsam dışı
bıraktı.

Matplotlib figürleri beyaz zeminlidir; her iki temada da beyaz bir "figür kartı" içinde
gösterilir, aksi hâlde koyu temada göz alır.

`middleware.ts` matcher'ı `_next/static` dışındaki her şeyi kapsadığı için `public/analiz/`
altındaki figürler de giriş arkasındadır — doğrulandı, ek önlem gerekmiyor.

---

## 4. Hata durumları

| Durum | Davranış |
|---|---|
| Akış ortasında bağlantı kopar | Arayüz "Bağlantı kesildi" gösterir; kısmi metin korunur |
| `repair` metni değiştirir | `replace` olayı; balon içeriği güncellenir |
| Yükleme sınırı aşılır | 413 + Türkçe açıklama; mevcut belgeler etkilenmez |
| Desteklenmeyen dosya tipi | 400 + kabul edilen tiplerin listesi |
| TTL süresi dolmuş belge | `GET /api/documents` boş döner; arayüz çipleri eşitler |
| Rerank çağrısı başarısız | Füzyon sıralaması kullanılır, cevap üretilir, hata gösterilmez |
| Embedding modeli değişti | Yüklenen parçalar bir sonraki kullanımda yeniden vektörlenir |
| Dağıtılmamış model seçilir | 400; menüde zaten devre dışı |
| `localStorage` kotası dolar | Uyarı gösterilir, en eski konuşma silinmez — kullanıcı seçer |

---

## 5. Test stratejisi

TDD zorunlu (CLAUDE.md §3). LLM çıktısının metni asla test edilmez; LLM sınırına kadar her
şey test edilir.

**Backend (pytest):**
- Akış istemcisi: sahte delta parçaları → doğru token dizisi + `usage` doğru toplanır
- Olay üreteci: reddetme / `repair` / `no_info` yollarında `replace` yayılır
- Yükleme deposu: TTL süpürme, sert sınırlar, oturum izolasyonu (bir oturum diğerinin
  belgesini göremez)
- Birleşik arama: yüklenen parça korpus isabetleriyle doğru sırada birleşir
- Kapı: yalnızca yüklenen belgede olan soru kapıdan geçer
- Özetleme ucu: boş mesaj listesi 400, geçerli liste özet döndürür
- Katalog doğrulaması: tanınmayan model 400
- Rerank: başarısızlıkta füzyon sırası korunur
- İndeks seçimi: model anahtarı doğru koleksiyona gider

**Ön yüz (vitest):**
- Özetleme eşiği: 10. mesajda tetiklenir, 9'da tetiklenmez
- `buildContext`: özet + özetlenmemiş mesajlar doğru ayrılır
- Konuşma deposu: kaydet/yükle/sil turu
- SSE ayrıştırıcı: parçalı `data:` satırları doğru birleştirilir
- Mevcut kimlik doğrulama/proxy testleri (12 test) bozulmadan geçmeli

**Entegrasyon:** gerçek korpus üzerinde üç indeksin de kurulduğu ve dört sorgunun beklenen
belgeleri getirdiği doğrulanır.

Kapsam eşiği %70 korunur.

---

## 6. Aşamalandırma

Tek tasarım, üç teslim edilebilir aşama. Her aşama kendi başına canlıya çıkabilir.

**Aşama 1 — Arayüz ve sohbet yetenekleri**
Yeni palet ve düzen, SSE akışı, yükleme (vektörlü + TTL), 10 mesaj özetleme.
Backend tek modelle kalır. Bu aşama bittiğinde canlıdaki uygulama tamamen yenilenmiş olur.

**Aşama 2 — Analiz sayfası**
Dışa aktarım script'i + `/analiz` rotası. Diğer aşamalardan tamamen bağımsız.

**Aşama 3 — Model katalogu ve reranking**
Üç embedding indeksi + kalibrasyon, çoklu sağlayıcı istemcisi, ayarlar menüsü, rerank katmanı.
En riskli ve tek ücret doğuran aşama; yeni model dağıtımları için ayrıca onay alınacak.

---

## 7. Kapsam dışı

- Excel görüntüleyici (kullanıcı kaldırdı)
- `src/rag/` ve `web/` — yerel dağıtım bu çalışmadan etkilenmez
- Yüklenen belgelerin kalıcı saklanması (bilinçli olarak TTL'li ve disksiz)
- Çok replikalı ölçekleme: yükleme deposu ve hız sınırı replika başınadır
- Konuşmaların sunucuda saklanması / cihazlar arası eşitleme

---

## 8. Riskler

| Risk | Etki | Karşılık |
|---|---|---|
| Phi-4-mini araçları çağırmaz | "Budget" seçeneği zayıf cevap verir | `inject_context` geri dönüşü mevcut; sonuç ölçülüp raporlanacak |
| Yeni embedding modellerinin kalibrasyonu ayırt edici eşik vermez | Kapı yanlış çalışır | `calibrate.py` çıktısı incelenir; ayrışma yoksa o model menüde devre dışı bırakılır |
| GPT-5 parametre farkları gözden kaçar | Çalışma zamanı hatası | Model tanımında bayrak + her model için sözleşme testi |
| SSE proxy tamponlaması | Akış görünmez | Proxy'de akış yolu ayrı test edilir |
| Çoklu replika | Yükleme deposu tutarsızlaşır | Tek replika varsayımı belgelenir; arayüz her konuşma değişiminde listeyi eşitler |
| `localStorage` sınırı | Uzun konuşmalar kaybolur | Kota hatası yakalanır ve kullanıcıya gösterilir |
