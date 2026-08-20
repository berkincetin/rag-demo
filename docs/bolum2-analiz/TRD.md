# TRD — Bölüm 2: İlaç Sektörü Satış & Talep Analizi

Veri gerçekleri: [../01-veri-kesif-bulgulari.md](../planlama/01-veri-kesif-bulgulari.md) §2.
Kararlar: [../02-karar-kaydi.md](../planlama/02-karar-kaydi.md) ADR-009, ADR-010.

---

## 1. Mimari

```
AI Engineer/bolum2_veriseti.xlsx  (378 × 375, 3 satırlık hiyerarşik başlık)
              │
              ▼
   ┌────────────────────────┐
   │  src/analysis/load.py  │   wide → tidy unpivot
   │                        │   (Pazar, Şirket, Ürün, Tarih, Brüt Kutu, MF Oran, Net TL)
   └───────────┬────────────┘
               ▼
   ┌────────────────────────┐   V2  MF ölçek düzeltmesi (B Pazarı ÷100)  ⚠️ kritik
   │  src/analysis/clean.py │   V3  MF kırpma [0, 0.95] + bayrak
   │                        │   V4  negatif değer bayrağı
   │                        │   V5  ilk satış öncesi kırpma
   │                        │   V7  ürün adı normalizasyonu
   └───────────┬────────────┘
               ▼
   ┌────────────────────────┐   Net Kutu, Birim Fiyat (V8 guard)
   │ src/analysis/metrics.py│   pazar payı, YoY, mevsimsellik indeksi, HHI
   └───────────┬────────────┘
               ├────────────────────────────┐
               ▼                            ▼
   ┌────────────────────────┐   ┌──────────────────────────┐
   │src/analysis/forecast.py│   │  src/analysis/plots.py   │
   │ naive / snaive / MA    │   │ ortak stil, TR etiketler │
   │ global LightGBM        │   └──────────────────────────┘
   │ walk-forward CV        │
   └───────────┬────────────┘
               ▼
   ┌──────────────────────────────────────────────────────┐
   │  notebooks/analiz.ipynb  — 7 görev, grafik + yorum   │
   └──────────────────────────────────────────────────────┘
```

**Neden modül + ince notebook:** ADR-009. Temizleme mantığı ~200 satır ve 7 görevin
hepsinde kullanılıyor; notebook hücresine gömülü olsa test edilemez ve kopyalanır.

---

## 2. Yükleme — `src/analysis/load.py`

```python
def load_raw(path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=0, header=None)
    # satır 1 = Yıl, satır 2 = Ay (TR ad), satır 3 = Metrik, satır 4+ = veri
    years   = raw.iloc[1, 3:].ffill().astype(int)
    months  = raw.iloc[2, 3:].ffill()
    metrics = raw.iloc[3, 3:]
    keys    = raw.iloc[4:, :3]           # Pazar, Şirket, Ürün
    ...
```

- **Ay adı eşlemesi:** `{'Ocak':1, 'Şubat':2, 'Mart':3, 'Nisan':4, 'Mayıs':5, 'Haziran':6,
  'Temmuz':7, 'Ağustos':8, 'Eylül':9, 'Ekim':10, 'Kasım':11, 'Aralık':12}` — 12 ayın
  tamamı veride doğrulandı.
- Çıktı tidy şeması:

| Kolon | Tip | Not |
|---|---|---|
| `pazar` | category | A/B/C/D Pazarı |
| `sirket` | category | Şirket 1 / Şirket 2 / Diğer Şirket |
| `urun` | str | normalize edilmiş |
| `tarih` | datetime64 | ayın 1'i |
| `brut_kutu` | float | |
| `mf_oran` | float | ham (temizlenmemiş) |
| `net_tl` | float | |

- **Doğrulama (assert):** `len(years) == len(months) == len(metrics) == 372`;
  `tarih.nunique() == 124`; `keys` yinelenmez; metrik adları tam olarak
  `{'Brüt Kutu', 'MF Oran', 'Net TL'}`.
