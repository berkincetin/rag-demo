# Task 9: A5 rakip karşılaştırması, A6 birim fiyat ve promosyon maliyeti

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: TRD §5 (A5, A6).
> **Önceki:** [Task 8](08-notebook-a3-a4.md) · **Sonraki:** [Task 10](10-notebook-a7.md)

**Dosyalar:** `notebooks/analiz.ipynb` (genişletme)

---

- [ ] **Adım 1: A5 — Şirket 1 vs Şirket 2**

- Yıllık toplam Brüt Kutu → YoY %, pazar bazında, iki şirket yan yana.
- Rekabet yoğunluğu: HHI + ilk-2 firma payı + pay farkının volatilitesi.
- 🚨 **"Diğer Şirket hacim kaybı" veriden kanıtlanır**, iddia edilmez:
  1. mutlak hacim trendi — doğrusal regresyon eğimi + p-değeri,
  2. pay trendi,
  3. kaybedilen payın kime gittiği: Şirket 1 ve 2'nin pay kazancıyla eşleştirme.
     **Tutarlılık kontrolü:** üç şirketin pay değişimi toplamı ≈ 0 olmalı; notebook bunu
     hesaplayıp gösterir.
- Kanıt zayıfsa "kanıt zayıf" yazılır.
- Yorumlar.

- [ ] **Adım 2: A6 — birim fiyat trendi ve promosyon maliyeti**

- Ürün × pazar aylık birim fiyat serisi; yıllık ortalama + CAGR.
- Aynı ürünün pazarlar arası fiyat sapması — `price_dispersion` (CV).
  ⚠️ A3'teki aynı gerçek geçerli: Şirket 1'in ürün setleri pazarlar arası ayrık, bu yüzden
  karşılaştırma **pazar seviyesinde ortalama fiyat** üzerinden yapılır ve bu belirtilir.
- Promosyon maliyeti: `bedava_kutu = brut_kutu × mf_oran_temiz`,
  `gelir_kaybi_TL = bedava_kutu × birim_fiyat`; yıllık ve ürün-pazar bazında toplam TL.
- Maliyet-fayda: yüksek MF dönemlerindeki hacim artışı × birim fiyat vs gelir kaybı
  (basit ROI oranı). A4'ün sonucuyla tutarlı okunur.
- 🚨 Sınırlılık yazılır: TÜFE verisi veri setinde **yok**, dolayısıyla fiyat trendi
  **nominal**; reel karşılaştırma yapılmıyor.
- Yorumlar.

- [ ] **Adım 3: Notebook'u baştan çalıştır**

- [ ] **Adım 4: Kalite kapısı ve commit** — `feat(notebook): add competitor growth and promotion cost analysis`

## Definition of Done
- [ ] A5'te Diğer Şirket kaybı üç ayrı kanıtla desteklenmiş, pay toplamı kontrolü yapılmış
- [ ] A6'da yıllık TL gelir kaybı tablosu var
- [ ] Nominal fiyat sınırlılığı yazılmış
- [ ] Her iki görevde teknik + iş yorumu
