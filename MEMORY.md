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

---

## 5. Açık Sorular / Bekleyen Kararlar

_(Şu an yok. Bir karar kullanıcıya sorulacaksa buraya yaz, cevap gelince §1'e taşı.)_
