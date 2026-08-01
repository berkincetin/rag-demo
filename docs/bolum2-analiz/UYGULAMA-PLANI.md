# Uygulama Planı — Bölüm 2: İlaç Sektörü Satış & Talep Analizi

**Ön koşul:** Bölüm 1 (RAG) teslim edilebilir durumda olmalı.
Toplam tahmini süre: **~12–16 saat**.

Her adımın **Bitti Tanımı (DoD)** var. Faz sırası, tüm analizlerin dayandığı veri
temelini önce sağlamlaştıracak şekilde kuruldu — MF ölçek hatası düzeltilmeden yapılan
hiçbir analiz güvenilir değil (bulgular §2.3).

---

## Faz 0 — İskelet (~45 dk)

| Adım | İş | DoD |
|---|---|---|
| 0.1 | `src/analysis/`, `notebooks/`, `figures/`, `tests/` klasörleri | Mevcut |
| 0.2 | `requirements-analysis.txt` (TRD §7) | Temiz venv'de kuruluyor |
| 0.3 | Veri dosyası yolu konfigürasyonu (`AI Engineer/bolum2_veriseti.xlsx`) | Tek yerden okunuyor |
| 0.4 | Windows UTF-8 notu (`PYTHONIOENCODING=utf-8`) README'ye | Notlandı |

---

## Faz 1 — Yükleme ve Temizleme (~4 saat) ⚠️ Kritik faz

### 1.1 `load.py` — wide → tidy (~1,5 saat)
- 3 satırlık başlığın ayrıştırılması, Türkçe ay eşlemesi, unpivot.
- Doğrulama assert'leri (TRD §2).
- **DoD:**
  - Çıktı tidy DataFrame; `tarih.nunique() == 124`, aralık 2016-01 → 2026-04.
  - `(pazar, sirket, urun)` benzersiz kombinasyon sayısı **374**.
  - Şirket 1 için pazar başına ürün sayısı: A=10, B=4, C=2, D=2 ✔
  - `test_load_shape` yeşil.

### 1.2 `clean.py` — MF ölçek düzeltmesi (~1 saat) 🚨 **En kritik adım**
- `detect_mf_scale()` program tespiti (TRD §3.2).
- **DoD:**
  - Fonksiyon yalnızca `B Pazarı` için 100 döndürüyor (A/C/D → 1).
  - Düzeltme sonrası B/Şirket 1/Ürün-FR birim fiyatı: 2016'da 8–9 TL, 2026'da 130–150 TL
    bandında ve **pozitif**.
  - `test_mf_scale_detection` ve `test_birim_fiyat_pozitif` yeşil.
  - Düzeltmenin gerekçesi (öncesi/sonrası fiyat tablosu) notebook'a girecek şekilde
    fonksiyondan raporlanabiliyor.

### 1.3 `clean.py` — diğer temizleme kuralları (~1 saat)
- V7 ürün adı normalizasyonu, V3 MF kırpma + bayrak, V4 iade bayrağı, V5 seri kırpma.
- **DoD:**
  - Normalizasyon sonrası anahtar çakışması **0**.
  - `is_return` sayısı ≈ 1.158.
  - `mf_clipped` sayısı raporlanıyor.
  - `test_urun_ad_normalizasyonu`, `test_seri_kirpma` yeşil.

### 1.4 `metrics.py` — türetilmiş metrikler (~30 dk)
- Net Kutu, Birim Fiyat (V8 guard), pazar payı, HHI, YoY.
- **DoD:** `test_net_kutu_guard`, `test_metrics_market_share` yeşil; hiçbir yerde `inf` yok.

---

## Faz 2 — Notebook Omurgası ve Veri Kalitesi Raporu (~1,5 saat)

| Adım | İş | DoD |
|---|---|---|
| 2.1 | `notebooks/analiz.ipynb` iskeleti: 0. Veri Kalitesi + 7 görev başlığı | Tüm başlıklar yerinde |
| 2.2 | `plots.py` ortak stil (TR etiketler, sabit palet, sayı biçimi) | Örnek grafik doğru render |
| 2.3 | **Bölüm 0 — Veri Kalitesi Raporu:** ham veri profili, 7 sorunun tespiti, uygulanan düzeltmeler tablosu, MF ölçek kanıt tablosu | Değerlendiren, hangi düzeltmenin neden yapıldığını tek bakışta görüyor |

> Bölüm 0 opsiyonel değil: MF ölçek düzeltmesi gibi agresif bir müdahalenin
> gerekçelendirilmemesi, case'in "kararların gerekçelendirilmesi" kriterinden puan kaybettirir.

---

## Faz 3 — Görev A1–A3 (~3 saat)