- Tamamen boş hücreler `NaN` kalır (0'a çevrilmez — V5).

---

## 3. Temizleme — `src/analysis/clean.py`

Her adım hem veriyi değiştirir hem de bir **bayrak kolonu** ekler; notebook'un veri
kalitesi raporu bu bayrakları sayar.

### 3.1 Ürün adı normalizasyonu (V7)
```python
df["urun"] = df["urun"].str.replace(r"\s+", " ", regex=True).str.strip()
```
Doğrulandı: normalizasyon sonrası `(pazar, sirket, urun)` çakışması **yok**.

### 3.2 ⚠️ MF ölçek düzeltmesi (V2) — en kritik adım

**Sabit "B Pazarı" kuralı yazılmaz; program tespiti yapılır:**

```python
def detect_mf_scale(df) -> dict[str, float]:
    """Pazar bazında MF birimini tespit eder. Medyan > 1 ise yüzde ölçeği kabul edilir."""
    out = {}
    for pazar, g in df.groupby("pazar"):
        med = g.loc[g.mf_oran.notna() & (g.mf_oran > 0), "mf_oran"].median()
        out[pazar] = 100.0 if med > 1 else 1.0
    return out
```

Ölçülen medyanlar (bulgular §2.3): A ≈ 0,00 · **B ≈ 5,9–7,4** · C ≈ 0,05–0,12 · D ≈ 0,12–0,17
→ yalnızca B Pazarı 100'e bölünür.

**Doğrulama testi (zorunlu):** düzeltme sonrası B Pazarı / Şirket 1 / Ürün-FR için
birim fiyat **pozitif** ve 2016'da 8–9 TL, 2026'da 130–150 TL bandında olmalı
(A Pazarı / Ürün-A ile aynı büyüklük mertebesi: 10,28 → 157,20 TL).

**Bu adım atlanırsa:** Net Kutu negatife düşer → birim fiyat negatif → A4, A6, A7 çöker.

### 3.3 MF kırpma (V3)
```python
df["mf_clipped"] = (df.mf_oran_scaled < 0) | (df.mf_oran_scaled > 0.95)
df["mf_oran_clean"] = df.mf_oran_scaled.clip(0, 0.95)
```
Ölçek düzeltmesinden sonra bile kalan aşırı değerler: Diğer Şirket'te max 469,5 (B),
246,0 (C), 15,0 (A). Bunlar veri hatası; kırpılıp bayraklanır ve rapor edilir.

### 3.4 Negatif değer bayrağı (V4)
```python
df["is_return"] = (df.brut_kutu < 0) | (df.net_tl < 0)
```
1.158 / 1.168 gözlem. Toplamlarda korunur (net hacim doğru kalsın), tahmin girdisinde 0'lanır.

### 3.5 Seri kırpma (V5)
```python
ilk_satis = df[df.brut_kutu > 0].groupby(KEY).tarih.min()
df = df[df.tarih >= df[KEY].map(ilk_satis)]
```
`KEY = ["pazar", "sirket", "urun"]` (V6). İlk satıştan sonraki sıfırlar **gerçek sıfır**
kabul edilir; öncesi ürünün var olmadığı dönem.

### 3.6 Veri kalitesi raporu
Temizleme sonunda döndürülen özet:

| Metrik | Değer |
|---|---|
| Toplam gözlem (ham / temiz) | … |
| MF ölçek düzeltmesi uygulanan pazar | B Pazarı (÷100) |
| MF kırpılan gözlem sayısı | … |
| İade (negatif) gözlem sayısı | 1.158 |
| İlk satış öncesi kırpılan gözlem | … |
| Analiz dışı bırakılan kısa seri | `C/Ürün 1` (1 ay) |

---

## 4. Türetilmiş Metrikler — `src/analysis/metrics.py`

```python
net_kutu    = brut_kutu * (1 - mf_oran_clean)
birim_fiyat = np.where(net_kutu > 0, net_tl / net_kutu, np.nan)   # V8
```

| Fonksiyon | Tanım | Kullanan görev |
|---|---|---|
| `market_share(df, metric="brut_kutu")` | Pazar-ay bazında şirket payı % | A2 |
| `hhi(df)` | Σ payᵢ² (0–10.000) — rekabet yoğunluğu | A2, A5 |
| `yoy_growth(df, freq="Y")` | Yıllık büyüme % | A5 |
| `seasonal_index(series)` | STL/klasik ayrıştırma, ay bazında ortalama mevsimsel çarpan | A3 |
| `seasonality_strength(series)` | `max(0, 1 − Var(kalan) / Var(kalan + mevsimsel))` (Hyndman) | A3 |
| `promo_revenue_loss(df)` | `mf_oran × brut_kutu × birim_fiyat` (yıllık toplam TL) | A6 |
| `price_dispersion(df)` | Aynı ürünün pazarlar arası fiyat varyasyon katsayısı | A6 |

**Mevsimsellik yöntemi:** `statsmodels.tsa.seasonal.STL(period=12, robust=True)`.
Klasik `seasonal_decompose`'a tercih sebebi: aykırı değerlere dayanıklı (veride
promosyon kaynaklı sıçramalar var). Seri < 24 ay ise hesaplanmaz (V9), `NaN` döner ve
raporda "yetersiz veri" olarak listelenir.

---

## 5. Görev Bazlı Metodoloji

