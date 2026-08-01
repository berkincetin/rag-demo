# Veri Keşif Bulguları

Bu dosyadaki tüm sayılar, verinin kendisi üzerinde çalıştırılan ölçümlerden gelir
(pandas / pypdf / python-docx). Tahmin veya varsayım değildir. Tasarımı doğrudan
etkileyen bulgular **kalın** işaretlendi.

---

## 1. Bölüm 1 — RAG Korpusu (`AI Engineer/Rag_Agent/`)

### 1.1 Envanter

| Dosya | Format | Ölçü | Yapı |
|---|---|---|---|
| `Aksef 500 mg FKTB_Onaylı KUB.pdf` | PDF | 12 sayfa, ~24.350 karakter | Numaralı KÜB bölümleri (1 → 6.6), 27 başlık tespit edildi |
| `Duxet 30 mg GRSK_Onaylı KUB.pdf` | PDF | 24 sayfa, ~57.226 karakter | Aynı KÜB şablonu, 32 başlık |
| `ik_surecleri_politikası.docx` | DOCX | 84 dolu paragraf + **7 tablo** | Heading 1 (8 adet) / Heading 2 (16 adet) hiyerarşisi |
| `arac_kullanim_proseduru.docx` | DOCX | 54 dolu paragraf + **9 tablo** | Heading 1 (10) / Heading 2 (8) |
| `calisan_sss_rehberi.xlsx` | XLSX | **3 sayfa** (Genel SSS 17×6, IT Sistem Rehberi 14×5, Onboarding 19×6) | Başlık satırı kaymalı |
| `Anonim_Urun_Taksonomi_100Satir.xlsx` | XLSX | 100 satır × 15 kolon | Düz kayıt tablosu |

**Toplam korpus ≈ 95–100 bin karakter.** Bu, tasarımın en önemli girdisi: korpus çok küçük.
→ Ağır vektör altyapısı (Qdrant/Weaviate/pgvector) gereksiz; embedding + in-process arama yeterli.
Beklenen chunk sayısı **300–450**.

### 1.2 PDF Yapısı — Bölüm Tespiti Çalışıyor

KÜB dosyaları standart "Kısa Ürün Bilgisi" şablonunda; `^(\d{1,2}(\.\d{1,2}){0,2})\s+Başlık$`
düzeni ile bölümler ayıklanabiliyor:

```
s1   1        BEŞERİ TIBBİ ÜRÜNÜN ADI
s1   4.1      Terapötik endikasyonlar
s1   4.2      Pozoloji ve uygulama şekli
s3   4.4      Özel kullanım uyarıları ve önlemleri
s7   5.1      Farmakodinamik özellikler
...
```

**Bu bulgu Z3 (kaynak gösterimi) gereksinimini "sayfa numarası"nın ötesine taşıyor:**
atıf `Aksef 500 mg KÜB — Bölüm 4.2 Pozoloji ve uygulama şekli, s.2` şeklinde verilebilir.
Bu, case'in "dosya adı **veya bölüm**" şartını en güçlü biçimde karşılar.

⚠️ **Yanlış pozitif riski:** Duxet PDF'inde sayfa 15'te dipnot satırları (`7 Plasebodan
istatistiksel olarak anlamlı değil`) başlık gibi görünüyor. Çözüm: KÜB bölüm numaraları
beyaz listesi (1–6.6) + monoton artış kontrolü. → TRD §4.1

### 1.3 DOCX Yapısı — Tablolar İçeriğin Büyük Kısmı

| Belge | Paragraf karakteri | Tablo sayısı |
|---|---|---|
| `ik_surecleri_politikası.docx` | 4.916 | 7 |
| `arac_kullanim_proseduru.docx` | 3.651 | 9 |

**Kritik:** `python-docx` ile `document.paragraphs` okunduğunda **tablolar tamamen kaçırılır.**
Oysa en sorgulanabilir bilgi tablolarda:

```
['Pozisyon Seviyesi', 'Arac Hakki', 'Yakit Limiti (Ay)', 'Ozel Kullanim']
['Genel Mudur / Yonetim Kurulu', 'Tahsisli (premium segment)', 'Sinirsiz', 'Tam']
['Direktor / Bolum Baskani', 'Tahsisli (ust orta segment)', '1.500 TL/ay', 'Hafta sonu dahil']
```

"Direktörün aylık yakıt limiti nedir?" sorusu **yalnızca tablodan** cevaplanabilir.
→ DOCX loader tabloları Markdown tablosuna çevirip, ait olduğu başlığın altına
yerleştirmeli. Ayrıca `paragraph.style` bazı paragraflarda `None` dönüyor (ham `Normal`
stili yok) — kod bunu tolere etmeli, aksi halde `AttributeError` alınıyor (ölçümde alındı).

### 1.4 ⚠️ En Kritik Bulgu — Türkçe Karakter Tutarsızlığı

Belgeler arasında **karakter kodlaması tutarsız**:

| Kaynak | Örnek metin |
|---|---|
| DOCX (İK politikası) | `Insan Kaynaklari Surecler Politikasi`, `yıllık izin`, `surecinın` |
| XLSX (SSS) | `Yıllık izin talebimi nasıl yapabilirim?`, ama `Sorumlı: IK & IT` |
| PDF (KÜB) | `Terapötik endikasyonlar`, `İstenmeyen etkiler` (tam Türkçe) |

DOCX'ler ağırlıklı ASCII'ye indirgenmiş (`ç→c, ş→s, ğ→g, İ→I, ö→o, ü→u`) ama **kısmen**:
aynı cümlede `yıllık` (Türkçe ı) ve `Kaynaklari` (ASCII i) birlikte geçiyor.

**Sonuçları:**
1. Kullanıcı "İnsan Kaynakları" yazarsa, salt kelime eşleşmeli arama (BM25) DOCX'i **bulamaz**.
2. Salt vektör arama da zayıflar: tokenizer için `Kaynakları` ≠ `Kaynaklari`.
3. **Çözüm:** hem indeksleme hem sorgu tarafında Unicode NFKD + Türkçe-duyarlı ASCII katlama
   (`İ→I`, `ı→i`, `ş→s`, `ğ→g`, `ç→c`, `ö→o`, `ü→u`) uygulanmış bir *arama alanı* tutulmalı;
   gösterilen metin orijinal kalmalı.

Bu, hibrit aramayı (BM25 + dense) "ekstra özellik" olmaktan çıkarıp **doğruluk gereksinimi**
haline getiriyor. → Karar kaydı ADR-004.

### 1.5 XLSX Yapısı — Başlık Satırı Kaymalı

`calisan_sss_rehberi.xlsx` her sayfada 2 satırlık ön bilgi taşıyor; gerçek kolon başlıkları
**3. satırda**:

```
satır 0: TEKNOPARK YAZILIM A.S. — CALISAN SSS REHBERI
satır 1: Son Guncelleme: Ocak 2025 | Sorumlı: IK & IT Departmanları | Versiyon: 4.1
satır 2: # | Kategori | Alt Kategori | Soru & Cevap | Sorumlu Departman | Son Guncelleme
satır 3: 1 | Insan Kaynaklari | Izinler | "SORU: ...\n\nCEVAP: ..." | ...
```

→ `pd.read_excel(header=0)` **yanlış** okur. Loader başlık satırını otomatik tespit etmeli
(ilk satır ki hücrelerinin ≥%70'i dolu ve `Unnamed:` içermiyor) veya sayfa başına
konfigüre edilmeli.

**Chunk stratejisi bulgusu:** SSS'de bir satır = bir tam Soru&Cevap çifti (tek hücrede,
`SORU:` / `CEVAP:` ayraçlı). Bu doğal bir chunk sınırıdır — satırı bölmek **kesinlikle
yanlış** olur. Aynı şey taksonomide de geçerli: 1 satır = 1 ürün kaydı (15 alan).

