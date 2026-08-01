# PRD — Bölüm 2: İlaç Sektörü Satış & Talep Analizi

**Durum:** Plan · **Öncelik:** 2 (Bölüm 1 tamamlandıktan sonra) · **Zorunluluk:** Opsiyonel/Bonus

---

## 1. Problem ve Amaç

İlaç sektöründe dört bağımsız pazar (A, B, C, D) üzerinde 2016-01 → 2026-04 arası
124 aylık satış verisi mevcut. Şirket 1 (ana firma), Şirket 2 (doğrudan rakip) ve
Diğer Şirket (pazardaki diğer tüm rakipler) için aylık **Brüt Kutu**, **MF Oran**
(mal fazlası) ve **Net TL** metrikleri veriliyor.

**Amaç:** Case'in 7 analiz sorusunu Python ortamında yanıtlamak; tablo, grafik ve
istatistiksel bulgularla desteklemek; her sorunun altına **hem teknik hem iş açısından**
yorum yazmak.

---

## 2. Veri Sözleşmesi

| Kavram | Tanım |
|---|---|
| Şirket 1 | Analiz edilen ana firma |
| Şirket 2 | Doğrudan rakip firma |
| Diğer Şirket | Pazardaki diğer tüm rakip firmaların ürünleri |
| Brüt Kutu | Kanala fiilen dağıtılan toplam kutu adedi |
| MF Oran | O ay bedava verilen promosyon kutularının brüt satışa oranı |
| Net TL | Promosyon maliyeti düşüldükten sonra elde edilen gelir |

