# Karar Kaydı (ADR)

Case açıkça *"kararların gerekçelendirilebilmesi"*ni değerlendirme kriteri olarak koyuyor.
Bu dosya, her teknoloji ve tasarım seçimini **bağlam → seçenekler → karar → gerekçe →
sonuçlar** formatında kayıt altına alır. README'deki "Framework ve model seçim gerekçeleri"
bölümü bu dosyanın özeti olacak.

Durum etiketleri: ✅ Kesin — tüm kararlar onaylandı (2026-08-01).

---

## ADR-001 — Framework: Ham Python + sağlayıcı SDK'sı (LangChain/LlamaIndex **yok**) ✅

**Bağlam.** Korpus ~100 bin karakter, ~350 chunk. Zorunlu gereksinim yalnızca "≥1 tool
entegrasyonu" ve kaynak gösterimi.

**Seçenekler.**
| Seçenek | Artı | Eksi |
|---|---|---|
| LangChain | Hazır retriever/agent zincirleri | 40+ geçişli bağımlılık, sık kırılan API, atıf metadata'sı üzerinde kontrol zayıf, demo'yu "kara kutu" yapar |
| LlamaIndex | Güçlü doküman parsing | Aynı ağırlık sorunu; özel bölüm-farkındalıklı chunking yine elle yazılacak |
| **Ham Python** | Tam kontrol, ~10 bağımlılık, her satır gerekçelendirilebilir | Tool-call döngüsü elle yazılacak (~80 satır) |

**Karar.** Ham Python + LLM sağlayıcısının native tool-calling API'si.

**Gerekçe.** (a) Değerlendirilen şey "sistemin bu belgeler üzerinde nasıl çalıştığı" —
framework'ün soyutlama katmanı bunu gizler. (b) Bölüm/sayfa metadata'sının chunk'a
iliştirilmesi ve atıfta gösterilmesi bu case'in çekirdeği; framework'lerin varsayılan
metadata'sı bunu tam vermiyor, override etmek yazmaktan uzun sürüyor. (c) Docker imajı
küçük kalır, "3 komutla kurulum" şartı daha güvenilir olur.

**Sonuç.** Retriever, chunker ve agent döngüsü kendi kodumuz — test edilebilir ve README'de
ASCII diyagramla birebir eşleşir.

---

## ADR-002 — Embedding modeli: lokal `intfloat/multilingual-e5-base` ✅

**Bağlam.** Korpus tamamen Türkçe. Case "lokal ortamda çalışabilen" sistem istiyor.

**Seçenekler.**
| Model | Boyut | Türkçe | Not |
|---|---|---|---|
| `intfloat/multilingual-e5-base` | ~1,1 GB, 768-d | İyi (100 dil, TR dahil) | `query:` / `passage:` önek şeması gerektirir |
| `BAAI/bge-m3` | ~2,2 GB, 1024-d | Çok iyi | Demo için ağır, ilk indirme yavaş |
| `paraphrase-multilingual-MiniLM-L12-v2` | ~470 MB, 384-d | Orta | En hızlı, Türkçe kalitesi belirgin düşük |
| OpenAI `text-embedding-3-small` | Bulut | Çok iyi | "Lokal çalışabilen" şartını zayıflatır, API anahtarı zorunlu olur |

**Karar.** `intfloat/multilingual-e5-base`, `sentence-transformers` üzerinden.

**Gerekçe.** Kalite/boyut dengesi bu korpus ölçeği için en uygun. İndeksleme tamamen
lokal kalınca sistem internet olmadan da ingest + arama yapabiliyor; sadece cevap üretimi
LLM'e bağlı. e5 ailesinin `query:`/`passage:` önek şeması asimetrik arama için tasarlanmış
ve soru-cevap senaryosunda MiniLM'e göre gözle görülür fark yaratıyor.

**Sonuç.** İlk çalıştırmada ~1,1 GB model indirilir → README'de belirtilecek, Docker imajına
model önceden çekilerek (build aşamasında) gömülecek.

---

