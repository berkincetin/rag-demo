# Bölüm 2 — İlaç Sektörü Satış ve Talep Analizi

Dört pazar (A, B, C, D) × 124 ay (2016-01 → 2026-04) satış verisi üzerinde yedi analiz
sorusu: A1–A7.

---

## Paket içeriği

| Dosya | Ne |
|---|---|
| `analiz_full.ipynb` | **Tüm analiz tek dosyada.** Çıktılar ve grafikler gömülü olarak kayıtlı |
| `bolum2_veriseti.xlsx` | Kaynak veri |
| `figures/` | Notebook'un ürettiği 10 grafik, PNG olarak |
| `requirements.txt` | Bağımlılıklar (notebook bunları kendi de kurar) |

---

## Çalıştırma

Notebook **kendi kendine yeterlidir** — hiçbir proje modülü import etmez, tüm
fonksiyonlar dosyanın içinde tanımlıdır.

```bash
jupyter lab analiz_full.ipynb     # sonra: Restart & Run All
```

İlk hücre gerekli kütüphaneleri `%pip install` ile kurar. Veri dosyası notebook'un
yanında olduğu sürece başka ayar gerekmez.

`Restart & Run All` yaklaşık **2 dakika** sürer (LightGBM walk-forward en uzun adım) ve
`figures/` klasörünü yeniden üretir.

---

## İstenen çıktılar nerede

| İstenen | Nerede |
|---|---|
| **Jupyter Notebook** — tüm analizler ve görseller | `analiz_full.ipynb` |
| **Görseller** — her soru için en az 1 grafik | 10 grafik; aşağıdaki tabloda soru eşlemesi |
| **Yorum** — her soru altında teknik + iş yorumu | Her bölümün sonunda "Teknik yorum" ve "İş yorumu" başlıkları |
| **Model karşılaştırması (A7)** — MAE, MAPE, RMSE pazar bazında | A7'deki `metric_table.pivot_table(...)` hücresi: 5 model × 4 pazar |

### Soru → grafik eşlemesi

| Soru | Grafik(ler) |
|---|---|
| **A1** — Son 2 yıl performansı | `a1_pazar_bazinda_satis.png`, `a1_urun_katkisi.png` |
| **A2** — Pazar payı ve rekabet | `a2_pazar_paylari.png`, `a2_hhi.png` |
| **A3** — Mevsimsellik | `a3_mevsimsellik_isi_haritasi.png` |
| **A4** — MF'in sonraki ay satışına etkisi | `a4_mf_etkisi.png` |
| **A5** — Rakip karşılaştırması | `a5_yillik_buyume.png` |
| **A6** — Fiyat ve promosyon maliyeti | `a6_birim_fiyat.png`, `a6_promosyon_maliyeti.png` |
| **A7** — Talep tahmini | `a7_gercek_vs_tahmin.png` |

---

## 🚨 En kritik teknik bulgu

`MF Oran` kolonu **B Pazarı'nda yüzde (0–100)**, diğer üç pazarda oran (0–1) ölçeğinde.
Düzeltilmezse `Net Kutu = Brüt Kutu × (1 − MF Oran)` negatife düşüyor:

| B Pazarı / Şirket 1 / Ürün-FR, 2016-01 | Değer |
|---|---|
| Ham `MF Oran` | 9,54 |
| Oran olarak okunursa birim fiyat | **−0,88 TL** ❌ |
| 100'e bölününce birim fiyat | **8,32 TL** ✔ |

Bu düzeltme olmadan **A4, A6 ve A7 görevlerinin tamamı yanlış** sonuç verir. Düzeltme
sabit "B Pazarı" kontrolüyle değil, **grup medyanı > 1 ⇒ yüzde ölçekli** program
tespitiyle yapılıyor; veri değişirse kırılmaz.

---

## Bilinen sınırlılıklar

Bunlar gizlenmedi, notebook içinde de raporlanıyor:

1. **Kısa seriler.** `C Pazarı/Ürün 1` yalnız **bir** ayında satış görmüş,
   `D Pazarı/Ürün 78` on bir ayında. Bu iki seri için mevsimsellik ve tahmin
   matematiksel olarak mümkün değil — uydurulmuyor, "yetersiz geçmiş" etiketiyle ayrı
   tabloda raporlanıyor. Global LightGBM'in eğitim havuzunda kalıyorlar.
2. **Ürün setleri pazarlar arası ayrık.** Şirket 1'in hiçbir ürünü birden fazla pazarda
   yok. "Aynı ürünün farklı pazarlardaki örüntüsü" sorusu bu veriyle ürün seviyesinde
   **cevaplanamıyor**; karşılaştırma pazar seviyesine taşındı.
3. **Fiyatlar nominal.** Veri setinde TÜFE yok, reel fiyat karşılaştırması yapılmadı.
4. **A4 korelasyondur, nedensellik değil.** Yüksek MF satışı düşürüyor olabileceği gibi,
   düşeceği bilinen aylarda MF artırılıyor da olabilir.
5. **MAPE tek başına kullanılamıyor.** Sıfıra yakın gerçek değerlerde patlıyor
   (D Pazarı'nda `snaive` için 4.257.901). Case istediği için tabloda duruyor, ama model
   seçimi sıfır-dayanıklı **WAPE** üzerinden yapılıyor.
