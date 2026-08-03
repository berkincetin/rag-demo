# Task 3: Türetilmiş ve analitik metrikler

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: TRD §4.
> **Önceki:** [Task 2](02-temizleme.md) · **Sonraki:** [Task 4](04-grafikler.md)

**Dosyalar:** `src/analysis/metrics.py` · **Test:** `tests/test_analysis_metrics.py`

## Interfaces

```python
def turetilmis_metrikler(df) -> pd.DataFrame      # net_kutu, birim_fiyat ekler
def pazar_payi(df, metrik="brut_kutu") -> pd.DataFrame   # pazar-ay-şirket %
def hhi(df) -> pd.DataFrame                        # pazar-ay → 0–10.000
def yillik_buyume(df) -> pd.DataFrame              # pazar-şirket-yıl → %
def mevsimsel_indeks(seri: pd.Series) -> pd.Series | None   # ay → çarpan, <24 ay ise None
def mevsimsellik_gucu(seri: pd.Series) -> float | None      # Hyndman, 0–1
def promosyon_gelir_kaybi(df) -> pd.DataFrame      # yıl-pazar-ürün → TL
def fiyat_sapmasi(df) -> pd.DataFrame              # ürün → pazarlar arası CV
```

---

- [ ] **Adım 1: Kırmızı testler**

| Test | Doğruladığı |
|---|---|
| `test_net_kutu_formulu` | `brut × (1 − mf)` — case tanımı |
| `test_mf_bir_oldugunda_birim_fiyat_nan` | 🚨 `inf` **değil** `NaN` (V8) — sıfıra bölme koruması |
| `test_negatif_net_kutu_birim_fiyati_nan_yapar` | V8'in ikinci yarısı |
| `test_pazar_paylari_her_ay_yuze_toplaniyor` | Sentetik veride her ay toplam 100 (±1e-9) |
| `test_hhi_tek_oyunculu_pazarda_on_bin` | Sınır durumu |
| `test_yillik_buyume_bilinen_seride_dogru` | %50 büyüme kurgulanır |
| `test_mevsimsel_indeks_kisa_seride_none_doner` | 🚨 12 aylık seri → `None` (V9); `C/Ürün 1` kodu kırmasın |
| `test_mevsimsel_indeks_bilinen_sinus_deseni_yakalar` | Kurgu 12 aylık desen → tepe ay doğru |
| `test_mevsimsellik_gucu_duz_seride_sifira_yakin` | Sabit seri → ~0 |
| `test_promosyon_gelir_kaybi_bilinen_degeri_uretir` | `bedava_kutu × birim_fiyat` elle hesapla |

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: `metrics.py` yaz.** Mevsimsellik `statsmodels.tsa.seasonal.STL(period=12,
      robust=True)`. `robust=True` gerekçesi: veride promosyon kaynaklı sıçramalar var,
      klasik ayrıştırma onlara aşırı tepki verir. `< 24 ay` ise hesaplama **yapılmaz**,
      `None` döner (V9) — kısa seri sessizce uydurulmuş mevsimsellik üretmesin.

- [ ] **Adım 4: Yeşili doğrula**

- [ ] **Adım 5: Kalite kapısı ve commit** — `feat(metrics): add derived and analytical sales measures`

## Definition of Done
- [ ] 10 test yeşil
- [ ] `birim_fiyat` hiçbir durumda `inf` üretmiyor
- [ ] `mevsimsel_indeks` 24 aydan kısa seride `None` dönüyor, hata fırlatmıyor
- [ ] Pazar payları her ay %100'e toplanıyor