`Anonim_Urun_Taksonomi_100Satir.xlsx` kolonları: Terapötik Sistem, Tedavi Grubu, Endikasyon,
Molekül/Etken Madde, Ürün, Medikal Müdür, Medikal Grup Müdürü, Medikal Direktörü, Ürün Müdürü,
Bölüm Müdürü, Pazarlama Müdürü, Tanıtım Müdürü, Pazarlama Direktörü, Pazarlama Bölümü,
Pazarlama Direktörlük Grubu.
→ Chunk metni `"Ürün: Vitatin95 | Terapötik Sistem: Kardiyovasküler | ... "` formatında
alan-adı:değer olarak serileştirilmeli, yoksa "Vitatin95'in ürün müdürü kim?" sorusu
cevaplanamaz.

### 1.6 Dosya Adı Uyarısı

`ik_surecleri_politikası.docx` dosya adında Türkçe `ı` karakteri var (case metninde
`ik_surecleri_politikasi.docx` olarak ASCII yazılmış). Kod dosya adlarını **sabit yazmamalı**,
klasörü `glob` ile taramalı. Windows'ta `PYTHONIOENCODING=utf-8` olmadan konsol çıktısı
`UnicodeEncodeError` veriyor (ölçüm sırasında alındı) — README'de not düşülecek.

---

## 2. Bölüm 2 — Satış Veri Seti (`AI Engineer/bolum2_veriseti.xlsx`)

### 2.1 Fiziksel Yapı

- Tek sayfa (`Sheet1`), **378 satır × 375 kolon**.
- **3 satırlık hiyerarşik başlık:** satır 1 = Yıl, satır 2 = Ay (Türkçe ad), satır 3 = Metrik.
- Kolon 0–2 = `Pazar`, `Şirket`, `Ürün`. Kolon 3+ = 124 ay × 3 metrik = 372 kolon. ✔ tutarlı.
- Veri satırları 4. satırdan başlar: **374 seri** (Pazar × Şirket × Ürün).
- **Tarih aralığı: 2016-01 → 2026-04, tam 124 ay.** ✔ case ile uyumlu.
- Yinelenen anahtar **yok** (0 duplicate).

→ Veri **geniş (wide) formatta**; her analiz öncesi long/tidy formata çevrilmeli:
`(Pazar, Şirket, Ürün, Tarih, Brüt Kutu, MF Oran, Net TL)`.

### 2.2 Seri Dağılımı

| Pazar | Şirket 1 | Şirket 2 | Diğer Şirket |
|---|---|---|---|
| A Pazarı | **10** (Ürün-A … Ürün-J) | 37 | 134 |
| B Pazarı | **4** (FP, FQ, FR, FS) | 13 | 55 |
| C Pazarı | **2** (Ürün 1, Ürün 2) | 6 | 68 |
| D Pazarı | **2** (Ürün 77, Ürün 78) | 2 | 41 |

Şirket 1 toplam **18 ürün-pazar serisi**. Case'in "A Pazarı'nda Ürün-A'dan Ürün-J'ye 10 ürün"
ifadesi doğrulandı. ✔

**Son 12 ayın Brüt Kutu pazar payları (ham veriyle):**

| Pazar | Şirket 1 | Şirket 2 | Diğer |
|---|---|---|---|
| A | %12,4 | %52,2 | %35,4 |
| B | %13,1 | %44,1 | %42,8 |
| C | %6,0 | %46,3 | %47,7 |
| D | **%3,9** | %19,7 | %76,4 |

→ A2 görevinin cevabı bu yönde şekillenecek: Şirket 1 en güçlü B'de (pay olarak),
en zayıf D'de. (Nihai yorum temizlenmiş veriyle yapılacak.)

### 2.3 🚨 EN KRİTİK BULGU — MF Oran Ölçek Tutarsızlığı

`MF Oran` kolonu **pazarlar arasında farklı birimde**:

**"MF Oran > 1" olan gözlemlerin oranı:**

| Pazar | Şirket 1 | Şirket 2 | Diğer Şirket |
|---|---|---|---|
| A | 0,000 | 0,000 | 0,004 |
| **B** | **0,861** | **0,741** | **0,272** |
| C | 0,000 | 0,000 | 0,004 |
| D | 0,000 | 0,000 | 0,045 |

**Medyan MF Oran:**

| Pazar | Şirket 1 | Şirket 2 | Diğer |
|---|---|---|---|
| A | 0,000 | 0,000 | 0,000 |
| **B** | **7,429** | **5,912** | **0,568** |
| C | 0,000 | 0,117 | 0,049 |
| D | 0,000 | 0,117 | 0,167 |

**B Pazarı MF Oran değerleri oran (0–1) değil, yüzde (0–100) ölçeğinde.** Doğrulama —
B Pazarı / Şirket 1 / Ürün-FR için birim fiyat iki yorum altında hesaplandı:

| Tarih | Brüt Kutu | MF Oran | Net TL | Fiyat (oran yorumu) | Fiyat (yüzde yorumu) |
|---|---|---|---|---|---|
| 2016-01 | 27.378 | 9,538 | 206.073 | **−0,88 TL** ❌ | **8,32 TL** ✔ |
| 2016-03 | 56.533 | 10,131 | 410.180 | **−0,79 TL** ❌ | **8,07 TL** ✔ |
| 2026-03 | — | 6,507 | — | **−24,08 TL** ❌ | **141,84 TL** ✔ |

Karşılaştırma: A Pazarı / Ürün-A'da oran yorumuyla birim fiyat 2016'da 10,28 TL →
2026'da 157,20 TL (10 yılda ~15x, TL enflasyonuyla tutarlı). B Pazarı yüzde yorumuyla
8,32 → 148,15 TL, **aynı büyüklük mertebesinde**. Oran yorumu ise negatif fiyat üretiyor
(Net Kutu negatife düşüyor).

**Karar:** B Pazarı MF Oran değerleri 100'e bölünecek. Uygulama, sabit "B Pazarı" kuralı
yerine **program tespitiyle** yapılmalı (grup medyanı > 1 ⇒ yüzde ölçekli), böylece kural
gerekçelendirilebilir ve veri değişirse kırılmaz. → TRD §3.2

**Bu düzeltme yapılmazsa A4, A6 ve A7 görevlerinin tamamı yanlış sonuç verir**
(negatif Net Kutu, negatif birim fiyat, anlamsız promosyon maliyeti).

### 2.4 Diğer Veri Kalitesi Sorunları