### 3.1 A1 — Satış performansı ve ürün kırılımı (~1 saat)
- Grafik 1: 4 pazar × (Brüt Kutu bar + Net TL çizgi), son 24 ay.
- Grafik 2: pazar başına ürün katkısı (yığılmış alan) + Pareto tablosu.
- Zirve/dip ay karşılaştırma tablosu (4 pazar yan yana).
- **DoD:** ≥2 grafik; "hangi ürünler domine ediyor" sorusu **sayıyla** cevaplanmış
  (ör. "A Pazarı'nda ilk 3 ürün hacmin %X'i"); teknik + iş yorumu yazılmış.

### 3.2 A2 — Pazar yapısı ve rekabet pozisyonu (~1 saat)
- 4 pazar için 2016→2026 yığılmış pay grafiği.
- HHI zaman serisi.
- En güçlü/en zayıf pazar + orantısız pay tablosu (pazar CAGR vs Şirket 1 CAGR).
- **DoD:** Paylar her ay %100'e toplanıyor (assert); ölçülen referans değerler
  (son 12 ay: A %12,4 · B %13,1 · C %6,0 · D %3,9) temizlenmiş veriyle
  yeniden hesaplanıp yorumlanmış; teknik + iş yorumu.

### 3.3 A3 — Mevsimsellik (~1 saat)
- STL ile ürün × ay mevsimsel indeks; mevsimsellik gücü metriği.
- Isı haritası (pazar başına panel).
- V9 filtresine takılan seriler "yetersiz veri" tablosunda **açıkça** listelenir
  (`C/Ürün 1` = 1 ay, `D/Ürün 78` = 11 ay).
- Aynı ürünün pazarlar arası tutarlılığı → Şirket 1'de ürün setleri pazarlar arası
  ayrık olduğu için soru **pazar seviyesinde** cevaplanır, bu sınır belirtilir (TRD §5/A3).
- **DoD:** ≥1 ısı haritası; mevsimsellik gücü tablosu; stok planlama/hedef belirleme
  çıkarımı iş yorumunda somut (ör. "X ürününde Eylül indeksi 1,4 → stok +%40").

---

## Faz 4 — Görev A4–A6 (~3,5 saat)

### 4.1 A4 — MF'in satışlara etkisi (~1,5 saat) 📊 İstatistik ağırlıklı
- Yüksek MF ürün-pazar kombinasyonlarının tespiti ve sıralaması.
- Olay çalışması: MF > %10 → t+1 değişimi; kontrol grubu aynı serinin düşük MF ayları.
- Mann-Whitney U + Welch t-testi + etki büyüklüğü; **Benjamini-Hochberg FDR** düzeltmesi.
- Mevsimsel indekse göre düzeltilmiş alternatif sonuç metriği.
- **DoD:**
  - Pazar × ürün tablosu: olay sayısı, ortalama Δ, p, FDR-q, **anlamlı/anlamsız** kolonu.
  - "Bu etki tüm pazarlarda benzer mi?" sorusu tabloya dayanarak cevaplanmış.
  - ≥1 grafik (dağılım kutu grafiği + p anotasyonu).
  - Yorumda çoklu test düzeltmesinin neden yapıldığı 1 cümleyle açıklanmış.

### 4.2 A5 — Rakip karşılaştırması ve büyüme (~1 saat)
- Şirket 1 vs Şirket 2 yıllık büyüme tablosu (pazar bazında).
- Rekabet yoğunluğu: HHI + ilk-2 payı + pay volatilitesi.
- Diğer Şirket hacim kaybı kanıtı: trend regresyonu (eğim + p) + pay transferi eşleştirmesi
  (pay değişimleri toplamı ≈ 0 tutarlılık kontrolü).
- **DoD:** "Diğer Şirket kaybediyor" iddiası **istatistiksel kanıtla** (eğim, p-değeri)
  destekli; kaybedilen payın nereye gittiği gösterilmiş; teknik + iş yorumu.

### 4.3 A6 — Birim fiyat ve promosyon maliyeti (~1 saat)
- Ürün × pazar birim fiyat trendi + CAGR.
- Pazarlar arası fiyat sapması (varyasyon katsayısı) — not: Şirket 1'de aynı ürün
  birden fazla pazarda olmadığı için karşılaştırma **pazar ortalama fiyat seviyesi**
  üzerinden yapılır, bu sınır belirtilir.
- Promosyon gelir kaybı: `bedava kutu × birim fiyat`, yıllık TL, ürün-pazar bazında.
- Maliyet-fayda: yüksek MF dönemlerindeki hacim artışı vs. gelir kaybı (ROI tablosu).
- **DoD:** Yıllık TL kayıp tablosu somut sayılarla; "bu maliyet hacim artışını haklı
  kılıyor mu" sorusu **evet/hayır + gerekçe** ile cevaplanmış; nominal fiyat
  sınırlılığı (enflasyon düzeltmesi yok) belirtilmiş.

