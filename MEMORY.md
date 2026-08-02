# MEMORY — Kalıcı Proje Bilgisi

> Bu dosya, oturumlar arasında kaybolmaması gereken bilgiyi tutar: alınan kararlar,
> uygulama sırasında keşfedilen tuzaklar, zaman kaybettiren şeyler.
> **Buraya yazılan bilgi tekrar keşfedilmek zorunda kalmamalı.**
>
> Nerede kaldığımız burada değil → [PROGRESSION.md](PROGRESSION.md).
> Çalışma kuralları → [CLAUDE.md](CLAUDE.md).

**Son güncelleme:** 2026-08-01

---

## 0. Doküman Haritası — Hangisi Ne Zaman Okunur

| Dosya | Ne zaman | Boyut |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | Her oturum başı — çalışma kuralları | ~340 satır |
| [PROGRESSION.md](PROGRESSION.md) | Her oturum başı — aktif task ve sıradaki adım | ~180 satır |
| **MEMORY.md** (bu dosya) | Her oturum başı — kararlar ve tuzaklar | ~120 satır |
| [docs/superpowers/plans/rag-agent/00-overview.md](docs/superpowers/plans/rag-agent/00-overview.md) | 🚦 Her task başı — global kısıtlar | 100 satır |
| `docs/superpowers/plans/rag-agent/NN-*.md` | 🚦 **Sadece aktif task'ınki** | 111–303 satır |
| [docs/01-veri-kesif-bulgulari.md](docs/01-veri-kesif-bulgulari.md) | Bir test assertion'ı tutmadığında — ölçülmüş gerçekler burada | ~270 satır |
| [docs/02-karar-kaydi.md](docs/02-karar-kaydi.md) | "Neden bu teknoloji?" sorusu çıkınca (10 ADR) | ~230 satır |
| [docs/bolum1-rag/TRD.md](docs/bolum1-rag/TRD.md) | README'nin ASCII mimari diyagramı için (Task 14) | ~460 satır |
| [docs/bolum1-rag/PRD.md](docs/bolum1-rag/PRD.md) | Kabul kriterleri ve 8 demo sorusu için (Task 14) | ~190 satır |
| [docs/00-case-analizi.md](docs/00-case-analizi.md) | "Case bunu istiyor mu?" sorusunda — izlenebilirlik matrisi | ~100 satır |
| `docs/bolum*/UYGULAMA-PLANI.md` | ⚠️ **Uygulanmaz** — sadece faz gerekçesi merak edilirse | — |

---

## 1. Kesinleşmiş Kararlar

Tam gerekçeler: [docs/02-karar-kaydi.md](docs/02-karar-kaydi.md)

| Konu | Karar | Tarih |
|---|---|---|
| Framework | Ham Python + sağlayıcı SDK'sı. LangChain/LlamaIndex **yok** | 2026-08-01 |
| Embedding | `intfloat/multilingual-e5-base` (lokal, `query:`/`passage:` önekli) | 2026-08-01 |
| Vektör deposu | ChromaDB `PersistentClient`, `storage/chroma` | 2026-08-01 |
| Retrieval | **Hibrit** BM25 + dense, RRF (k=60) birleştirme | 2026-08-01 |
| Chunking | Bölüm-farkındalıklı, format başına ayrı strateji. XLSX satırları bölünmez | 2026-08-01 |
| Tool seti | 3 tool: `search_documents`, `lookup_section`, `list_documents` | 2026-08-01 |
| LLM sağlayıcı | Takılabilir katman, **varsayılan Ollama** (`qwen2.5:7b-instruct`); `LLM_PROVIDER` ile bulut'a geçiş | 2026-08-01 |
| Bilmiyorum/konu dışı | 3 katman: skor kapısı → grounded prompt → atıf post-check | 2026-08-01 |
| Bonus özellikler | **Hepsi** yapılacak (bilmiyorum, konu dışı, Streamlit, çoklu format, Docker) | 2026-08-01 |
| Bölüm 2 yapısı | `src/analysis/` modülü + ince notebook | 2026-08-01 |
| Tahmin modelleri | naive/snaive/ma3 + global LightGBM + MF ablasyonu, walk-forward | 2026-08-01 |
| Git akışı | Doğrudan `main`, faz başına 1 commit + push, Conventional Commits | 2026-08-01 |
| Commit imzası | 🚫 `Co-Authored-By` / `Generated with Claude Code` gibi hiçbir atıf satırı eklenmez | 2026-08-01 |
| Kod dili | Bölüm 1 tamamen İngilizce (yorumlar dahil), Bölüm 2 Türkçe | 2026-08-01 |
| Veri dosyaları | Git'e **commit edilmiyor** (`.gitignore`) — teslim ZIP'ine elle eklenecek | 2026-08-01 |
| Kalite kapısı | ruff format + ruff check + pytest, min %70 coverage | 2026-08-01 |
| Geliştirme disiplini | **TDD zorunlu** (RED→GREEN→REFACTOR, testin başarısız olduğu görülmeden kod yazılmaz) + tamamlandı demeden önce kanıtlı doğrulama | 2026-08-01 |
| Skill'ler | superpowers v6.2.0 (MIT) `.claude/skills/` altına proje-yerel kuruldu; `.claude/` gitignore'da, teslime dahil değil | 2026-08-01 |
| Faz akışı | Her task sonunda dur, onay iste — otomatik bir sonraki task'a geçme | 2026-08-01 |
| **Uygulama planı — tek kaynak** | 🚦 Kod **yalnızca** `docs/superpowers/plans/rag-agent/` altındaki 14 task dosyasından yazılır. `docs/bolum*/UYGULAMA-PLANI.md` dosyaları kavramsal arka plandır, **uygulanmaz**; çakışırlarsa superpowers task'ı kazanır | 2026-08-01 |
| Plan okuma kuralı | `00-overview.md` (100 satır) + **tek** task dosyası (111–303 satır). Tüm task seti asla birlikte okunmaz — 3115 satırlık monolit bu yüzden bölündü | 2026-08-01 |
| Bölüm 2 planı | Superpowers task planı Bölüm 1 bitince yazılacak; şimdi yazmak eşik kalibrasyonu gibi bilinmeyen çıktıları tahmine dayandırırdı | 2026-08-01 |

