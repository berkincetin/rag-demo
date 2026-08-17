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

### Task 14 — Demo notebook, Docker, README (2026-08-02)

| Konu | Öğrenilen |
|---|---|
| **Notebook göreli yol tuzağı** | `nbconvert` notebook'u **kendi klasöründe** çalıştırıyor; `STORAGE_DIR=./storage` → `notebooks/storage` oluyor ve `InvalidCollectionException: Collection documents does not exist` alınıyor. Çözüm: setup hücresinde `os.chdir(ROOT)`. `ROOT` hem kökten hem `notebooks/` içinden çalışacak şekilde tespit ediliyor |
| **`jupyter` bağımlılık olarak eklendi** | Plan Step 2 `jupyter nbconvert` çalıştırmayı şart koşuyor ve notebook case teslim kalemi. `requirements.txt`'e **geliştirme/demo aracı** bölümüne eklendi (çalışma zamanı bağımlılığı 10 olarak kaldı) |
| **Notebook 9 senaryo, 0 hata** | 12 hücrenin hepsi hatasız çalıştı. 9 soru-cevap çifti, **6'sı atıflı**. Format kapsamı tam: PDF + DOCX + XLSX + DOCX tablosu (`1.500 TL/ay`) |
| ⚠️ **Ölçülmüş yanlış negatif: Duxet sorusu** | Retrieval doğruydu (0,849 / 7,51, tool 6.255 karakter döndürdü) ama model `[n]` işareti koymadı → atıf post-check cevabı "bilgi bulamadım" yaptı. **Kod hatası değil**, yerel 7B modelin zayıflığı; güvenlik ağı uydurmak yerine reddetmeyi seçti. README sınırlılık #8'e ölçümüyle yazıldı. Otomatik atıf iliştirmek **yapılmadı** — model kullanmadığı kaynağı göstermek atıf uydurmak olurdu |
| **Atıf seçimi de kusurlu olabiliyor** | Aksef sorusunda cevap doğru ama model `Bölüm 1` ve `4.2`'yi işaretledi (`4.3` yerine). Retrieval sıralaması doğru, işaretleme modele bağlı |
| **CPU'da demo çok yavaş** | Tek soru 60–460 saniye (Duxet 461 sn). Tüm notebook ~25 dakika. Değerlendirici için README'de uyarı var |
| **Docker doğrulandı** | `docker compose build` başarılı (`rag-demo-rag`), `docker compose up -d` → `localhost:8501` **HTTP 200**, ollama konteyneri "Ollama is running". Model konteyner içinde ayrıca çekilmeli (`docker compose exec ollama ollama pull ...`) — README'de yazılı |
| **Üç komut sıfırdan doğrulandı** | `storage/` silinip `pip install` + `ingest.py` tekrar çalıştırıldı: 219 bölüm → 276 chunk, 120 sn. Ara adım gerekmedi |

### Docker uçtan uca test + atıf hatasının kökü (2026-08-02)

#### 🚨 Kök neden: örnekleme sıcaklığı ayarlanmamıştı

Task 14'te "yerel modelin zayıflığı" diye not edilen atıf kaybı aslında **bizim
hatamızdı**. `OllamaClient` hiç `options.temperature` göndermiyordu → Ollama varsayılanı
**0.8**. Sonuç aralıklı ve teşhisi zor: aynı soru, aynı indeks, bazen atıflı doğru cevap,
bazen "bilgi bulamadım".

**Teşhis yolu (yanlış hipotezler dahil, tekrar denenmesin):**

| Hipotez | Test | Sonuç |
|---|---|---|
| Prompt zayıf, hatırlatma yanlış yerde | Hatırlatma önce/sonra/ikisi (3 varyant) | ❌ Üçü de atıf üretti |
| Son turda `TOOL_SCHEMAS` göndermek bozuyor | tools var/yok × 2 soru × 3 koşu | ❌ 12/12 atıf üretti |
| **Örnekleme belirlenimsizliği** | temp 0.8 vs 0, 5'er koşu | ✅ temp=0'da **5 çıktı da birebir aynı**; 0.8'de her seferinde farklı, biri bozuk Türkçe (`"kayieńde"`) |

Küçük örneklem tuzağı: 0.8'de 12/12 atıf gördüm ama gerçek hata oranı ~%10 olduğu için
başarısızlığı yakalayamadım. **İki gerçek başarısızlık** (notebook Duxet, Docker yakıt
limiti) aynı girdinin başka koşularda başarılı olmasıyla birlikte kanıt oluşturdu.

**Düzeltme iki katmanlı:**
1. `LLM_TEMPERATURE=0` varsayılan → tekrarlanabilir çıktı. Docker smoke test **3 ardışık
   koşuda kelimesi kelimesine aynı** sonucu verdi.
2. `CITATION_REPAIR` — cevap atıfsız kalırsa **bir kez** açık talimatla yeniden sorulur.
   Yalnızca `final_text` doluysa tetiklenir; tur limiti dolduğunda tetiklenmez (mevcut
   `max_tool_turns` testi bu regresyonu yakaladı).

#### Retrieval de tam belirlenimci değil (küçük)

Aynı konu dışı soru iki koşuda `0,781 / 0,00` ve `0,782 / 3,64` verdi — Chroma HNSW
yaklaşık araması, skorlar neredeyse eşitken ilk sırayı değiştiriyor. **Alan içi
sorularda skorlar birebir aynı**, kapı kararı hiç değişmedi. Eşiğe çok yakın bir soru
teorik olarak koşudan koşuya farklı karar alabilir.

#### Docker bulguları

| Konu | Ölçüm |
|---|---|
| **`.dockerignore` yoktu** | 1,52 GB'lık Windows `.venv` imaja kopyalanıyordu. Eklendikten sonra imaj **8,98 → 7,37 GB**, `/app` 3,2 MB → **1,4 MB** |
| Case arşivi de imajdaydı | `AI Engineer/` (korpusun 2. kopyası + Bölüm 2 veri seti) çıkarıldı |
| Konteynerde Python | **3.11.15** (yerelde 3.10.3). Kod 3.10 uyumlu yazıldığı için sorun çıkmadı — `str \| None` her ikisinde de geçerli |
| Konteynerde ingest | 219 bölüm → **276 chunk**, Windows'la **birebir aynı** |
| Konteynerde testler | **103 test geçti** (77 birim + 26 entegrasyon) — platform bağımsızlığı kanıtlandı |
| Embedding modeli | İmajda önceden gömülü, `~/.cache/huggingface` = **2,27 GB** |
| Servisler arası ağ | `rag` → `http://ollama:11434` çalışıyor |
| `scripts/smoke_test.py` | Yeni: dağıtım doğrulama betiği, 5 senaryo, kapı+atıf+tool kontrolü |