## ADR-003 — Vektör deposu: ChromaDB (kalıcı, yerel dosya) ✅

**Bağlam.** ~350 chunk. Tek kullanıcılı demo.

**Seçenekler.** ChromaDB · FAISS · saf NumPy · Qdrant/Weaviate (Docker servisi).

**Karar.** ChromaDB `PersistentClient` (`./storage/chroma`).

**Gerekçe.** 350 vektörde arama hızının hiçbir önemi yok (NumPy dot product bile <1 ms);
belirleyici olan **kalıcılık + metadata filtreleme + kurulum kolaylığı**. Chroma tek `pip
install` ile geliyor, ayrı servis gerektirmiyor (docker-compose'u tek servise indiriyor) ve
`where={"source": ...}` metadata filtresini hazır veriyor — `search_documents` tool'unun
`source_filter` parametresi bunun üzerine kuruluyor. Qdrant/Weaviate bu ölçekte gereksiz
operasyonel yük. FAISS metadata'yı ayrı tutmayı gerektiriyor, kod artıyor.

**Sonuç.** `storage/` dizini `.gitignore`'a girer; `scripts/ingest.py` deterministik olarak
yeniden üretir (3 komutluk kurulumun 2. komutu).

---

## ADR-004 — Hibrit arama: BM25 + dense, RRF ile birleştirme ✅

**Bağlam.** Bu, ekstra özellik değil, [01-veri-kesif-bulgulari.md](01-veri-kesif-bulgulari.md)
§1.4'teki **doğruluk sorununun** çözümü: DOCX'ler ASCII'ye indirgenmiş (`Insan Kaynaklari`),
PDF'ler tam Türkçe (`İnsan Kaynakları`). Ek olarak korpusta çok sayıda **birebir eşleşmesi
gereken jeton** var: `IK-POL-001`, `OPS-PRO-003`, `hrportal.teknopark.com.tr`, `Vitatin95`,
`MM_19`, `Ürün-FP`, `4.2` bölüm numaraları. Dense embedding bu tür tanımlayıcıları güvenilir
biçimde yakalamaz.

**Seçenekler.** Salt dense · Salt BM25 · Hibrit (RRF) · Hibrit + cross-encoder reranker.

**Karar.** BM25 (`rank_bm25`) + dense (Chroma), **Reciprocal Rank Fusion** ile birleştirme.
Cross-encoder reranker **kapsam dışı** (demo için gereksiz gecikme ve 2. model indirmesi).

**Gerekçe.** İki yöntem farklı hata modlarına sahip: BM25 tanımlayıcı/kod eşleşmesinde,
dense parafraz sorularında güçlü. RRF skor normalizasyonu gerektirmez (sıra tabanlı),
yani ayarlanacak ağırlık yok — demo'da kırılganlığı azaltır. Her iki tarafta da
ASCII-katlanmış arama alanı kullanılarak §1.4 sorunu kökten çözülür.

**Sonuç.** `rank_bm25` bağımlılığı (+50 KB, saf Python). BM25 indeksi ingest sırasında
pickle'lanır.

---

## ADR-005 — Bölüm-farkındalıklı (section-aware) chunking ✅

**Bağlam.** Case, atıfta "dosya adı **veya bölüm**" istiyor. Sabit boyutlu (fixed-size)
chunking bölüm bilgisini yok eder.

**Karar.** Format başına ayrı strateji:

| Format | Chunk sınırı | Metadata |
|---|---|---|
| PDF (KÜB) | Numaralı bölüm (1, 4.1, 4.2 …); >1.200 karakter ise paragraf sınırından bölünür | `section_id`, `section_title`, `page_start`, `page_end` |
| DOCX | Heading 2 (yoksa Heading 1) bloğu; tablolar Markdown'a çevrilip ait olduğu başlığın altına eklenir | `section_path` (ör. `4. GÜNLÜK KULLANIM SÜRECİ > 4.1 Havuz Araç Talep Adımları`) |
| XLSX (SSS) | **1 satır = 1 chunk** (bir tam SORU/CEVAP çifti) | `sheet`, `row`, `category` |
| XLSX (taksonomi) | **1 satır = 1 chunk**, `alan: değer` serileştirmesi | `sheet`, `row`, `product` |

**Gerekçe.** §1.5'te ölçüldü: SSS'de bir satır zaten kendi kendine yeten bir cevap;
bölmek bilgiyi bozar. KÜB'de "Pozoloji" sorusu tam olarak Bölüm 4.2'ye karşılık geliyor.
Bu strateji hem retrieval kalitesini hem atıf kalitesini aynı anda yükseltir.

**Sonuç.** Tek bir generic splitter yerine 3 loader yazılacak (~250 satır). `lookup_section`
tool'u da bu metadata sayesinde mümkün oluyor.

---

## ADR-006 — Tool seti: 3 tool ✅

Case minimum 1 tool istiyor. 3 tool seçildi:

| Tool | İmza | Neden |
|---|---|---|
| `search_documents` | `(query: str, top_k: int = 5, source_filter: str \| None)` | **Zorunlu.** Ana retrieval yolu. Case'te örnek olarak birebir bu isim geçiyor. |
| `lookup_section` | `(document: str, section: str)` | Case'te örnek olarak birebir geçiyor; ADR-005 metadata'sı sayesinde neredeyse bedava. "Aksef'in 4.3 kontrendikasyonlarını göster" gibi doğrudan erişimi mümkün kılar. |
| `list_documents` | `()` | Agent'ın "hangi belgelerim var" bilgisine erişmesi, konu dışı/bilmiyorum kararını dayanaklı vermesi için. ~15 satır. |

**Karar.** Bu 3'te durulacak. `calculate`, `web_search` gibi tool'lar **kapsam dışı** —
case'in senaryosuyla ilgisiz.

---

## ADR-007 — LLM sağlayıcısı: takılabilir katman, varsayılan Ollama ✅

**Bağlam.** Case: *"Lokal (Ollama, LM Studio vb.) tercih edilir ancak bulut API (OpenAI,
Anthropic, Groq vb.) de kabul edilir. Tercihini README'de gerekçelendir."*