**Türetilmiş metrikler (case'ten):**
```
Net Kutu    = Brüt Kutu × (1 − MF Oran)
Birim Fiyat = Net TL / Net Kutu
```

**Kapsam:** 374 seri (Pazar × Şirket × Ürün), 124 ay. Şirket 1'in **18 ürün-pazar serisi**
var: A'da 10 (Ürün-A…J), B'de 4, C'de 2, D'de 2.

---

## 3. Kapsam

### 3.1 Kapsam İçi — 7 Analiz Görevi

| ID | Görev | Zorunlu Çıktı |
|---|---|---|
| **A1** | Son 2 yıl aylık Brüt Kutu + Net TL, dört pazar; ürün kırılımı; zirve/dip ayların pazar karşılaştırması | ≥1 grafik + ürün dominasyon tablosu |
| **A2** | Pazar payları (Brüt Kutu %) Şirket 1/2/Diğer, 2016→bugün değişimi; en güçlü/zayıf pazar; orantısız pay alınan pazarlar | ≥1 grafik + pay tablosu |
| **A3** | Ürün × pazar mevsimsellik indeksi; belirgin mevsimsellik vs. stabil; aynı ürünün pazarlar arası tutarlılığı; stok/hedef çıkarımı | ≥1 grafik (ısı haritası) + indeks tablosu |
| **A4** | Yüksek MF ürün-pazar kombinasyonları; MF > %10 → t+1 satış etkisi; pazarlar arası fark; **istatistiksel anlamlılık** | ≥1 grafik + test sonuç tablosu (p-değeri, etki büyüklüğü) |
| **A5** | Şirket 1 vs Şirket 2 yıllık büyüme, pazar bazında; rekabet yoğunluğu; Diğer Şirket hacim kaybının **veriden kanıtlanması** | ≥1 grafik + büyüme tablosu |
| **A6** | Ürün × pazar birim fiyat trendi; aynı ürünün pazarlar arası fiyat sapması; yüksek MF'te yıllık gelir kaybı (TL); maliyet-fayda | ≥1 grafik + TL kayıp tablosu |
| **A7** | Bir sonraki ay Brüt Kutu tahmini, Şirket 1'in tüm ürünleri; **≥2 yaklaşım** (naive + ML); **pazar bazında** MAE/MAPE/RMSE; MF'in tahmin gücüne katkısı | Model karşılaştırma tablosu + tahmin grafiği |

### 3.2 Kapsam İçi — Altyapı

- **B1.** Wide → tidy dönüşümü (3 satırlık hiyerarşik başlık).
- **B2.** Veri temizleme boru hattı ([../01-veri-kesif-bulgulari.md](../01-veri-kesif-bulgulari.md) §2.3–2.5'teki 7 sorunun hepsi).
- **B3.** Temizleme kurallarının **birim testleri** — özellikle MF ölçek düzeltmesi.
- **B4.** Veri kalitesi raporu (notebook'un ilk bölümü): hangi kayıt kaç kez düzeltildi.

### 3.3 Kapsam Dışı

| Özellik | Neden |
|---|---|
| Power BI dashboard | Case "kullanılabilir" diyor, zorunlu değil. matplotlib/plotly ile aynı bilgi veriliyor |
| Şirket 2 ve Diğer Şirket için tahmin | Case A7'de yalnızca Şirket 1'in ürünlerini istiyor |
| SARIMA / Prophet | ADR-010 — 18 serinin çoğu kısa, per-series model yakınsamıyor; demo süresini uzatır |
| Hiperparametre optimizasyonu (Optuna vb.) | Demo kapsamı; makul varsayılanlar yeterli |
| Nedensellik modellemesi (causal inference) | A4 için istatistiksel test yeterli; case "istatistiksel olarak anlamlı" diyor, "nedensel etki" demiyor |
| Fiyat elastikiyeti modeli | Case sormuyor |
| İnteraktif web dashboard | Notebook teslim formatı |

---

## 4. Kabul Kriterleri

- [ ] Notebook `Restart & Run All` ile baştan sona hatasız çalışıyor
- [ ] **7 sorunun her biri** için en az 1 grafik
- [ ] **7 sorunun her biri** için hem teknik hem iş yorumu (ayrı başlıklar altında)
- [ ] A7'de **≥2 yaklaşım** ve **pazar bazında** MAE/MAPE/RMSE tablosu
- [ ] A7'de MF Oranı'nın tahmin gücüne katkısı **ablasyon ile** ölçülmüş
- [ ] A4'te p-değeri ve etki büyüklüğü içeren, anlamlı/anlamsız ayrımı yapan tablo
- [ ] **MF ölçek düzeltmesi** uygulanmış ve notebook'ta gerekçesi gösterilmiş
      (bu düzeltme olmadan A4/A6/A7 yanlış sonuç verir — bulgular §2.3)
- [ ] Veri kalitesi raporu notebook başında; kaç kayıt neden düzeltildi şeffaf
- [ ] Kısa seriler (`C/Ürün 1` = 1 ay, `D/Ürün 78` = 11 ay) gizlenmemiş, **açıkça raporlanmış**
- [ ] Tüm grafiklerde Türkçe eksen etiketi, başlık ve kaynak metrik adı
- [ ] `pip install -r requirements-analysis.txt` ile bağımlılıklar kuruluyor

---

## 5. Analitik Kararlar (varsayımlar)

Aşağıdaki kararlar veriden çıkarıldı; notebook'ta açıkça belirtilecek.

| # | Karar | Gerekçe |
|---|---|---|
| V1 | "Son 2 yıl" = **2024-05 … 2026-04** | Verinin son ayı 2026-04 (ölçüldü) |
| V2 | B Pazarı `MF Oran` değerleri **100'e bölünür** | Bulgular §2.3 — negatif birim fiyat üretiyor; yüzde ölçekli |
| V3 | Ölçek düzeltmesi sonrası MF `[0, 0.95]`'e kırpılır, kırpılanlar bayraklanır | Diğer Şirket'te max 469 gibi imkânsız değerler var |
| V4 | Negatif Brüt Kutu/Net TL **iade** kabul edilir; toplamlarda korunur, tahmin girdisinde 0'lanır | 1.158 / 1.168 gözlem; toplamdan silmek hacmi şişirir |
| V5 | Serinin **ilk pozitif satışından önceki** dönem analizden çıkarılır | 28.006 boş hücre; ürün yaşam döngüsü, gerçek sıfır değil |
| V6 | Birincil anahtar daima `(Pazar, Şirket, Ürün)` | `Ürün-A` ve `Ürün-FP` birden fazla şirkette geçiyor |
| V7 | Ürün adları `\s+ → ' '` ile normalize edilir | `Ürün 1` vs `Ürün  2` (çift boşluk) |
| V8 | Net Kutu ≤ 0 ise Birim Fiyat `NaN` | Sıfıra bölme ve negatif fiyat koruması |
| V9 | Mevsimsellik ve tahminde **≥24 ay** veri şartı | 12 aylık döngünün en az 2 tekrarı gerekli |
| V10 | MAPE'nin yanında **WAPE ve sMAPE** raporlanır | Sıfıra yakın gerçek değerlerde MAPE patlıyor; MAPE case istediği için yine de tabloda |

---

## 6. Riskler

| Risk | Etki | Azaltma |
|---|---|---|
| MF ölçek sorunu fark edilmezse A4/A6/A7 tamamen yanlış | **Kritik** | Bulgular §2.3'te tespit edildi; V2 + birim testi ile plana gömüldü |
| `C/Ürün 1` (1 ay) mevsimsellik/tahmin kodunu kırar | Yüksek | V9 filtresi + açık raporlama |
| MAPE sıfır bölmeleri sonsuz değer üretir | Orta | V10 + `y_true == 0` maskeleme |
| 18 serinin 10'u A Pazarı'nda → toplu metrik A'yı yansıtır | Orta | Metrikler **pazar bazında** raporlanır (case zaten istiyor) |
| Ürün adı çakışması yanlış birleştirme üretir | Yüksek | V6 birincil anahtar kuralı, testle doğrulanır |
| Notebook'un çalışması uzun sürer (ML eğitimi) | Düşük | Global model tek eğitim; walk-forward 12 katman; toplam < 2 dk |