---

## 2. Veri Tuzakları (ölçülerek tespit edildi)

Tam detay: [docs/01-veri-kesif-bulgulari.md](docs/01-veri-kesif-bulgulari.md)

### Bölüm 1 — RAG korpusu

| # | Tuzak | Sonucu | Çözüm |
|---|---|---|---|
| 1 | **Türkçe karakter tutarsızlığı.** DOCX'ler ASCII'ye indirgenmiş (`Insan Kaynaklari`), PDF'ler tam Türkçe (`İnsan Kaynakları`), hatta aynı cümlede karışık (`yıllık` + `Kaynaklari`) | Doğru yazılmış sorgu DOCX'i bulamaz | `fold_tr()` — Türkçe eşlemeler **`casefold()`'dan önce**; `İ` Python'un `lower()`'ında bozuluyor. Hem indeks hem sorgu tarafında |
| 2 | **DOCX tabloları `document.paragraphs` ile görünmüyor** (7 + 9 tablo). En sorgulanabilir bilgi orada (yakıt limitleri, oryantasyon takvimi) | "Direktörün yakıt limiti?" cevapsız kalır | `document.element.body` üzerinden `CT_P` / `CT_Tbl` sırayla dolaşılır; tablo → Markdown |
| 3 | `paragraph.style` bazı paragraflarda `None` | `AttributeError` (fiilen alındı) | `getattr(p.style, "name", "") or ""` |
| 4 | **XLSX başlık satırı 3. satırda** (üstte başlık + versiyon satırı var) | `read_excel(header=0)` yanlış okur | Otomatik başlık satırı tespiti |
| 5 | **Dosya adında Türkçe karakter:** `ik_surecleri_politikası.docx` (case metni ASCII yazmış) | Sabit yazılmış dosya adı bulunamaz | `glob` ile tarama, dosya adı koda gömülmez |
| 6 | **PDF bölüm tespitinde yanlış pozitif:** Duxet s.15 dipnotları (`7 Plasebodan istatistiksel olarak...`) başlık gibi görünüyor | Uydurma bölüm atfı | KÜB bölüm beyaz listesi (1–6.6) + monoton artış kontrolü |
| 7 | Windows konsolu cp1252 | Türkçe çıktıda `UnicodeEncodeError` (fiilen alındı) | `PYTHONIOENCODING=utf-8` / `sys.stdout.reconfigure` |

### Bölüm 2 — Satış veri seti

| # | Tuzak | Sonucu | Çözüm |
|---|---|---|---|
| 1 | 🚨 **`MF Oran` B Pazarı'nda yüzde ölçeğinde** (medyan ~7,4; Şirket 1 satırlarının %86'sı > 1), diğer pazarlarda oran ölçeğinde | `Net Kutu` negatife düşüyor, birim fiyat **−0,88 TL** çıkıyor (doğrusu 8,32 TL). **A4, A6, A7 tamamen yanlış olur** | Grup medyanı > 1 ⇒ yüzde ölçeği; program tespitiyle 100'e böl. "B Pazarı" sabit yazılmaz |
| 2 | **Ürün adı çakışması:** `Ürün-A`/`Ürün-B` hem Şirket 1 hem Diğer Şirket'te (A Pazarı); `Ürün-FP` hem Şirket 1 hem Şirket 2'de (B Pazarı) | Yanlış birleştirme | Birincil anahtar **daima** `(Pazar, Şirket, Ürün)` |
| 3 | **Ürün adında çift boşluk:** `Ürün 1` vs `Ürün  2` | Aynı ürün iki ayrı seri gibi | `re.sub(r'\s+', ' ', ad).strip()` |
| 4 | **Aşırı kısa seriler:** `C Pazarı/Ürün 1` = **1 gözlem**, `D Pazarı/Ürün 78` = 11 ay, `B/Ürün-FP` = 27 ay | Mevsimsellik/tahmin kodu kırılır veya anlamsız sonuç verir | ≥24 ay şartı; hariç tutulanlar **açıkça raporlanır**, gizlenmez |
| 5 | Negatif `Brüt Kutu` (1.158) / `Net TL` (1.168) — iade kayıtları | Toplamları bozar veya silinirse hacim şişer | `is_return` bayrağı; toplamda korunur, tahmin girdisinde 0'lanır |
| 6 | Ölçek düzeltmesinden sonra bile aşırı MF değerleri (Diğer Şirket max 469,5) | Fiyat ve pay hesabı bozulur | `[0, 0.95]` kırpma + bayrak + raporlama |
| 7 | 139.128 hücrenin 28.006'sı boş (%20) — ürün yaşam döngüsü | 0 ile doldurulursa satış düşüşü gibi görünür | İlk pozitif satıştan önceki dönem kırpılır |