**Seçenekler.**
| Seçenek | Artı | Eksi |
|---|---|---|
| Ollama (`qwen2.5:7b-instruct`) | Case'in tercihi; tamamen offline; API maliyeti yok | ~5 GB indirme; Türkçe kalitesi orta; tool-calling küçük modellerde kırılgan; değerlendiren kişide Ollama kurulu olmayabilir |
| Bulut API (Anthropic `claude-haiku-4-5` / OpenAI) | Türkçe ve tool-calling çok güvenilir; kurulum anında | API anahtarı gerekli; "lokal çalışabilen" şartını LLM tarafında karşılamıyor |

**Karar.** `llm.py` içinde tek arayüz (`chat(messages, tools) -> ToolCall | str`), `LLM_PROVIDER`
env değişkeni ile `ollama` / `anthropic` / `openai` arasında geçiş. **Varsayılan `ollama`**
(case'in tercihi + `docker-compose` ile tek komutta ayağa kalkar), bulut sağlayıcı anahtar
varsa devreye giren alternatif.

**Gerekçe.** Soyutlama katmanı ~60 satır ve "tercihini gerekçelendir" şartını en güçlü
şekilde karşılıyor: iki seçenek de çalışır durumda gösterilip trade-off README'de
anlatılabiliyor. Tek sağlayıcıya kilitlenmek, değerlendirenin ortamında çalışmama riskini
artırıyor.

**Sonuç.** Varsayılan `ollama` olarak onaylandı (2026-08-01). Bulut sağlayıcılar
`.env` üzerinden tek satırla devreye girer; README'de her iki yolun trade-off'u anlatılacak.

---

## ADR-008 — "Bilmiyorum" ve konu dışı yönetimi: 3 katman ✅

**Bağlam.** İki ayrı bonus madde (B1, B2) aslında tek bir problemin iki yüzü.

**Karar.**
1. **Retrieval kapısı (deterministik).** En iyi RRF skoru eşiğin altındaysa LLM'e hiç
   gidilmez → "Bu konuda bilgi tabanımda bilgi bulamadım." Bu katman en ucuz ve en
   güvenilir olanı; hallucination'ı kaynağında keser.
2. **Grounded prompt.** Sistem promptu: yalnızca verilen bağlamdan cevapla, bağlamda yoksa
   açıkça belirt, her iddiaya atıf ekle, bilgi tabanı dışı konuları kibarca reddet.
3. **Atıf post-check.** Cevap üretildikten sonra en az bir geçerli atıf içeriyor mu
   kontrol edilir; içermiyorsa cevap "bilgi bulunamadı" ile değiştirilir.

**Gerekçe.** Tek başına prompt'a güvenmek bu bonusu güvenilir biçimde karşılamaz —
küçük/lokal modellerde özellikle. Deterministik kapı + post-check, model kalitesinden
bağımsız garanti sağlar. Eşik değeri demo notebook'unda kalibre edilip README'de raporlanacak.

**Sonuç.** Konu dışı sorularda (ör. "bugün hava nasıl?") 1. katman zaten devreye girer;
kibar red metni sabit şablondan gelir → LLM çağrısı bile yapılmaz (hız + maliyet).

---

## ADR-009 — Bölüm 2: Analiz boru hattı `src/analysis/` modülü + ince notebook ✅

**Bağlam.** Case notebook teslimi istiyor. Ama temizleme mantığı ([01-veri-kesif-bulgulari.md](01-veri-kesif-bulgulari.md)
§2.3–2.4) tek başına ~200 satır ve 7 görevin hepsinde tekrar kullanılıyor.

**Karar.** Yükleme + temizleme + metrik türetme `src/analysis/` altında test edilebilir
fonksiyonlara; notebook bunları `import` edip analiz, görsel ve yoruma odaklanır.

**Gerekçe.** MF ölçek düzeltmesi gibi kritik bir dönüşümün notebook hücresine gömülü olması
hem test edilemez hem de 7 görevde kopyalanır. Ayrı modül, düzeltmenin birim testiyle
kanıtlanmasını sağlıyor — "istatistiksel bulgularla destekleyin" şartıyla uyumlu.

**Sonuç.** Notebook okunabilir kalır; değerlendiren kişi hem üst seviye anlatıyı hem
alttaki mantığı ayrı ayrı inceleyebilir.

---

## ADR-010 — Tahmin modelleri: seasonal-naive baseline + global gradient boosting ✅

**Bağlam.** A7: "En az iki yaklaşım (naive baseline ve makine öğrenimi)". 18 seri, en
uzunu 124 ay, en kısası 1 ay (§2.5).

**Karar.**
- **Baseline'lar:** Naive (son ay), Seasonal Naive (12 ay önce), 3-aylık hareketli ortalama.
- **ML:** Tek **global** LightGBM modeli (tüm serilerin havuzu) — lag (1,2,3,12), rolling
  mean/std, ay/çeyrek, pazar/ürün kategorik, MF Oran lag'leri.
- **Kapsam dışı:** SARIMA/Prophet per-series (18 seri × ayrı model, kısa serilerde
  yakınsamıyor, demo süresini gereksiz uzatıyor).

**Gerekçe.** (a) Global model, 1–27 aylık kısa serilerin uzun serilerden öğrenmesini sağlar —
per-series model bunlarda çalışmaz. (b) LightGBM kategorik değişkenleri doğrudan alır,
hiperparametre hassasiyeti düşük. (c) `MF Oran`'ın tahmin gücüne katkısı, aynı model
MF özellikleriyle/onsuz eğitilerek **ablasyon** ile ölçülür — case tam bunu soruyor.
(d) Değerlendirme **walk-forward** (son 12 ay, expanding window) — tek train/test bölmesi
zaman serisinde yanıltıcı olur.

**Sonuç.** MAPE, sıfıra yakın gerçek değerlerde patlıyor → yanına **WAPE** ve **sMAPE**
raporlanacak; MAPE yine de case istediği için tabloda kalacak.