---

### Sağlayıcı Merkezi — Task 1–13 (2026-08-02)

Plan: [docs/superpowers/plans/saglayici-merkezi/](docs/superpowers/plans/saglayici-merkezi/).
Dört commit: `feat(providers)`, `feat(agent)` (LangGraph), `feat(ui)`, `feat(setup)`.

| Konu | Öğrenilen |
|---|---|
| **LangGraph yalnız şemadaki anahtarları taşır** | `_response` state şemasında olmadığı için düğümler arasında **kayboldu** → `KeyError`. `TypedDict`'e `pending_tool_calls: list[Any]` eklendi. Kural: iki düğüm arasında taşınan her şey şemada tanımlı olmalı |
| **Göç kanıtı: `tests/test_agent.py` değişmedi** | Kabul kriteri sözleşmeydi. `git diff --stat` boş, SHA256 aynı (`6D6EBE8A…FEE19`), 8/8 yeşil, gerçek modelde smoke test 0 hata |
| **Streamlit `text_input` yalnız blur'da yazar** | Anahtar girip **Kaydet**'e tıklandığında boş değer kaydediliyordu (tıklama blur'dan önce rerun tetikliyor). `st.form` + `st.form_submit_button` ile atomik gönderim |
| **Varsayılan model `bge-m3` seçiliyordu** | `ollama list` embedding modellerini de döndürüyor; alfabetik ilk isim sohbet edemiyor. `active_model(..., preferred=Config.load().llm_model)` eklendi |
| **Fiyatı bilinmeyen model `$0` değil** | `config/model_prices.json`'da yalnız Anthropic fiyatları dolu (2026-06-24 tablosu). OpenAI/Gemini `null` → `estimate_cost` `None` → arayüz **"fiyat girilmedi"**. SQL tarafında `COUNT(cost_usd)` ile `priced_runs` raporlanıyor; NULL ortalamayı düşürmüyor |
| **Anahtarlar diske yazılmıyor** | `SessionCredentialStore` yalnız bellekte; `__repr__` sadece sağlayıcı adlarını basar. Kaynak kodu testi `open(`, `Path(`, `json.dump`, `write_text` geçmesini engelliyor (ADR-012) |
| **Boyut birimi `ollama list` ile aynı olmalı** | GiB/MiB ile ondalık GB/MB karıştırılınca iki test çelişti. **Ondalık** standart alındı (`12,6 MB`) |
| **Etiket eşleştirme kuantizasyonu yok saymalı** | `qwen2.5:7b-instruct` ile `…-q4_K_M` aynı ağırlık. `_QUANT_SUFFIX = re.compile(r"-q\d+[_\w]*$")` |
| **Ollama kurulumu otomatikleştirilmedi** | `scripts/setup.py` Ollama'yı **kurmaz**, platforma göre komutu yazar. Sessizce sistem kurulumu yapmak kullanıcı kararı olmalı. Docker tarafında `ollama-init` servisi modeli `service_completed_successfully` ile çeker |
| 🚨 **`ollama` servisi host portunu yayımlıyordu** | `ports: ["11434:11434"]` — ama kurulum betiği kullanıcıya **yerel Ollama kurmasını** söylüyor ve o zaten 11434'ü tutuyor. Yani `docker compose up`, betiğin hazırladığı makinelerde **hiç başlamıyordu**. `expose` ile değiştirildi; `rag` zaten servis adıyla erişiyor. Doğrulama: yerel Ollama çalışırken `docker compose up -d` sorunsuz ayağa kalktı |
| **Otomatik model çekme doğrulandı** | Sıfırdan `up`: `ollama-init` 4,7 GB'ı kendi çekti, `ollama list` modeli gösterdi, `rag` beklendi, `localhost:8501` → **HTTP 200**. Elle `ollama pull` **gerekmedi** |

### Task 14–17 — Kaynak ölçümü, bellek, kimlik (2026-08-03)

| Konu | Öğrenilen |
|---|---|
| 🚨 **`None` ile `0` farklı bilgidir** | GPU'da `size_vram == 0` = "ölçüldü, CPU'da çalışıyor"; `None` = "ölçülemedi". Arayüz ikisini ayrı gösteriyor. Aynı kural RAM/CPU ve fiyat için de geçerli |
| **Kaynak ölçümü testleri 3,35 sn → 30 sn yaptı** | Her `answer()` çağrısı 5 sn timeout'lu bir Ollama `/api/ps` isteği yapıyordu. Üç katmanlı düzeltme: `metrics is None` iken `NullMonitor`, bulut modelinde `read_gpu=False`, timeout 2 sn |
| 🎯 **Bellek, skor kapısını bozabilirdi** | *"peki ya müdür seviyesinde?"* tek başına hiçbir belgeye benzemiyor — kapı reddediyor (entegrasyon testiyle ölçüldü). Çözüm: **yalnız retrieval sorgusu** önceki soruyla genişletiliyor (`retrieval_query`), LLM'e giden mesajlarda kullanıcının **kendi yazdığı metin** duruyor |
| **Reddedilen cevap belleğe girmiyor** | Girseydi bir sonraki sorunun retrieval sorgusunu konu dışı metinle kirletirdi |
| **İsim satırı sistem promptunu bozmadı** | Task 12'de ölçülen risk (prompta eklenen her cümle tool çağrısını bastırabiliyor) yeniden ölçüldü. `smoke_test.py` isimsiz → **0 hata**; `smoke_test.py "Berkin"` → **0 hata**, üç alan içi soruda da `tool=1` ve atıf yerinde. Betiğe bu ölçümü tekrarlanabilir kılmak için isteğe bağlı isim argümanı eklendi. İsim boşken prompt **birebir** eski hali (test) |
| 🎯 **İsim yalnız sistem promptunda etkisizdi** | Beklenen risk (tool çağrısının bastırılması) gerçekleşmedi, ama başka bir şey oldu: model ismi **hiç kullanmadı** (iki temellendirilmiş cevap, ikisinde de yok). Task 12'nin çözümü aynen işe yaradı — isim `CITATION_REMINDER` ile birlikte **tool sonucu mesajına** da eklenince ölçüm: *"Merhaba Berkin, …"* (atıf=2, tool=1), *"Berkin, direktör seviyesinde … 1.500 TL/ay"* (atıf=1, tool=1). **Kural: 7B modelde davranış talimatı sistem promptuna değil, tool sonucuna iliştirilir** |
| **İsim ölçüm veritabanına yazılmıyor** | Kişisel veri. `path.read_bytes()` içinde adın geçmediğini doğrulayan test var |
| **`turn_index` ölçüme eklendi** | Gecikme ve token sayısı geçmiş uzadıkça artıyor; tur numarası olmadan yavaş bir 3. tur "yavaş model" gibi görünür |
| **`st.text_input` her rerun'da yeniden cevaplatıyordu** | Widget değerini koruduğu için kenar çubuğundaki her tıklama aynı soruyu tekrar cevaplatıyor ve belleğe **ikinci bir tur** ekliyordu. Belleksiz sürümde yalnız boşa giden bir çağrıydı, görünmüyordu. `st.chat_input` metni yalnız gönderimden sonraki koşuda bir kez döndürüyor |
| **Ekran dökümü ≠ model belleği** | Reddedilen cevap belleğe girmiyor ama ekranda kalmalı → `ui_state.get_transcript` ayrı liste tutuyor |
| 🚨 **Enjekte edilen arama da genişletilmeli** | `inject_context` (model tool çağırmayınca bizim onun yerine yaptığımız arama) **çıplak** soruyla arıyordu; kapı ise genişletilmiş sorguyla. Takip sorusunda yanlış belgelerden cevap üretirdi. Test kırmızıyı gösterdi: `assert 'yakıt limiti' in 'peki ya müdür?'`. İki arama yolu da artık `retrieval_query`'den geçiyor |
| **Bellek uçtan uca doğrulandı** | Arayüzde: *"Direktör … yakıt limiti nedir?"* → `1.500 TL/ay`; ardından *"peki ya müdür seviyesinde?"* → `1.000 TL/ay`. İkisi de kaynak tablodaki değerlerle birebir, `gate_passed=1`, `turn_index=1` |
| ⏱ **CPU'da sohbet çok yavaş** | Tarayıcı da çalışırken tek soru **422 sn**, geçmişli takip sorusu **306 sn**. `size_vram=0` — model GPU'ya hiç yüklenmiyor. Değerlendirici için README'deki yavaşlık uyarısı hâlâ geçerli, bellek onu uzatıyor (bağlam büyüyor) |
| 🚨 **16 GB'ta iki Ollama aynı anda çalışmaz** | Konteyner içi smoke test doğrulaması sırasında host Ollama (WSL) ve konteyner Ollama **aynı 4,7 GB modeli** yükledi; boş RAM 1 GB'ın altına indi, **Docker daemon çöktü** (`docker ps` dahil her çağrı `500 Internal Server Error`) ve host tarafındaki ölçüm 600 sn timeout'a düştü. Uygulama hatası değil, ortam sınırı. Task 13'ün "konteyner smoke test 0 hata" satırı bu yüzden **doğrulanmadı** olarak bırakıldı; tekrar denemek için önce host Ollama durdurulmalı |
| 🚨 **HNSW `search_ef` varsayılanı (10) sessizce cevap kaybettiriyordu** | Aralıklı test hatası kovalanınca çıktı ve **test sorunu değil, ürün hatası**: `test_document_code_is_matched_exactly` 12 tam koşunun 1'inde düşüyordu. Ölçüm — aynı indeks, **bayt bayt aynı** sorgu vektörü (`sha1=cc59028…`), BM25 her seferinde doğru: buna rağmen doğru parça **8 koşunun 2'sinde dense ilk 20'ye hiç girmedi**. Girdiğinde sırası 0 (gerçek en yakın komşu). Girmeyince en iyi kosinüs 0,7916'ya düşüyor → **0,80 kapısının altı** → ajan geçerli soruyu **reddediyor**. Sebep: HNSW yaklaşık arama, `search_ef=10` retriever'ın istediği `n_results=20`'den dar. Düzeltme: koleksiyon `hnsw:search_ef=200` ile yaratılıyor (276 parçada arama fiilen tam taramaya dönüyor). Doğrulama: kopya indekste 8/8, yeniden kurulan gerçek indekste **10/10, `gate=True`** |
| ⚠️ **`collection.modify()` metadata'yı değiştirmez, değiştirir yerine geçer** | Kopya üstünde denerken `modify({'hnsw:search_ef': 200})` çağrısı `hnsw:space: cosine` anahtarını **sildi**; `space`'i birlikte yollamak da `ValueError: Changing the distance function … is not supported`. Bu yüzden ayar yükleme anında değil, **yaratma anında** veriliyor — yani ayar değişince `python scripts/ingest.py` ile indeks yeniden kurulmalı |
| ⚠️ **Açıklanamayan tek test hatası (ayrı olay)** | Smoke test arka planda koşarken `--cov`'lu tam koşuda `test_chunks_jsonl_round_trips_text_and_citation` bir kez düştü. Hata metni yakalanamadı; **0/2 tekrar üretilebildi**. Yukarıdaki `search_ef` hatasıyla **aynı şey değil** — o test tmp_path'e yazıp okuyor, retrieval'a dokunmuyor. Tekrarlarsa `-rA --tb=long` ile bakılmalı |

---

### Bölüm 2 — Satış Analizi (2026-08-04)

| Konu | Öğrenilen |
|---|---|
| 🚨 **MF ölçek düzeltmesi ölçümle doğrulandı** | Bulgular §2.3'teki tahmin tuttu: `mf_olcek_tespit` gerçek veride yalnız `{'B Pazarı': 100.0}` döndü. Düzeltme sonrası B/Ürün-FR 2016-01 birim fiyatı **8,32 TL** (düzeltmesiz −0,88 TL). Kural pazar adına değil grup medyanına bakıyor; uydurma bir "Z Pazarı" yüzde ölçekliyse onu da yakalıyor, adı B olan oran ölçekli bir pazarı yakalamıyor — test bunu koruyor |
| 🚨 **"Kısa seri" satır sayısıyla ölçülemez** | İki ayrı yerde aynı hataya düştüm. `C Pazarı/Ürün 1` kırpma sonrası **27 satır** taşıyor ama yalnız **bir** ayında satış var. (1) `_kisa_seriler` satır sayarken seriyi kısa görmedi. (2) `mevsimsel_indeks` aynı sebeple STL'e girdi ve tek sıçramayı **mevsimsellik gücü 0,987, zirve indeksi 8,72** diye raporladı. Doğru ölçü: **satış görülen ay sayısı**. Uydurulmuş mevsimsellik, "hesaplanamadı" demekten kötüdür |
| 🚨 **Case'in "Diğer Şirket hacim kaybediyor" varsayımı doğrulanmadı** | Regresyonla sınandı: C'de **+6.066 kutu/ay** (p ≈ 1,6×10⁻¹⁵), D'de **+17.863 kutu/ay** (p ≈ 0,003) — anlamlı biçimde **artıyor**. A'da eğim negatif ama anlamsız (p = 0,46). Kayıp yalnız **pay** düzeyinde gerçek (A'da −12,2 puan). Varsayımı doğrulamak yerine sınamak, cevabı tersine çevirdi |
| **A4'ün işareti beklenenin tersi çıktı** | Yüksek MF ayını izleyen ay A Pazarı'nda medyan **−%21,7** (kontrol +%1,0), Mann-Whitney p ≈ 3×10⁻¹², FDR q ≈ 9×10⁻¹², Cliff δ = −0,49. Yani MF talep yaratmıyor, **öne çekiyor** (kanal doldurma). C Pazarı'nda hiç yüksek MF olayı yok → "etki yok" değil, **"test edilemedi"** yazıldı |
| **MAPE gerçekten patlıyor** | D Pazarı'nda `snaive` için MAPE **4.257.901**. Sıfıra yakın gerçek değerler yüzünden. WAPE aynı satırda 195,0. Case MAPE istiyor, tabloda duruyor; model seçimi WAPE'den yapılıyor (V10 kararı ölçümle haklı çıktı) |
| **Tek model mimarisi her pazarda geçerli değil** | Dört pazarda **üç farklı kazanan**: A `snaive` (16,9), B ve C `ma3` (10,8 / 9,9), D `lgbm` (52,9). `lgbm` hiçbirinde birinci değil ama hiçbirinde kötü de değil — tek model seçilecekse en savunulabilir olanı |
| **MF ablasyonu negatif de sonuç verdi** | MF özellikleri A, B, D'de WAPE'yi 1,2–9,8 puan **iyileştiriyor**; C'de **4,5 puan kötüleştiriyor**. C'de A4'e göre hiç MF olayı yok, yani sütun bilgi değil gürültü taşıyor. Negatif sonucu gizlememek, MF'in *ne zaman* işe yaradığını gösterdi |
| ⚠️ **Notebook `notebooks/` içinden koşuyor** | İki göreli yol bu yüzden kırıldı: `VERI_YOLU` (FileNotFoundError) ve `FIGUR_DIZINI` (figürler `notebooks/figures/` altına yazıldı). İkisi de `Path(__file__).resolve().parents[2]` ile mutlak yapıldı, ikisi de `monkeypatch.chdir` testiyle korunuyor |
| ⚠️ **Yinelenen indeks etiketi tahmine seri sızdırıyordu** | `lgbm_walk_forward` hedef satırları indeks etiketiyle seçiyordu; çağıran taraf `pd.concat` ile yinelenen etiket bırakınca **hedef olmaması gereken 3 aylık seri tahmin setine girdi**. `ozellik_matrisi` artık indeksi sıfırlıyor. Test kurgu veriyle bunu yakaladı |
| **Pay değişimi toplamı sıfır çıkmıyordu** | C ve D'de üç şirketin pay değişimi toplamı −6,07 ve −4,04 çıkıyordu. Sebep: Şirket 1 o pazarlarda 2016'da **yok** ve payı `NaN`. "Pazarda yok" = "payı %0" olduğu için eksikler 0 ile dolduruldu; toplam dört pazarda da tam 0 oldu. Tutarlılık kontrolü ancak bu tanımla anlamlı |
| **`ruff` notebook'ları da denetliyor** | `.ipynb` hücreleri E501/F401/E402 veriyor. `sys.path` bootstrap'ı ayrı hücreye alındı, kullanılmayan importlar (sonraki task'lar için erken eklenenler) temizlendi |

---

### Streamlit → Gradio geçişi (2026-08-06)

Kullanıcı isteğiyle arayüz **tamamen** Gradio'ya taşındı: `app.py` + `pages/*.py` (4 sayfa)
silindi, yerine tek dosya `gradio_app.py` (5 sekme) geldi. Port `8501` → **`7860`**.

| Bulgu | Ayrıntı |
|---|---|
| **`ui_state.py` hiç değişmeden taşındı** | Modül baştan `MutableMapping` alıyordu ve hiçbir arayüz kütüphanesi import etmiyordu. Streamlit'e bağımlı olsaydı bu geçiş kat kat pahalı olurdu — sınırın doğru yerde çizilmesinin somut getirisi |
| 🚨 **`gradio==5.9.1` çalışmıyor: `gr.Chatbot(type="messages")` ile başlangıçta 500** | `gradio_client/utils.py` içindeki `_json_schema_to_python_type`, `additionalProperties`'e özyineliyor; JSON Schema bunun **bool** olmasına izin veriyor (`false`) ve ardından `get_type` `"const" in <bool>` yapıp `TypeError: argument of type 'bool' is not iterable` atıyor. `show_api=False` bu yolu **engellemiyor**. Bileşen bileşen izole edildi: yalnızca `Chatbot(type="messages")` patlıyor. Çözüm: **`gradio==5.50.0`** (client 1.14.0) — yukarı akışta düzelmiş. Sürüm seçerken bu tuzağa dikkat |
| **`gr.Progress()` varsayılan argümanda B008 veriyor** | Gradio'nun belgelenmiş kullanımı bu, ama ruff `B008` ile şikâyet ediyor. Modül düzeyinde `_PROGRESS = gr.Progress()` singleton'ı yapıldı; Gradio yine her istekte kendi izleyicisini enjekte ediyor |
| **Gradio 6.0 uyarıları** | `theme`, `css`, `show_api` parametreleri `Blocks()`/`launch()` içinde 6.0'da kalkacak. Şu an yalnızca `DeprecationWarning`; 6.0'a geçilirse `launch()`'a taşınmalı |
| **README "üç komut" tutarsızlığı giderildi** | Başlık üç diyordu, dört komut listeliyordu. `setup.py` isteğe bağlı dördüncü adım olarak ayrıldı; case "3 komutla baslamali" diyor |
| 🚨 **Sohbet için `gr.ChatInterface` kullanılmalı — elle `Chatbot`+`Textbox`+`Button` kurma** | İlk iki tasarım denemesi kullanıcı tarafından reddedildi ("neyin nerede olduğu anlaşılmıyor"). Kök sebep: sohbet bloğu elle kuruluyordu, dolayısıyla girdi/gönder/örnekler/otomatik kaydırma/geçmiş yeniden icat ediliyor, çevredeki paneller de yer kalan yere konuyordu. `gr.ChatInterface` bunların hepsini hazır veriyor; kaynak/araç/metrik panelleri **`additional_outputs`** ile aynı çağrıdan güncelleniyor, ad alanı **`additional_inputs`** ile onun kendi akordiyonuna giriyor. Panelleri sohbetin **altına** koymak için bileşenleri `render=False` ile tanımlayıp sonra `.render()` çağır |
| **`ChatInterface` iki API tuzağı** | (1) `additional_inputs` varsa `examples` **liste-listesi** olmalı: `[[soru, None, None], …]` — düz string listesi `ValueError` veriyor. (2) `fn` imzası `(mesaj, geçmiş, *additional_inputs)` ve **yalnız** cevap metni + `additional_outputs` döndürmeli; `history`'yi kendisi yönetiyor, elle yeniden kurulursa mesajlar ikilenir |

---

### Next.js arayüzü + FastAPI katmanı (2026-08-06)

Kullanıcı Gradio tasarımını üç denemede de beğenmedi ve **Gradio'ya dokunmadan** ayrı bir
Next.js arayüzü istedi. Sonuç: iki arayüz yan yana duruyor, ikisi de tam işlevli.

| Bulgu | Ayrıntı |
|---|---|
| **`serialize.py` ayrıldı, `api.py` ince kaldı** | Wire contract (`answer_payload`, `run_payload`, …) sunucu başlatmadan test edilebiliyor — 9 test TDD ile yazıldı, önce kırmızı görüldü. `api.py` yalnız yönlendirme, kapsam dışı |
| **`ui_state.py` yine değişmedi** | FastAPI de `MutableMapping` oturum sözlüğü veriyor. Aynı yardımcılar hem Gradio hem HTTP API'yi besliyor — sınırın doğru yerde olmasının ikinci getirisi |
| 🚨 **`web/AGENTS.md` var: "This is NOT the Next.js you know"** | Next.js 16 kendi dokümanlarını `node_modules/next/dist/docs/` altına koyuyor ve kod yazmadan **önce** okunmasını istiyor. Ben kodu önce yazdım, sonra doğruladım. Kırıcı değişiklikler (async request API'leri, `middleware`→`proxy`, `next/image`) bu istemci-taraflı uygulamayı etkilemedi ama sıradaki Next.js işinde önce o dokümanlar okunmalı |
| **React 19 `set-state-in-effect` kuralı** | `useEffect` içinde `setState` artık lint hatası. İki gerçek düzeltme yapıldı: türetilebilir state (`picked ?? activeId`) senkronlanmayacak, tema `useState` lazy initializer'ı ile okunacak. Kalan üç yer gerçek "mount'ta sunucudan veri çek" — `disable` yorumu **`useEffect`'in üstüne değil, içindeki çağrının üstüne** konmalı, yoksa kural yine patlıyor |
| **Türkçe curl gövdesi Git Bash'te bozuluyor** | `curl -d '{"question":"Direktör…"}'` → `400 "error parsing the body"`. API hatası değil, kabuk UTF-8'i bozuyor. Gerçek testi Python `urllib` ile yapmak gerekti |

### Docker: 6 servis + "üç komut" kuralı (2026-08-07)

Next.js arayüzü Docker'a eklendi ve case'in "3 komutla baslamali" şartı **her üç yolda da**
sağlandı.

| Bulgu | Ayrıntı |
|---|---|
| **`api` ve `rag` aynı imajı paylaşıyor** | İkisi de 7,4 GB'lık Python imajını kullanıyor, yalnızca `command` farklı (`uvicorn …` / `python gradio_app.py`). Ayrı imaj derlemek boyutu iki katına çıkarırdı |
| **`ingest` ayrı bir servis oldu** | Eskiden `CMD` içinde `[ -f chunks.jsonl ] \|\| ingest.py` vardı. Üç servis aynı anda kalkınca üçü birden ingest çalıştırıp aynı `storage/` dizinine yazardı. Artık `ingest` bir kez çalışıp çıkıyor; `api` ve `rag` `service_completed_successfully` ile bekliyor |
| 🚨 **`web/.dockerignore` şart** | Yoksa `node_modules` + `.next` derleme bağlamına giriyor: **287 MB** aktarım ölçüldü ve Dockerfile zaten hepsini atıyor. Eklendikten sonra bağlam birkaç yüz KB'a düştü. Kök `.dockerignore`'a da `web/node_modules/` eklendi (Python imajına sızmasın) |
| **`NEXT_PUBLIC_API_URL` derleme zamanında gömülüyor** | Tarayıcıda çalışan kod API'yi **host'tan** çağırır, konteyner adı (`http://api:8000`) tarayıcıda çözümlenmez. Bu yüzden compose'da `build.args` olarak `http://localhost:8000` veriliyor, `environment` olarak değil |
| **CORS artık ortam değişkeni** | `CORS_ORIGINS` (varsayılan `localhost:3000,127.0.0.1:3000`). Sabit kodlanmış olsaydı farklı bir host/port ile sunulduğunda kırılırdı |
| **`scripts/run_web.py` "üç komut" için yazıldı** | Next.js yolu Docker'sız 5 komut olurdu (`pip`, `ingest`, `npm install`, `uvicorn`, `npm dev`). Betik son üçünü tek komuta indiriyor, gerekirse `npm install` çalıştırıyor, Ctrl+C ikisini birden durduruyor. TDD ile yazıldı (6 test) |
| **`output: "standalone"`** | `next.config.ts`'e eklendi; Next.js 16 dokümanlarından doğrulandı. Runner imajı tam `node_modules` yerine yalnız çalışma zamanı dosyalarını taşıyor |

---

### Teslim paketi yeniden üretildi (2026-08-07)

README üç katmanı (Next.js + FastAPI + Gradio) anlatacak şekilde genişletildi ve
`rag-demo.zip` sıfırdan kuruldu: **88 → 188 dosya**, 0,7 MB → 3,5 MB.

| Bulgu | Ayrıntı |
|---|---|
| 🚨 **`git archive` bu projede ZIP üretemez** | Eski paket böyle üretilmişti ve bayatlamasının sebebi buydu: `web/`, `gradio_app.py`, `api.py`, `serialize.py` ve 3 test dosyası hâlâ **untracked**. `git archive` onları sessizce atlar. Üstelik `data/` ve `AI Engineer/` bilerek gitignore'da ama teslimde **bulunmak zorunda**. Paket artık çalışma ağacından, açık dışlama listesiyle kuruluyor |
| **Dışlananlar** | `node_modules` (`run_web.py`/Docker yeniden kurar), `.next`, `storage/`, `figures/`, `__pycache__`, `.venv`, `.git`, `.claude`, `.env` (yalnız `.env.example` gidiyor), `CLAUDE.md` + `web/CLAUDE.md` + `web/AGENTS.md` (ajan araçları, teslim değil) |
| **Doğrulama yöntemi** | ZIP temiz bir dizine açılıp testler **oradan** çalıştırıldı: 289 birim + 31 entegrasyon geçti. Entegrasyon testlerinin geçmesi `data/`nın gerçekten pakette olduğunu kanıtlıyor — dosya listesine bakmak bunu kanıtlamaz |
| **`api.py` kapsam dışına alındı** | README "kapsam dışı" diyordu ama `pyproject.toml`'da yoktu; %0 görünüp toplamı %87'ye çekiyordu. Eklendikten sonra **%95**. Gerekçe `gradio_app.py` ile aynı: içinde test edilecek karar yok |
| 🚨 **`env_file: .env` teslimde `docker compose up`'ı kırıyordu** | `.env` sır dosyası olduğu için pakete girmiyor, ama compose onu **zorunlu** sayıyordu: açılan ZIP'te `docker compose config` bile `env file not found` ile patlıyordu — yani README'nin "tek komut" vaadi teslim paketinde çalışmıyordu. Çözüm `env_file: [{path: .env, required: false}]`. Bu ancak paketi açıp **içinden** çalıştırınca görüldü; repo kökünde `.env` durduğu için hep yeşil görünüyordu |

---

### Bölüm 2 teslim paketi: tek dosyalık notebook (2026-08-07)

Kullanıcı Bölüm 2 için ayrı bir teslim istedi: `src/analysis/` fonksiyonları notebook'un
**içine** alınmış, `pip install` hücresiyle başlayan tek dosya (`analiz_full.ipynb`) +
onun ürettiği görseller. Mevcut kodlara dokunulmadı.

| Bulgu | Ayrıntı |
|---|---|
| **Notebook elle değil betikle üretildi** | `analiz.ipynb`'nin 48 analiz hücresi **birebir** kopyalandı; yalnız iki bootstrap hücresi (`sys.path` + `src.analysis` import'ları) pip/veri-yolu/fonksiyon hücreleriyle değiştirildi. Elle kopyalamak analizi kaynaktan ayrıştırırdı |
| 🚨 **Kopyalanan kod aynı sonucu veriyor mu — varsayılmadı, ölçüldü** | Notebook'un tanım hücreleri ayrı bir isim alanında çalıştırılıp modüllerle **yan yana** koşturuldu: `load_raw`, `clean` (+7 rapor alanı), `derived_metrics`, `market_share`, `hhi`, `yoy_growth`, `promo_revenue_loss`, STL fonksiyonları ve üç temel model + **LightGBM'in iki varyantı** `assert_frame_equal` ile karşılaştırıldı. Hepsi birebir |
| **`nbformat` kaynak satırları** | `text.split("
")` satır sonlarını düşürüyor ve bütün hücre tek satıra yapışıp `SyntaxError` veriyor. Doğrusu `splitlines(keepends=True)` — son satır hariç her satır `
` taşır |
| **Kopyalanan hücrelerin `id`'si çakışır** | nbformat 4.5+ benzersiz `id` istiyor; kaynaktan alınan hücreler kendi id'lerini taşıdığı için konuma göre yeniden atandı. Ayrıca `execution_count`/`outputs` temizlendi ki paket "çalıştırılmamış" halde başlasın |
| **Doğrulama izole dizinde yapıldı** | Notebook `src/` erişilemeyen bir klasöre kopyalanıp `nbconvert --execute` ile koşturuldu — "bağımsız çalışıyor" iddiası ancak böyle kanıtlanır. 0 hata, 10 grafik. Sonra ZIP açılıp **oradan** tekrar koşturuldu: promosyon 108,3 milyon TL, %2,93, A4 1783/89/1694 ve A7 kazananları (snaive/ma3/ma3/lgbm) `analiz.ipynb` ile aynı |
| **Teslim edilen notebook çalıştırılmış olan** | ZIP'e çıktıları ve grafikleri gömülü sürüm konuldu; değerlendirici çalıştırmadan da sonuçları görüyor. `figures/` ayrıca PNG olarak da var |

---

### Aşama 1 — Arayüz yenileme, akış, yükleme (2026-08-17)

| Konu | Öğrenilen |
|---|---|
| 🚨 **`contextvar`'lar iş parçacığına miras geçmez** | Akış, grafiği bir `threading.Thread` içinde koşturuyor. Token alıcısı çağıranın bağlamında kurulursa çalışan iş parçacığı onu **göremez** ve akış sessizce boş kalır. Alıcı thread'in *içinde* kuruluyor (`streaming.py: worker()`) — `copy_context()` ile uğraşmaktan hem daha basit hem daha güvenli |
| 🚨 **`stream=True` varsayılan olarak `usage` döndürmez** | `stream_options={"include_usage": True}` gönderilmezse token sayıları ve maliyetin tamamı sessizce `null` olur; hata da vermez. Ayrı bir test bu bayrağın gerçekten gönderildiğini sabitliyor. Canlıda doğrulandı: 1539/69 token |
| **Akan metin *aday*dır, nihai değil** | `citation_check` akış bittikten sonra metni değiştirebiliyor (`repair`), tamamen atabiliyor (`no_info`), ya da `score_gate` LLM'i hiç çağırmadan reddedebiliyor. Bu yüzden `replace` olayı var. Uçtan uca görüldü: "Bitcoin" sorusunda hiç token akmadı, reddetme metni `replace` ile geldi |
| **Araç çağrısı argümanları parça parça gelir** | Akışta `{"query": "yem` + `ek"}` şeklinde ayrı delta'larda geliyor; `index` alanına göre biriktirilmeden JSON olarak ayrıştırılamaz. Paralel çağrılar da `index` ile ayrışıyor |
| **Grafiğe hiç dokunulmadı** | Akış bir *kontrol akışı* değişikliği değil, LLM istemcisine takılan bir *gözlem katmanı* olarak eklendi. `graph.py` ve `agent.py` diff'te yok; notlandırılan RAG çekirdeği ve testleri aynen duruyor |
| 🚨 **Yüklenen parçaların BM25'i korpusunkiyle karşılaştırılamaz** | Farklı IDF tabanı (bir avuç parça vs 276 parçalık korpus). Kapı bu yüzden yüklenen isabetleri **yalnızca kosinüsle** değerlendiriyor; korpus isabetleri ölçülmüş iki sinyalli kuralı koruyor. Aksi hâlde ölçülmemiş sayılar ölçülmüş eşiklerle kıyaslanırdı |
| **Kapı entegrasyonu olmasa yükleme işe yaramazdı** | Katman 1, LLM'den *önce* skorla reddediyor. Yüklenen belge kapıya girmezse "sadece o dosyada olan" soru modele hiç ulaşmadan reddedilir. Uçtan uca kanıtlandı: belge varken cevap geldi, belge silinince aynı soru reddedildi |
| 🚨 **`azure/web/lib/` hiç commit edilmemişti** | Kök `.gitignore`'daki `lib/` (Python artefaktı için) `azure/web/lib/`'i de yakalıyordu; `auth.ts`, `api.ts`, `format.ts` git'te yoktu. Taze bir klon **derlenmezdi** — canlı çalışıyordu çünkü Docker imajı yerel dosyalardan derleniyor. Kural `/lib/` olarak köke sabitlendi. `web/lib/` de aynı kurbandı (kapsam dışı, dokunulmadı) |
| **Alıntı etiketi chunk'lama sırasında üretiliyor** | Yüklemede dosya geçici bir adla diske yazılıyor; `doc.filename`'i sonradan düzeltmek yetmiyordu çünkü `citation_label` çoktan `tmp2wt19fln.txt`'den kurulmuştu. Doğru yer: `chunk_sections`'tan **önce** `section.source_file`'ı değiştirmek |
| **`txt` için alıntı şablonu yoktu** | `build_citation_label` genel dala düşüp `— , s.None` basıyordu. Korpusta txt yok, bu tip yalnızca yüklemeden geliyor; kendi dalı eklendi |
| **Yerelde `INTERNAL_TOKEN` boş** | `azure/.env`'de anahtar var ama değeri yok, bu yüzden yerel backend her isteği 401'liyor (boş beklenen değer = güvenli varsayılan, doğru davranış). Uçtan uca test için `INTERNAL_TOKEN=... uvicorn ...` ile geçici değer verildi |
| **Kalite kapısı `azure/` kapsamına daraltıldı** | `tests/` altındaki 18 test bu iş başlamadan **zaten** kırıktı (`sentence_transformers`, `statsmodels` kurulu değil; Azure dağıtımı torch'u bilinçli attı). `-o addopts=""` şart: `pyproject`'teki `--cov=src` komut satırından eklenen `--cov=azure` ile *kaldırılmıyor*, üstüne biniyor ve kapsam %54'e düşüyor |

### Aşama 1 canlıya alma + Aşama 2 — Analiz sayfası (2026-08-17)

| Konu | Öğrenilen |
|---|---|
| 🚨 **Testler bildirilmemiş bağımlılığı yakalayamaz** | `python-multipart` `azure/requirements.txt`'te yoktu ama geliştirme makinesinde başka bir paketten kurulu olduğu için 163 testin **tamamı geçiyordu**. Konteyner yalnız o dosyayı kurduğundan `api.py` import zamanında `Form data requires "python-multipart"` ile patladı ve revizyon `Failed` oldu. Ders: bir bağımlılık *bildirimini* doğrulayan test, kodu doğrulayan testten farklı bir şey ölçer — `test_requirements.py` bunu yapıyor |
| 🚨 **`provisioningState: Succeeded` konteynerin ayakta olduğunu göstermez** | Azure isteği kabul ettiğinde `Succeeded` döner; uygulama çökse bile. Gerçek durum `az containerapp revision list` içindeki `healthState` / `runningState`. Bozuk revizyon `Succeeded` raporlarken `Unhealthy/Failed` durumundaydı ve trafiği %100 almıştı |
| **`latest` etiketiyle push rollout tetiklemez** | Aynı etiket yeniden push edilince Container Apps yeni revizyon açmaz. `--image ...@sha256:<digest>` ile güncellemek gerekiyor; digest `docker push` çıktısından alınıyor |
| **Push öncesi yerel duman testi ucuz sigortadır** | İkinci kez bozuk imaj göndermemek için imaj yerelde `docker run` ile ayağa kaldırılıp `/api/health` ve `/openapi.json` kontrol edildi. Dört yeni ucun kayıtlı olduğu orada görüldü, canlıda değil |
| **`.internal.` FQDN halka açık DNS'te çözünür** | Plan "DNS hatası bekle" diyordu; gerçekte Azure edge'i tanınmayan host için **HTML 404** ("Azure Container App - Unavailable") döndürüyor. Sızıntı değil — ayrım, yanıtın uygulamadan (JSON) mı altyapıdan (HTML) mı geldiğine bakılarak yapılıyor |
| **Next standalone çıktısı `public/`'i kopyalamaz** | Yerelde `.next/standalone/server.js` doğrudan çalıştırılınca figürler 404 verdi. Bu bir kod kusuru değil, Next'in bilinen davranışı; `Dockerfile` zaten `COPY ... /app/public ./public` yapıyor. Üretim yolu imajın içinde doğrulandı (10 PNG, doğru boyutlarda) |
| **Pandas tablosu ham HTML olarak enjekte edilmedi** | `to_html` çıktısı `<style scoped>` taşıyor ve koyu temada okunmaz metin üretiyor; ayrıca gereksiz enjeksiyon yüzeyi. `HTMLParser` ile başlık + satıra çevrilip uygulamanın kendi tablo bileşeniyle çiziliyor. `<th>` hem başlıkta hem satır etiketinde geçtiği için ayrım `<thead>` içinde olup olmamasıyla yapılıyor |
| **Figürler JSON'a gömülmedi** | 10 PNG toplam 835 KB; base64 olarak `analysis.json` içine konsaydı dosya ~1,1 MB olur ve her sayfa yüklemesinde parse edilirdi. Ayrı dosya olarak yazılıp yalnızca yolları taşınıyor — JSON 97 KB'de kaldı |
| **Tema iki rota arasında paylaşılmalı** | Sohbet temayı `<html>` sınıfı + `localStorage` ile yönetiyordu; `/analiz` ayrı bir rota olduğu için mantık kopyalanmasa koyu temadaki kullanıcı açık sayfaya düşerdi. `lib/theme.ts` tek kaynak oldu, sohbet sayfası da ona taşındı |
| **Bölümleme notebook'un `## ` başlıklarından çıkıyor** | Ayırıcı markdown hücreleri zaten `## ` ile bölüm açıyordu; ek işaretleme gerekmedi. Çapa kimlikleri Türkçe harfler ASCII'ye indirgenerek üretiliyor — `casefold()` tek başına `İ`'yi iki kod noktasına açıp tarayıcıda eşleşmez kimlik üretirdi |
| **`public/analiz/` giriş arkasında** | `middleware.ts` matcher'ı `_next/static` dışında her şeyi kapsıyor. İddia varsayılmadı, ölçüldü: anonim istek hem `/analiz` hem `/analiz/figur-01.png` için 307 → `/login` |

### Aşama 3 — Model katalogu ve ayarlar menüsü (2026-08-17)

| Konu | Öğrenilen |
|---|---|
| 🚨 **`list-models` kota demek değildir** | Spec altı modeli "hepsi mevcut ve hepsi GlobalStandard" diye listelemişti; `list-models` gerçekten öyle diyor. Ama o komut *katalogda var mı* sorusunu yanıtlıyor, *dağıtabilir miyim* sorusunu değil. eastus'ta `text-embedding-3-large`, `embed-v-4-0`, `Cohere-rerank-v4.0-fast` ve `cohere-command-a` için kota **sıfır**dı; dağıtım denemesi `InsufficientQuota` ile döndü. Doğru komut `az cognitiveservices usage list -l <bölge>`. Dördü de swedencentral/eastus2'de kotalı ama hesap eastus'ta — ikinci hesap mimariyi değiştireceği için kullanıcı kararıyla kapsam dışı bırakıldı |
| **Üç embedding indeksi ve rerank yapılmadı** | Kota olmadan `text-embedding-3-large` ve `embed-v-4-0` dağıtılamadı; rerank modeli de öyle. Spec'in D ve F bölümleri bu yüzden uygulanmadı. Menü bunları "kota yok" sebebiyle devre dışı gösteriyor |
| 🚨 **gpt-5-mini ajan döngüsünde tıkanıyor** | Ölçüldü (gerçek korpus, aynı soru): gpt-4.1-mini 2 turda 1 arama yapıp 2 atıflı doğru cevap veriyor; gpt-5-mini **6 turda bile** aynı aramayı tekrarlayıp hiç metin yazmadan bitiyor. Sebep sistem promptu: "Cevap vermeden önce HER ZAMAN search_documents çağırmalısın" talimatını akıl yürütme adımında her turda yeniden değerlendiriyor. Tur sınırını 3→6 çıkarmak çözmedi. Promptu modele göre yeniden yazmak bu aşamanın kapsamı dışında bırakıldı, bulgu `quality_warning` ile menüde gösteriliyor |
| 🚨 **Phi-4-mini atıf işareti koymuyor** | Doğru kaynağı (`calisan_sss_rehberi.xlsx` satır 4) buluyor ve içeriği alıyor ama cevaba `[1]` koymuyor; atıf kapısı haklı olarak reddediyor. Yani "araç çağırıyor" yeterli değil — atıflı yazabilmesi ayrı bir yetenek |
| **GPT-5 parametre farkları gerçek** | Sondalanarak doğrulandı: `max_tokens` → HTTP 400 (`max_completion_tokens` isteniyor), `temperature=0` → HTTP 400 (yalnızca varsayılan 1). Bayrak olarak katalogda duruyor, istemcide `if model_id ==` zinciri yok |
| **Akıl yürütme tokenı bütçeyi yiyor** | gpt-5-mini tek kısa cevapta 128 `reasoning_tokens` harcadı. 1024'lük ortak sınır bırakılsaydı cevap sessizce boş dönebilirdi; bu modelin sınırı 4096 |
| **Phi için ayrı SDK gerekmedi** | Spec `azure-ai-inference` paketini ve ikinci bir uç adresini öngörüyordu. Ölçüm bunu çürüttü: `Phi-4-mini-instruct` mevcut Azure OpenAI ucundan sorunsuz çalışıyor ve araç çağırıyor. Yeni bağımlılık eklenmedi |
| 🚨 **Stub'lı testler yanlış öznitelik adını kaçırdı** | `_agent_for` `base.tools` okuyordu ama gerçek alan `base.toolbox`. Tüm API testleri ajanı stub'ladığı için 200 dönüyordu; hata yalnızca gerçek korpusla çalıştırınca ortaya çıktı. Gerçek `Agent` alanlarına bakan bir test yazılıp düzeltildi — stub, stub'ladığı şeyin sözleşmesini doğrulamaz |
| **Model seçimi indeksi yeniden yüklemiyor** | `_agent_for` yalnızca LLM istemcisini değiştiriyor; retriever, indeks ve araç kutusu modelden bağımsız. Aksi hâlde her istek 276 parçayı diskten yeniden okurdu |
| **İstek gövdesi tek yerden kuruluyor** | `buildAskBody` model alanını ekliyor. Çağıran taraf `readStoredModel()` çağırıp alanı elle koysaydı, ikinci bir çağrı yeri eklendiğinde sessizce unutulur ve o yol hep varsayılan modelle çalışırdı |

## 5. Açık Sorular / Bekleyen Kararlar

- **`gemini-3.5-flash` model ID'si doğrulanmadı.** Kullanıcı verdi, katalogda öyle yazıldı;
  Google'ın resmi ID listesiyle teyit edilmedi. Yanlışsa `404` döner.