### A1 — Satış performansı ve ürün kırılımı
- Filtre: Şirket 1, `tarih >= 2024-05-01` (V1).
- Grafik 1: 2×2 subplot (4 pazar), ikili eksen — Brüt Kutu (bar) + Net TL (çizgi).
- Grafik 2: Pazar başına ürün katkısı (yığılmış alan) + Pareto tablosu
  (ilk N ürün hacmin/cironun %X'ini oluşturuyor).
- Zirve/dip: ay bazında ortalamanın toplam ortalamaya oranı; 4 pazarın zirve ayları
  yan yana tabloda karşılaştırılır.

### A2 — Pazar yapısı ve rekabet pozisyonu
- Pay = `brut_kutu` toplamı üzerinden, pazar-ay bazında %.
- Grafik: 4 pazar için yığılmış alan grafiği (2016→2026), 3 şirket.
- Ek metrik: HHI zaman serisi (yoğunlaşma artıyor mu?).
- "Orantısız pay": pazar toplam büyümesi vs. Şirket 1 büyümesi (CAGR farkı) tablosu.

### A3 — Mevsimsellik
- Şirket 1'in 18 serisi; V9 filtresi sonrası uygun olanlar.
- Grafik: ürün × ay ısı haritası (mevsimsel indeks), pazar başına panel.
- Tutarlılık: aynı ürün adı birden fazla pazarda yoksa (Şirket 1'de yok — A/B/C/D
  ürün setleri ayrık), analiz **pazar seviyesinde toplulaştırılmış** mevsimsellik
  karşılaştırmasına dönüşür. Bu, notebook'ta açıkça belirtilecek — case'in
  "aynı ürünün farklı pazarlardaki örüntüsü" sorusunun veri gerçeğiyle sınırı.

### A4 — MF'in satışa etkisi (olay çalışması)
```
olay      : mf_oran_clean > 0.10 olan (seri, ay) çiftleri
sonuç     : Δ = brut_kutu[t+1] / brut_kutu[t] − 1
kontrol   : aynı serinin mf ≤ 0.10 olan aylarındaki aynı büyüklük
testler   : Mann-Whitney U (dağılım varsayımsız) + Welch t-testi
etki boyu : Cliff's delta veya Cohen's d
düzeltme  : çoklu karşılaştırma → Benjamini-Hochberg FDR
```
- Mevsimselliği kontrol etmek için alternatif sonuç metriği: aynı ayın mevsimsel
  indeksine göre düzeltilmiş `Δ`.
- Grafik: pazar bazında olay/kontrol dağılım kutu grafiği + p-değeri anotasyonu.
- Çıktı tablosu: pazar × ürün, olay sayısı, ortalama Δ, p, FDR-q, anlamlı mı.

### A5 — Rakip karşılaştırması
- Yıllık toplam Brüt Kutu → YoY %, Şirket 1 vs Şirket 2, pazar bazında.
- Rekabet yoğunluğu: HHI + ilk-2 firma payı + Şirket 1/Şirket 2 pay farkının volatilitesi.
- "Diğer Şirket hacim kaybı" kanıtı: (a) mutlak hacim trendi (regresyon eğimi + p),
  (b) pay trendi, (c) kaybedilen payın kime gittiği — Şirket 1 ve 2'nin pay kazancıyla
  eşleştirme (pay değişimlerinin toplamı sıfır olmalı, bu bir tutarlılık kontrolü).

### A6 — Birim fiyat ve promosyon maliyeti
- Ürün × pazar aylık birim fiyat serisi; yıllık ortalama + CAGR.
- Enflasyon bağlamı: nominal fiyat trendi verilir; reel karşılaştırma için TÜFE verisi
  veri setinde yok → notebook'ta sınırlılık olarak belirtilir.
- Promosyon maliyeti: `bedava_kutu = brut_kutu × mf_oran_clean`,
  `gelir_kaybi_TL = bedava_kutu × birim_fiyat`, yıllık ve ürün-pazar bazında toplam.
- Maliyet-fayda: yüksek MF dönemlerindeki hacim artışı × birim fiyat vs. gelir kaybı
  karşılaştırma tablosu (basit ROI oranı).

### A7 — Tahmin
**Hedef:** Şirket 1'in her ürün-pazar serisi için t+1 ayı `brut_kutu`.

**Değerlendirme:** walk-forward (expanding window), son **12 ay**, her adımda 1 ay ileri.
Tek train/test bölmesi zaman serisinde yanıltıcıdır.

**Modeller:**

| Model | Tanım |
|---|---|
| `naive` | ŷ(t+1) = y(t) |
| `snaive` | ŷ(t+1) = y(t−11) |
| `ma3` | ŷ(t+1) = son 3 ayın ortalaması |
| `lgbm` | Global LightGBM (tüm seriler tek modelde) |
| `lgbm_no_mf` | Aynı model, MF özellikleri çıkarılmış → **ablasyon** |

**LightGBM özellikleri:**
```
lag_1, lag_2, lag_3, lag_12
roll_mean_3, roll_mean_6, roll_std_3
ay (1-12), çeyrek, yıl_indeksi (trend)
pazar (kategorik), urun (kategorik)
mf_lag_0, mf_lag_1, mf_roll_mean_3          ← ablasyonda çıkarılan set
seri_uzunlugu
```
Hedef dönüşümü: `log1p(brut_kutu)` (negatifler V4 ile 0'lanmış olduğu için güvenli),
tahmin `expm1` ile geri çevrilir. Gerekçe: hacimler pazar/ürün arası 3 mertebe farklı;
log ölçek global modelde büyük serilerin kaybı domine etmesini engeller.

**Metrikler (pazar bazında + genel):**
```
MAE   = mean(|y − ŷ|)
RMSE  = sqrt(mean((y − ŷ)²))
MAPE  = mean(|y − ŷ| / y),  y > 0 olan gözlemlerde     ← case istiyor
WAPE  = Σ|y − ŷ| / Σy                                  ← sıfır-dayanıklı
sMAPE = mean(2|y − ŷ| / (|y| + |ŷ|))
```

**Çıktı tabloları:**
1. Model × Pazar → MAE, MAPE, RMSE, WAPE (case'in istediği tablo)
2. `lgbm` vs `lgbm_no_mf` → MF katkısının pazar bazında delta'sı
3. Mevsimsellik gücü yüksek/düşük seriler ayrımında model sıralaması
   → "aynı mimari her pazarda geçerli mi?" sorusunun doğrudan cevabı

**Kısa seri politikası:** < 24 ay olan seriler (`C/Ürün 1`, `D/Ürün 78`, `B/Ürün-FP`)
LightGBM'in eğitim havuzunda kalır (global model onlardan da öğrenir) ama
per-seri metrik tablosunda "yetersiz geçmiş" etiketiyle ayrı gösterilir.

---

## 6. Görselleştirme Standardı — `src/analysis/plots.py`

- Kütüphane: **matplotlib** (statik, notebook'ta güvenilir render) + seçili yerlerde
  `plotly` (etkileşimli zaman serisi). Power BI kapsam dışı (PRD §3.3).
- Tüm başlık, eksen ve lejant **Türkçe**.
- Sayı biçimi: binlik ayracı nokta, ondalık virgül (`1.234,5`); TL değerlerinde `₺` yok,
  kolon başlığında `(TL)`.
- Tutarlı pazar renkleri: A/B/C/D için sabit palet; şirketler için sabit palet
  (Şirket 1 vurgulu, Şirket 2 ve Diğer nötr).
- Her grafiğin altında tek cümlelik "ne gösteriyor" notu.
- Figürler `figures/` altına PNG olarak da kaydedilir (README/sunum için).

---

## 7. Bağımlılıklar (`requirements-analysis.txt`)

| Paket | Amaç |
|---|---|
| `pandas`, `numpy` | Veri işleme |
| `openpyxl` | XLSX okuma |
| `matplotlib` | Statik grafikler |
| `plotly` | Etkileşimli zaman serisi (opsiyonel görseller) |
| `statsmodels` | STL ayrıştırma, istatistiksel testler |
| `scipy` | Mann-Whitney, t-testi, etki büyüklüğü |
| `scikit-learn` | Metrikler, yardımcı araçlar |
| `lightgbm` | Global tahmin modeli |
| `jupyter` | Notebook |

---

## 8. Test Stratejisi — `tests/test_analysis.py`

| Test | Doğruladığı |
|---|---|
| `test_load_shape` | 124 ay, 374 seri, 3 metrik; yinelenen anahtar yok |
| `test_mf_scale_detection` | Yalnızca B Pazarı için faktör 100 dönüyor ⚠️ **en kritik test** |
| `test_birim_fiyat_pozitif` | Düzeltme sonrası B/Ürün-FR birim fiyatı pozitif ve 8–150 TL bandında |
| `test_urun_ad_normalizasyonu` | `Ürün 1` / `Ürün  2` normalize; çakışma yok |
| `test_net_kutu_guard` | MF = 1 → Birim Fiyat `NaN`, `inf` değil |
| `test_seri_kirpma` | İlk satış öncesi satırlar düşmüş; sonraki sıfırlar korunmuş |
| `test_metrics_market_share` | Pazar payları her ay %100'e toplanıyor |