---

## 3. Doğrulanmış Referans Sayılar

Kodun bunlarla eşleşmesi beklenir; eşleşmiyorsa **önce kodu** sorgula.

**Bölüm 1**
- Korpus: 6 dosya, ~95–100 bin karakter, beklenen chunk sayısı 250–450
- Aksef KÜB: 12 sayfa, 24.350 karakter, 27 bölüm başlığı; `4.3 Kontrendikasyonlar` → sayfa 3
- Duxet KÜB: 24 sayfa, 57.226 karakter, 32 başlık (5'i yanlış pozitif)
- `ik_surecleri_politikası.docx`: 84 dolu paragraf, 7 tablo, 8× Heading 1, 16× Heading 2
- `arac_kullanim_proseduru.docx`: 54 dolu paragraf, 9 tablo, 10× Heading 1, 8× Heading 2
- `calisan_sss_rehberi.xlsx`: 3 sayfa (17×6, 14×5, 19×6)
- `Anonim_Urun_Taksonomi_100Satir.xlsx`: 100 satır × 15 kolon → tam **100** chunk
- Tablo kanıt metni: `1.500 TL/ay` (Direktör yakıt limiti)

**Bölüm 2**
- Ham veri: 378 satır × 375 kolon, tek sayfa (`Sheet1`)
- 374 seri × 124 ay (2016-01 → 2026-04), yinelenen anahtar yok
- Şirket 1 ürün sayısı: A=10, B=4, C=2, D=2 (toplam 18 seri)
- Son 12 ay Brüt Kutu payı — Şirket 1: A %12,4 · B %13,1 · C %6,0 · D %3,9
- MF medyanları: A ≈ 0,00 · **B ≈ 5,9–7,4** · C ≈ 0,05–0,12 · D ≈ 0,12–0,17
- Birim fiyat kontrolü: A/Ürün-A 10,28 TL (2016) → 157,20 TL (2026);
  B/Ürün-FR (düzeltme sonrası) 8,32 → 148,15 TL

---

## 4. Uygulama Sırasında Öğrenilenler

> Her faz sonunda buraya ekle: ne beklenmedik çıktı, ne zaman kaybettirdi, bir daha nasıl
> yapılmalı. Boşsa henüz kod yazılmamış demektir.

### Task 1 — İskelet, config, modeller (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **Ortam kurulumu** | `.venv` + `pip install -r requirements.txt` **birkaç dakika sürüyor** — `sentence-transformers` PyTorch'u (~200 MB) çekiyor. Arka planda başlat, beklerken test/kod yazmaya devam et |
| **RED'i doğrulamak için pytest şart değil** | pytest kurulumu beklenirken `python -c "from src.rag.config import Config"` ile `ModuleNotFoundError` doğrudan görülebilir. Kurulum bitince resmî `pytest -v` çıktısı yine alınır |
| **`.gitignore` zaten hazırdı** | Task 1 Step 4 `.venv/`, `storage/`, `data/` eklenmesini istiyor ama üçü de mevcuttu (`.venv` satır 153, `data/` 223, `storage/` 226). `git check-ignore -v` ile doğrulandı, düzenleme yapılmadı |
| **Bağımlılık sayısı** | `requirements.txt` 13 satır; overview "max 12" diyor. Çelişki değil: 3'ü geliştirme aracı (`pytest`, `pytest-cov`, `ruff`), **çalışma zamanı bağımlılığı 10** |
| **Python 3.10.3 doğrulandı** | `str | None` union sözdizimi çalışıyor (3.10'dan itibaren geçerli). `tomllib`/`Self` kullanılamaz |
| **Git satır sonu** | Git `LF → CRLF` uyarısı veriyor (Windows). Zararsız, `.gitattributes` gerekmedi |

### Task 2 — Türkçe normalizasyon (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **`fold_tr` gerçek veride doğrulandı** | Sentetik testlerin ötesinde canlı korpusla kontrol edildi: `fold_tr("İnsan Kaynakları")` → `insan kaynaklari`, ASCII'ye indirgenmiş DOCX metninde **bulunuyor**. Hiçbir belgede U+0307 kalıntısı yok. Tuzak #1 fiilen kapandı |
| **Sıralama kritik** | Türkçe eşleme `casefold()`'dan **önce** çalışmalı. Aksi halde `İ` → `i` + U+0307 olur, kombine işaret NFKD'den sağ çıkar ve eşitlik bozulur. Test bunu açıkça koruyor (`"̇" not in fold_tr("İZİN")`) |
| **`fold_tr` boşluk da sıkıştırır** | Sadece harf eşlemesi değil — `\s+` → tek boşluk + `strip()`. Yani arama metni tek satıra iner. `clean_text` ise **paragraf yapısını korur** (`\n\n`), ikisi farklı amaca hizmet eder |

### Task 3 — PDF loader (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **Yanlış pozitif filtresi ölçüldü** | Ham regex eşleşmesi: Aksef **28**, Duxet **33**. Beyaz liste + monoton sıra sonrası ikisi de **20 bölüm**. Yani Aksef'te 8, Duxet'te 13 satır elendi — Duxet'in dipnot yoğunluğu (s.15) veri keşfindeki tespitle uyumlu |
| **İki filtre birlikte çalışıyor** | Sadece KÜB beyaz listesi yetmez; `_sort_key(...) > last_key` monoton artış şartı, gövde metnindeki tekrar eden `4.2` gibi referansları da eliyor. Biri kaldırılırsa yanlış pozitifler geri gelir |
| **Ölçülmüş gerçekler tuttu** | Aksef 12 sayfa, Duxet 24 sayfa — veri keşfiyle birebir. `4.3 Kontrendikasyonlar` → sayfa 3 doğrulandı, assertion değiştirilmedi |
| **Kapsanmayan satırlar bilinçli** | `_one_section_per_page` fallback'i (satır 78, 87) hiç tetiklenmiyor — her iki PDF de bölüm numarası taşıyor. Coverage %98, eşiğin üstünde. Numarasız bir PDF gelirse devreye girecek |

### Task 4 — DOCX loader (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **Tablo tuzağı fiilen kanıtlandı** | `document.paragraphs` metninde `1.500 TL/ay` **yok**, `load_docx` çıktısında **var**. Yani entegrasyon testi gerçekten `_iter_block_items`'ı koruyor; tablo dalı kaldırılırsa test kırmızıya döner |
| **Ölçülmüş gerçekler birebir tuttu** | `arac_kullanim_proseduru.docx`: 54 dolu paragraf, 9 tablo, 10× H1, 8× H2 → **15 bölüm**. `ik_surecleri_politikası.docx`: 84 dolu paragraf, 7 tablo, 8× H1, 16× H2 → **19 bölüm**. Veri keşfiyle uyumlu, hiçbir assertion değiştirilmedi |
| **Başlık sayısı ≠ bölüm sayısı** | Araçta 10 H1 + 8 H2 = 18 açılan bölüm ama çıktı 15. Fark: metni boş kalan bölümler `if section.text` ile eleniyor (art arda gelen başlıklar, ör. H1'i hemen H2 izliyorsa H1 boş kalır). Bu kasıtlı — boş bölüm indekse girmemeli |
| **`getattr(p.style, "name", "")` savunması gerekli kaldı** | Tuzak #3'ün gerçekleştiği yer burası; `_style_name` olmadan `AttributeError` alınır |
| **Entegrasyon testleri ilk çalıştırmada geçti** | Plan Step 3'te `load_docx` zaten yazılmış olduğu için Step 5 testleri RED aşaması görmedi. Bunu telafi etmek için tablo iddiasının anlamlılığı ayrı bir probe ile kanıtlandı (paragraphs-only metinde `1.500 TL/ay` yok). Task 5'te aynı desen tekrarlarsa aynı probe yaklaşımı uygulanmalı |

### Task 5 — XLSX loader (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **Başlık satırı üç sayfada aynı değil** | Plan "3 sayfanın da başlığı satır 2'de" diyor; ölçüm: `Genel SSS` → **2**, `IT Sistem Rehberi` → **2**, `Onboarding Kontrol Listesi` → **1**. Üçüncü sayfada alt başlık satırı yok, sadece tek başlık satırı var. `detect_header_row` üçünü de doğru buluyor — sabit `header=2` yazılsaydı üçüncü sayfa kayardı. Plandaki genelleme yanlış, kod doğru |
| **`header=0` tuzağı kanıtlandı** | Naif okuma sütun adlarını `['TEKNOPARK YAZILIM A.S. — ...', 'Unnamed: 1', ...]` yapıyor; tespitli okuma `['#', 'Kategori', 'Alt Kategori', 'Soru & Cevap', ...]` veriyor. Tuzak #4 fiilen kapandı |
| **Tespit sezgiseli: doluluk oranı** | `_MIN_FILL_RATIO = 0.6` — başlık satırı tüm sütunları doldurur (6/6), başlık/alt başlık satırları yalnız ilk hücreyi (1/6). İlk 10 satır taranır, en çok dolu olan kazanır |
| **Bölüm sayıları** | Taksonomi: 101 ham satır → başlık 0 → tam **100** bölüm (ölçümle birebir). SSS: 15+12+18 = **45** bölüm |
| **Kapsanmayan satırlar bilinçli** | `xlsx_loader.py` satır 50 (`raw.empty` → boş sayfa atlama) ve 58 (`text` boş → satır atlama) hiç tetiklenmiyor; korpusta boş sayfa/satır yok. %94 kapsam, eşiğin üstünde |
| **Entegrasyon testleri yine ilk çalıştırmada geçti** | Task 4'teki desen tekrarlandı (plan Step 3 uygulamayı zaten yazdırıyor). Yine probe ile anlamlılık kanıtlandı — bu artık loader task'ları için standart adım |

### Task 6 — Loader dispatch (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **Korpusun tam ölçüsü** | `load_all(data/)` → **219 bölüm, 144.365 karakter**, 6 dosya. Dağılım: Taksonomi 100 (41.295 kr) · SSS 45 (11.378) · Aksef 20 (22.748) · Duxet 20 (54.771) · İK 19 (7.081) · Araç 15 (7.092). Tür bazında: xlsx 145 · pdf 40 · docx 34 |
| **§3'teki "~95–100 bin karakter" tahmini düşük kalmış** | Gerçek toplam 144.365. Fark büyük ölçüde XLSX'ten: satır başına `Alan: Değer` serileştirmesi alan adlarını 100 satırda tekrar ediyor (taksonomi tek başına 41 bin karakter). Task 7'de beklenen chunk sayısı (250–450) bu yüzden tekrar kontrol edilmeli |
| **Türkçe dosya adı tuzağı kapandı** | `ik_surecleri_politikası.docx` glob ile bulundu, `source_file` alanına Türkçe `ı` ile geçti. Hiçbir yerde dosya adı sabit yazılmadı |
| **`~$` filtresi savunma amaçlı** | Word açıkken bıraktığı geçici dosyalar (`~$...docx`) `.docx` uzantılı ama okunamaz. Korpusta şu an yok, testi tetiklemiyor ama üretimde tek satırlık maliyeti var |
| **Entegrasyon testleri yavaşladı** | `load_all` 3 testte 3 kez çağrılıyor, tam süite 6,4s→21s. Sorun değil ama Task 8'den sonra fixture'a alınması düşünülebilir |

### Task 7 — Chunker (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| 🚨 **Plandaki `_split_text` hatalıydı — düzeltildi** | Kod yalnızca `\n\n` sınırında bölüyordu. Tek başına `max_chars`'ı aşan bir paragraf geldiğinde `else` dalı `paragraph[:max_chars]`'ı yazıp **kalanın tamamını** `buffer`'a atıyor, kalan bir daha asla bölünmüyordu. Sonuç: 232 chunk (beklenen 250–450'nin altı) ve **12 chunk 1200 sınırının üstünde, en büyüğü 9.681 karakter** |
| **Kök neden ölçümle bulundu** | KÜB bölümleri boş satır içermiyor: 91.692 karakterlik PDF+DOCX metni yalnızca **80 paragrafa** bölünüyor, 13'ü 1200'ün üstünde, en uzunu **10.731** karakter. Yani "paragraf sınırında böl" stratejisi bu korpusta tek başına çalışmıyor |
| **Çözüm: `_hard_split`** | `max_chars`'ı aşan paragraflar önce satır sonu / cümle sonu (`. `) tercih edilerek kesiliyor, uygun sınır pencerenin ilk yarısına düşerse sert kesim yapılıyor. `start += max(cut - overlap, 1)` hem örtüşmeyi hem ilerlemeyi (sonsuz döngü yok) garanti ediyor. Sonuç: **276 chunk, sınır aşımı 0** (PDF 53→97) |
| **Birikim döngüsü de sızdırıyordu** | Eski kod `buffer[-overlap:] + "\n\n" + paragraph` sonucunu boyut kontrolü olmadan buffer'a yazıyordu. Yeni kod sığmazsa örtüşmeyi bırakıp yalnız paragrafı alıyor — böylece **her parça ≤ max_chars** garanti |
| **Mevcut birim testi bu hatayı yakalayamıyordu** | `test_long_section_splits...` 400'er karakterlik 6 paragraf kullanıyor; hepsi sınırın altında olduğu için hatalı dal hiç çalışmıyor. Ders: sınır testinde **tek parçanın sınırı aştığı** durum ayrıca test edilmeli |
| **Chunk sayısı beklentisi doğrulandı** | Düzeltme sonrası 276, planın 250–450 aralığında. Task 6'da not düşülen "144 bin karakter tahminden yüksek" endişesi sorun çıkarmadı |

### Task 8 — İndeks + ingest (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **Ingest gerçek çıktısı** | 219 bölüm → **276 chunk**, **50,5 saniye** (model önbellekteyken, CPU). Dosya başına: Taksonomi 100 · Duxet **63** · SSS 45 · Aksef **34** · İK 19 · Araç 15. PDF'ler bölüm sayısının (20+20) çok üstünde chunk veriyor — Task 7'nin `_hard_split`'i burada görünür oluyor |
| **e5 önek şeması** | Belgeler `passage: `, sorgular `query: ` önekiyle gömülüyor. Task 9'da sorgu tarafında **aynı öneki kullanmak zorunlu** — unutulursa benzerlik skorları sistematik olarak düşer ve `MIN_COSINE=0.72` eşiği her şeyi eler |
| **Model indirme maliyeti** | `intfloat/multilingual-e5-base` ilk çalıştırmada ~1,1 GB indiriyor, `~/.cache/huggingface` altına. Windows'ta symlink uyarısı veriyor (zararsız, disk biraz daha fazla yer kaplar) |
| **Chroma telemetri hatası zararsız** | `Failed to send telemetry event ... capture() takes 1 positional argument but 3 were given` — chromadb/posthog sürüm uyumsuzluğu, indeksleme etkilenmiyor. `ANONYMIZED_TELEMETRY=False` ile susturulabilir |
| **Yeniden kurma idempotent** | `build_index` her çağrıda koleksiyonu silip yeniden yaratıyor; iki kez çalıştırınca chunk sayısı iki katına çıkmıyor (test ile korunuyor) |
| **`chunks.jsonl` = tek gerçek kaynağı** | Chunk metni/atıf etiketi hem Chroma'da hem JSONL'de. Retriever JSONL'i okuyor, Chroma yalnız vektör araması için. `Chunk(**json.loads(line))` round-trip çalışıyor |
| **Pydantic uyarısı** | `chromadb` 50 adet `PydanticDeprecatedSince211` uyarısı üretiyor. Kütüphane içi, bizim kodla ilgisi yok |

### Task 9 — Hibrit retriever ve eşik kalibrasyonu (2026-08-02)

Bu task'ta **üç ayrı kök neden** bulundu ve düzeltildi. Üçü de ölçümle tespit edildi.

#### 1. Bölüm başlıkları aranabilir değildi (chunker düzeltmesi)

KÜB bölüm 4.3'ün **başlığı** "Kontrendikasyonlar" ama bu kelime **gövde metninde hiç geçmiyor**.
`search_text` sadece gövdeydi → ne BM25 ne dense o bölümü ayırt edebiliyordu; "Aksef
kontrendikasyonları" sorgusunda 4.3 üçüncü sıradaydı. Çözüm: `_search_heading()` —
`section_id + section_title + section_path + sheet` **yalnız `search_text`'e** ekleniyor,
görüntülenen `text` değişmiyor. Yan fayda: "Havuz aracı nasıl talep edilir?" artık doğrudan
`4.1 Havuz Araç` bölümünü buluyor (önce genel `3. ARAÇ TAHSİS` geliyordu).

#### 2. BM25 Türkçe eklerde eşleşmiyordu (`bm25_tokens`)

Başlık eklendikten **sonra bile** 4.3'ün BM25 skoru 0,00 kaldı. Sebep: sorgu tokenı
`kontrendikasyonlari`, indeks tokenı `kontrendikasyonlar` — BM25 tam eşleşme yapar,
Türkçe eklemeli dilde bu asla tutmaz. Çözüm: `bm25_tokens()` — tokenlar **ilk 6 karaktere**
kırpılıyor (sabit uzunlukta kırpma kökleştirme, Türkçe bilgi erişiminde standart yöntem,
yeni bağımlılık gerektirmez). Ölçüm — demo sorgu setinde doğru ilk sonuç sayısı:

| Önek uzunluğu | Sonuç |
|---|---|
| kırpma yok | Aksef 4.3 ✗ · Duxet 4.6 ✓ |
| 5 | Aksef 4.3 ✗ · Duxet 4.6 ✓ |
| **6 (seçilen)** | **Aksef 4.3 ✓ · Duxet 4.6 ✓** |
| 7 | Aksef 4.3 ✓ · Duxet 4.6 ✗ |
| 8 | Aksef 4.3 ✓ · Duxet 4.6 ✓ (6'dan zayıf) |

Sonuç: 4.3'ün BM25 skoru 0,00 → **8,31**, sıralamada 3. → **1.**

#### 3. Güven eşiği: tek sinyal ayırt edemiyor (VEYA → VE)

Planın `MIN_COSINE=0.72` değeri e5 için **çok düşük**: e5 kosinüsü dar bir banda sıkıştırıyor,
konu dışı sorular bile 0,75–0,81 alıyor. Ölçülen dağılım (10 geçerli soru, 6 konu dışı):

| | kosinüs (ilk sonuç) | BM25 (ilk sonuç) |
|---|---|---|
| **Geçerli sorular** | 0,811 – 0,874 | 7,51 – 21,55 |
| **Konu dışı sorular** | 0,746 – **0,813** | 0,00 – **8,25** |

🚨 **Bantlar çakışıyor.** Konu dışı "Bana bir şiir yaz" kosinüs **0,813** alıyor — en zayıf
geçerli soru olan "OPS-PRO-003"ün (**0,811**) üstünde. Konu dışı "En sevdiğin film hangisi?"
BM25 **8,25** alıyor — birçok geçerli sorunun üstünde. Yani **VEYA kapısı bu veride matematiksel
olarak imkânsız**: kosinüs eşiği 0,813'ün üstünde olmalı, ama o zaman geçerli sorular için
BM25 eşiği ≤ 7,55 olmalı, o da 8,25'lik konu dışı soruyu içeri alır.

**Karar: iki sinyalin de aynı anda desteklemesi (VE kapısı).**
`MIN_COSINE = 0.80` **ve** `MIN_BM25 = 5.0` → 10 geçerli sorunun **10'u** geçiyor,
6 konu dışı sorunun **6'sı** eleniyor. PRD 8a ("Şirketin 2027 kâr hedefi" — alan içi ama
belgede yok) da doğru şekilde eleniyor (kosinüs 0,778).

| Konu | Öğrenilen |
|---|---|
| **Eşik değerleri değişti** | Overview'daki `MIN_COSINE=0.72` **artık geçerli değil**; `0.80` + yeni `MIN_BM25=5.0`. `config.py` ve `test_config.py` güncellendi. README'ye bu tablo girecek |
| **Eşik değiştikçe yeniden ingest gerekiyor** | `search_text` veya `bm25_tokens` değişirse indeks bayatlar. Task 9'da 3 kez yeniden ingest edildi (~55–62s). Ölçüm yaparken bunu unutma |
| **RRF sıralamayı dense'ten devralmıyor** | 4.3 en yüksek kosinüse sahipken (0,828) bile BM25 desteği olmadan 3. sıraya düşüyordu. RRF **sıra** birleştirir, skor değil — bir ranker tamamen kör kalırsa fusion onu kurtarmaz |

### Task 10 — Tool'lar + promptlar (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **Sorunsuz geçti** | 10 birim testi, plandan sapma yok. Tool çıktısı `[1]`, `[2]` diye numaralı — Task 12'nin atıf post-check'i bu numaraları gerçek kaynaklarla eşleştirecek |
| **`prompts.py` kapsam dışı görünüyor** | Sadece sabit string'ler, hiçbir test import etmiyor → %0. Task 12'de agent import edince kapsanacak. Yapay test yazılmadı |

### Task 11 — LLM sağlayıcıları (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **Ollama model etiketi farklı** | Bu makinede `qwen2.5:7b-instruct` **yok**, `qwen2.5:7b-instruct-q4_K_M` var. Düz etiketle `/api/chat` **404** veriyor. Yerelde `.env` içinde `LLM_MODEL=qwen2.5:7b-instruct-q4_K_M` gerekiyor; `config.py` varsayılanı kanonik etiket olarak bırakıldı (değerlendirici `ollama pull qwen2.5:7b-instruct` ile tam onu alır) |
| **Bulut SDK'ları kurulu değil** | `anthropic` ve `openai` `requirements.txt`'te yok (ADR-007: varsayılan Ollama). Yönlendirme testleri `pytest.importorskip` ile koşullu atlanıyor — bu, "testi geçirmek için skip" değil, planın Step 4'ünün açıkça izin verdiği durum. Yönlendirme mantığı ayrıca SDK'sız da test ediliyor (`ModuleNotFoundError` = doğru constructor'a ulaşıldı, `ValueError` = yönlendirme hatası) |
| **CPU'da 7B yavaş** | Tek tool-calling isteği ~60–75 saniye. 4 senaryoluk probe 300s timeout'u aştı. Task 12/14'te LLM çağıran her adım için bunu hesaba kat — demo notebook'u dakikalar sürecek |
| 🚨 **SYSTEM_PROMPT tool çağrısını engelliyor** | Ölçüldü: sistem promptu **olmadan** model `search_documents`'i çağırıyor; **mevcut SYSTEM_PROMPT ile çağırmıyor**, doğrudan genel bilgiden cevap veriyor. Sebep: Kural 3 ("araçlardan gelen içerikte cevap yoksa 'bilgi bulamadım' de") modele daha 1. turda kullanabileceği bir kaçış yolu veriyor ve qwen2.5-7b onu kullanıyor. Prompt'a "önce aracı çağır" eklemek **düzeltmedi**. **Task 12 bunu çözmek zorunda** — muhtemelen bağlamı agent'ın kendisi önceden çekmeli (skor kapısı zaten LLM'den önce çalışıyor), modelin tool çağırma inisiyatifine güvenilmemeli |

### Task 12 — Agent döngüsü + güvenlik ağı (2026-08-02)

Birim testleri (scripted LLM) ilk denemede geçti ama **uçtan uca çalışmıyordu**. Gerçek
LLM ile denemeden "bitti" denseydi teslim edilen sistem her soruya "bilgi bulamadım"
diyecekti.

#### 🚨 Kök neden 1: Uzun sistem promptu tool çağrısını öldürüyor

Ölçüm (qwen2.5:7b-instruct-q4_K_M, aynı sorular):

| Sistem promptu | Tool çağrıldı mı? |
|---|---|
| Prompt yok | ✅ |
| Planın 5 kurallı numaralı listesi | ❌ |
| Numaralı liste + "İlk adımın DAİMA search_documents" | ❌ |
| **3 satırlık, yalnız tool direktifi** | ✅ (iki soruda da) |
| 3 satır + atıf cümlesi eklenince | ❌ (tekrar bozuldu) |

Sorun tek bir kural değil, **promptun uzunluğu/liste biçimi**. Model son derece hassas:
tool direktifinin dışındaki her ek cümle tool çağrısını bastırıyor.

**Çözüm — talimatı zamanda ayır:**
- `SYSTEM_PROMPT` yalnız 3 satır: "önce search_documents çağır".
- Atıf/temellendirme talimatı (`CITATION_REMINDER`) **tool sonucunun yanında** gönderiliyor.
  Tool zaten çalıştıktan sonra gelen talimat çağrıyı bastıramıyor.
- Prompttan çıkarılan kurallar kaybolmadı: konu dışı reddi **1. katman** (skor kapısı,
  LLM'den önce), "kaynaksız cevap yok" **3. katman** (atıf post-check) tarafından
  deterministik olarak zorlanıyor. Yani promptun *rica ettiği* şeyi güvenlik ağı *dayatıyor*.

#### 🚨 Kök neden 2: Model tool çağırmazsa cevap çöpe gidiyordu

Model tool çağırmadığında `outputs` boş kalıyor → atıf çıkmıyor → 3. katman her cevabı
`NO_INFO_TEMPLATE` ile değiştiriyordu. Prompt düzeltilse bile bu davranış modele bağlı
kalırdı. **Çözüm:** agent, ilk turda hiç tool çağrılmamışsa aramayı **kendisi** yapıyor
(`_add_tool_result(..., injected=True)`) ve trace'e `injected: True` diye **dürüstçe**
kaydediyor. Böylece sistem model kaprisinden bağımsız.

#### Kök neden 3: 120 saniyelik timeout yetmiyor

Tool sonucu bağlama girince 7B model CPU'da 120s'i aşıyor → `ReadTimeout`. Varsayılan
**600s** yapıldı, `LLM_TIMEOUT_SECONDS` ile ayarlanabilir.

#### Uçtan uca doğrulanmış çıktı

`"Yıllık izin talebimi nasıl yaparım?"` → model **kendisi** tool çağırdı (`injected: False`),
2.280 karakter aldı, 3 gerçek kaynağa atıf verdi ve İK belgesindeki gerçek rakamları
(14/20/26 iş günü) döndürdü. `"Bugün hava nasıl olacak?"` → red, boş trace.

| Konu | Öğrenilen |
|---|---|
| **Scripted LLM testleri yeterli değil** | 7 birim testi yeşilken sistem uçtan uca bozuktu. LLM'li her task'ta **gerçek modelle bir kez** çalıştırmadan "bitti" denmemeli |
| **Model sorguyu yanlış yazsa bile retrieval tutuyor** | Model `"yılınık izin"` diye hatalı sorgu üretti, doğru chunk'lar yine geldi — `fold_tr` + BM25 6-karakter kırpmasının yan faydası |
| **Kaynak belgede yazım hatası var** | `ik_surecleri_politikası.docx` başlığı gerçekten `5.1 Yıllık Izin Haklarıq` (sondaki `q` belgede var). Loader hatası **değil**; atıf etiketi belgeyi birebir yansıttığı için düzeltilmedi |

### Task 13 — CLI + Streamlit (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **CLI uçtan uca doğrulandı** | `python -m src.rag.cli "Direktör ... yakıt limiti nedir?"` → **"1.500 TL/ay"** + `arac_kullanim_proseduru.docx — 3. ARAC TAHSIS POLITIKASI`. Bu tek çıktı **DOCX tablo çıkarımı → chunking → retrieval → agent → atıf** zincirinin tamamını kanıtlıyor (demo sorusu 3) |
| **Streamlit tarayıcıda test edildi** | Konu dışı soru → red metni + `Kaynaklar (0)` + `Araç çağrıları (0)`. `Vitatin95` → cevap + `Kaynaklar (1)` + trace tablosu (`search_documents`, 1763 karakter, `injected: false`). Türkçe karakterler doğru render ediliyor |
| **İlk soru yavaş, sonrakiler hızlı** | `@st.cache_resource` sayesinde indeks + embedding modeli bir kez yükleniyor. İlk soruda ~20s ek gecikme var, README'de belirtilmeli |
| **`build_agent` eşikleri config'den alıyor** | Task 9'da eklenen `min_bm25` buraya da geçirildi; aksi halde retriever varsayılanı kullanılır ve `.env` ayarı sessizce yok sayılırdı |

---

## 5. Açık Sorular / Bekleyen Kararlar

_(Şu an yok. Bir karar kullanıcıya sorulacaksa buraya yaz, cevap gelince §1'e taşı.)_