---

## Faz 5 — Görev A7: Tahmin (~3 saat)

### 5.1 `forecast.py` — özellik mühendisliği ve baseline'lar (~1 saat)
- Lag/rolling/takvim özellikleri; MF özellik seti ayrı bayrakla.
- `naive`, `snaive`, `ma3` implementasyonları.
- Walk-forward (expanding, son 12 ay) değerlendirme çatısı.
- **DoD:** Baseline'lar tüm serilerde çalışıyor; kısa seriler hata vermiyor;
  metrik fonksiyonları (`MAE/RMSE/MAPE/WAPE/sMAPE`) sıfır bölmesi üretmiyor.

### 5.2 `forecast.py` — global LightGBM + ablasyon (~1 saat)
- `log1p` hedef dönüşümü; kategorik `pazar`/`urun`.
- İki varyant: `lgbm` (MF özellikleriyle) ve `lgbm_no_mf`.
- **DoD:** Her iki model walk-forward'da eğitiliyor; toplam süre < 2 dk;
  tahminler `expm1` ile geri çevrilmiş ve negatif değer içermiyor.

### 5.3 Notebook A7 bölümü (~1 saat)
- **Tablo 1:** Model × Pazar → MAE, MAPE, RMSE, WAPE (case'in istediği tablo).
- **Tablo 2:** MF ablasyonu — pazar bazında delta.
- **Tablo 3:** Mevsimsellik gücü yüksek/düşük seriler ayrımında model sıralaması.
- Grafik: seçili serilerde gerçek vs. tahmin (son 12 ay).
- **DoD:**
  - Pazar bazında hata metrikleri tablosu tam ✔ (case'in açık şartı).
  - "Aynı model mimarisi tüm pazarlarda geçerli mi?" sorusu Tablo 3'e dayanarak cevaplanmış.
  - "MF Oranı'nın tahmin gücüne katkısı" ablasyon delta'sıyla **sayısal** cevaplanmış.
  - Kısa seriler ayrı etiketle raporlanmış, gizlenmemiş.

---

## Faz 6 — Kapanış (~1,5 saat)

| Adım | İş | DoD |
|---|---|---|
| 6.1 | Notebook `Restart & Run All` uçtan uca | Hatasız; tüm çıktılar kaydedilmiş |
| 6.2 | Her 7 görevin altında **teknik yorum** + **iş yorumu** başlıkları dolu | Boş bırakılmış yorum yok |
| 6.3 | Figürlerin `figures/` altına PNG kaydı | 7+ PNG mevcut |
| 6.4 | Yönetici özeti bölümü (notebook başına): 5–7 maddelik ana bulgular | Yazıldı |
| 6.5 | `tests/test_analysis.py` tam yeşil | 7 test geçiyor |
| 6.6 | README'ye Bölüm 2 kurulum/çalıştırma adımları | Yazıldı |

---

## Faz Özeti

```
Faz 0 (0,75s) ─► Faz 1 (4s) ─► Faz 2 (1,5s) ─► Faz 3 (3s) ─► Faz 4 (3,5s) ─► Faz 5 (3s) ─► Faz 6 (1,5s)
  iskelet      temizleme ⚠️    omurga+DQ      A1–A3        A4–A6 📊         A7 tahmin     kapanış
```

**Kritik yol Faz 1.** MF ölçek düzeltmesi doğru yapılmazsa A4, A6 ve A7'nin tamamı
yanlış sonuç verir; bu yüzden Faz 1.2'nin DoD'si sayısal doğrulama içeriyor.

## Erken Doğrulama Noktaları

| Ne zaman | Kontrol | Başarısızsa |
|---|---|---|
| Faz 1.1 sonu | 374 seri × 124 ay, Şirket 1 dağılımı A=10/B=4/C=2/D=2 | Unpivot mantığını gözden geçir |
| Faz 1.2 sonu | B/Ürün-FR birim fiyatı pozitif ve A/Ürün-A ile aynı mertebede | Ölçek tespitini yeniden değerlendir |
| Faz 3.2 sonu | Pazar payları %100'e toplanıyor | Toplulaştırma hatası var |
| Faz 5.2 sonu | LightGBM ≥1 baseline'ı yeniyor | Özellikleri/log dönüşümünü gözden geçir; yenmiyorsa **bu da bir bulgudur**, dürüstçe raporla |
| Faz 6.1 sonu | Notebook uçtan uca temiz | Teslim etme |
