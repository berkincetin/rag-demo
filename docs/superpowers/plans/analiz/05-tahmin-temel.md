# Task 5: Temel tahmin modelleri ve walk-forward değerlendirme

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: TRD §5 (A7).
> **Önceki:** [Task 4](04-grafikler.md) · **Sonraki:** [Task 6](06-tahmin-lgbm.md)

**Dosyalar:** `src/analysis/forecast.py` · **Test:** `tests/test_analysis_forecast.py`

## Interfaces

```python
TEST_AYLARI = 12          # walk-forward penceresi

def naive(gecmis: pd.Series) -> float          # y(t)
def snaive(gecmis: pd.Series) -> float         # y(t-11)
def ma3(gecmis: pd.Series) -> float            # son 3 ayın ortalaması
def walk_forward(df, tahminci, ay_sayisi=TEST_AYLARI) -> pd.DataFrame
    # → pazar, sirket, urun, tarih, gercek, tahmin
def hata_metrikleri(gercek, tahmin) -> dict    # mae, rmse, mape, wape, smape
def pazar_bazinda_metrikler(sonuc: pd.DataFrame) -> pd.DataFrame
```

---

- [ ] **Adım 1: Kırmızı testler**

| Test | Doğruladığı |
|---|---|
| `test_naive_son_gozlemi_donduruyor` | Tanım |
| `test_snaive_on_iki_ay_oncesini_donduruyor` | Tanım; 12 aydan kısa geçmişte `naive`'e düşüyor |
| `test_ma3_son_uc_ayin_ortalamasi` | Tanım |
| `test_walk_forward_gelecegi_sizdirmiyor` | 🚨 Her katmanda eğitim penceresi yalnız `t`'ye kadar — kurgu seride ispat |
| `test_walk_forward_kisa_seriyi_atliyor` | 1 gözlemli seri (`C/Ürün 1`) hata fırlatmıyor, sonuç setinde yok |
| `test_mape_sifir_gercek_degerde_patlamiyor` | 🚨 `y=0` gözlemler MAPE'den dışlanıyor, `inf` yok (V10) |
| `test_wape_sifir_dayanikli` | Aynı veride WAPE sonlu |
| `test_hata_metrikleri_bilinen_degerlerle` | Elle hesaplanmış küçük vektör |
| `test_pazar_bazinda_metrikler_her_pazari_ayri_veriyor` | 🚨 A Pazarı diğerlerini maskelemiyor (bulgular §2.5) |

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: `forecast.py` yaz.** Walk-forward genişleyen pencere, son 12 ay, her
      adımda 1 ay ileri. Tek train/test bölmesi zaman serisinde yanıltıcıdır — TRD §5.
      Tahmin girdisinde negatifler 0'lanır (V4); toplam raporlarında **0'lanmaz**.

- [ ] **Adım 4: Yeşili doğrula**

- [ ] **Adım 5: Kalite kapısı ve commit** — `feat(forecast): add baselines and walk-forward evaluation`

## Definition of Done
- [ ] 9 test yeşil
- [ ] 🚨 Veri sızıntısı testi geçiyor
- [ ] MAPE `inf` üretmiyor; WAPE ve sMAPE yanında raporlanıyor
- [ ] Kısa seriler kodu kırmıyor, sonuçtan **sessizce düşmüyor** — ayrı listeleniyor