| Sorun | Ölçüm | Etki | Planlanan Çözüm |
|---|---|---|---|
| **Aşırı MF outlier'ları** | Ölçek düzeltmesi sonrası bile Diğer Şirket'te max **469,5** (A: 15,0, C: 246,0) | Pazar payı ve fiyat hesabını bozar | `[0, 0.95]` aralığına kırp + `mf_flag` kolonu; kırpılanlar raporlanır |
| **Negatif Brüt Kutu** | **1.158 gözlem** (A/Diğer 579, C/Diğer 280, B/Diğer 125, D/Diğer 102, Şirket 1'de 3) | İade/düzeltme kayıtları; toplamları düşürür | Ayrı `is_return` bayrağı; toplamlarda korunur (net hacim doğru olsun), tahmin girdisinde 0'a sabitlenir |
| **Negatif Net TL** | **1.168 gözlem** | Aynı | Aynı |
| **Sıfır Brüt Kutu ayları** | **9.536 gözlem** (tüm veri) | Ürün henüz yok / çıkmış vs. gerçek sıfır ayrımı yok | Serinin ilk pozitif satışından önceki dönem kırpılır; sonrası gerçek sıfır kabul edilir |
| **Tamamen boş hücreler** | 139.128 hücrenin **28.006'sı boş** (%20) | Panel dengesiz | Ürün yaşam döngüsü olarak modellenir, 0 ile doldurulmaz |
| **Ürün adı tutarsızlığı** | C/D pazarlarında `Ürün 1` vs `Ürün  2` (**çift boşluk**) | Gruplamada ayrı ürün gibi görünme riski | `re.sub(r'\s+', ' ', ad).strip()` normalizasyonu (normalizasyon sonrası çakışma yok — doğrulandı) |
| **Ürün adı çakışması** | `Ürün-A`, `Ürün-B` hem Şirket 1 hem A Pazarı/Diğer Şirket'te var; `Ürün-FP` hem Şirket 1 hem Şirket 2'de (B Pazarı) | Yanlış birleştirme riski | Birincil anahtar **daima** `(Pazar, Şirket, Ürün)` — asla tek başına `Ürün` |

### 2.5 🚨 Tahmin Görevi (A7) İçin Kritik Kısıt

Şirket 1'in 18 serisinin **veri uzunlukları çok farklı**:

| Pazar | Ürün | İlk satış | Son satış | Dolu ay sayısı |
|---|---|---|---|---|
| A | Ürün-A … Ürün-J (10 ürün) | 2016-01 | 2026-04 | **124** (tam) |
| B | Ürün-FQ | 2016-05 | 2026-04 | 120 |
| B | Ürün-FR, Ürün-FS | 2016-01 | 2026-04 | 124 |
| B | **Ürün-FP** | 2024-01 | 2026-04 | **27** |
| C | Ürün 2 | 2017-12 | 2026-04 | 101 |
| C | **Ürün 1** | 2024-01 | 2024-01 | **1** ⚠️ |
| D | Ürün 77 | 2021-11 | 2026-04 | 52 |
| D | **Ürün 78** | 2025-06 | 2026-04 | **11** ⚠️ |

**Sonuçlar:**
- `C Pazarı / Ürün 1` **tek gözlemli** → mevsimsellik (A3) ve tahmin (A7) matematiksel olarak
  imkânsız. Notebook'ta bunu gizlemek yerine **açıkça raporlamak** doğru davranış.
- `D Pazarı / Ürün 78` (11 ay) ve `B Pazarı / Ürün-FP` (27 ay) → 12 aylık mevsimsel döngü
  tam çıkmıyor; sadece naive baseline uygulanabilir, ML modeline global havuzda katılır.
- Serilerin çoğunluğu A Pazarı'ndan geliyor (10/18). Model performans metrikleri **pazar
  bazında** raporlanmazsa A Pazarı sonucu diğerlerini maskeler — case zaten pazar bazında
  istiyor. ✔
- **Bu heterojenlik, A7'nin "aynı model mimarisi tüm pazarlarda geçerli mi?" sorusunun
  cevabının çekirdeği:** hayır, ve gerekçesi seri uzunluğu + mevsimsellik gücü.

### 2.6 Türetilmiş Metrik Tanımları (case'ten)

```
Net Kutu   = Brüt Kutu × (1 − MF Oran)        # MF ölçek düzeltmesinden SONRA
Birim Fiyat = Net TL / Net Kutu                # Net Kutu ≤ 0 ise tanımsız → NaN
```

**Guard gerekli:** MF Oran = 1 olduğunda Net Kutu = 0 → sıfıra bölme. Ayrıca MF > 1
kalırsa negatif fiyat. Her iki durum da `NaN` üretmeli, `inf` değil.

---

## 3. Ortam Bulguları

| Öğe | Durum |
|---|---|
| Python | 3.10.3 (Windows, `AppData\Local\Programs\Python\Python310`) |
| Mevcut paketler | `pandas`, `openpyxl`, `python-docx`, `pypdf` ✔ |
| Konsol kodlaması | cp1252 → Türkçe çıktı için `PYTHONIOENCODING=utf-8` gerekli |
| Repo durumu | `main` dalı, tek commit, `docs/` ve kod henüz yok |
| `.gitignore` | Standart Python şablonu mevcut |
