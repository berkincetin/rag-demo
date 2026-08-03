# Task 8: A3 mevsimsellik, A4 MF etkisi (istatistiksel test)

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: TRD §5 (A3, A4).
> **Önceki:** [Task 7](07-notebook-a1-a2.md) · **Sonraki:** [Task 9](09-notebook-a5-a6.md)

**Dosyalar:** `notebooks/analiz.ipynb` (genişletme)

---

- [ ] **Adım 1: A3 — mevsimsellik**

- Şirket 1'in 18 serisi; V9 filtresi (≥24 ay) sonrası uygun olanlar.
- Grafik: ürün × ay ısı haritası (mevsimsel indeks), pazar başına panel.
- `mevsimsellik_gucu` ile "belirgin mevsimsel" vs "stabil" ayrımı, eşik yazılı.
- 🚨 **Veri gerçeğinin sınırı açıkça yazılır:** Şirket 1'in ürün setleri pazarlar arası
  **ayrık** (A'da Ürün-A…J, B'de FP…FS, C'de Ürün 1–2, D'de 77–78). Yani case'in "aynı
  ürünün farklı pazarlardaki örüntüsü" sorusu bu veriyle **ürün seviyesinde
  cevaplanamaz**; analiz pazar seviyesinde toplulaştırılmış mevsimsellik
  karşılaştırmasına dönüşür. Bu bir eksiklik değil, veri gerçeği — notebook'ta böyle denir.
- Yetersiz veri nedeniyle hesaplanamayan seriler tabloda "yetersiz veri" olarak listelenir.
- Stok/hedef çıkarımı: zirve aylardan önceki üretim/stok penceresi yorumu.
- Yorumlar.

- [ ] **Adım 2: A4 — MF'in bir sonraki ay satışına etkisi**

Olay çalışması (TRD §5):
```
olay      : mf_oran_temiz > 0.10 olan (seri, ay) çiftleri
sonuç     : Δ = brut_kutu[t+1] / brut_kutu[t] − 1
kontrol   : aynı serinin mf ≤ 0.10 olan aylarındaki aynı büyüklük
testler   : Mann-Whitney U (dağılım varsayımsız) + Welch t-testi
etki boyu : Cliff's delta
düzeltme  : Benjamini-Hochberg FDR (çoklu karşılaştırma)
```
- Grafik: pazar bazında olay/kontrol kutu grafiği + p-değeri anotasyonu.
- Tablo: pazar × ürün, olay sayısı, ortalama Δ, p, FDR-q, **anlamlı mı**.
- Mevsimsellik kontrolü: mevsimsel indekse göre düzeltilmiş Δ ile tekrar.
- 🚨 Sonuç anlamsız çıkarsa **anlamsız yazılır**. Negatif bulgu da bulgudur.
- Yorumlar.

- [ ] **Adım 3: Notebook'u baştan çalıştır**

- [ ] **Adım 4: Kalite kapısı ve commit** — `feat(notebook): add seasonality and MF effect analysis`

## Definition of Done
- [ ] A3 ısı haritası ve A4 kutu grafiği üretiliyor
- [ ] A4 tablosunda p-değeri, etki büyüklüğü ve FDR düzeltmesi var
- [ ] Ürün setlerinin pazarlar arası ayrık olduğu **açıkça** yazılmış
- [ ] Her iki görevde teknik + iş yorumu
