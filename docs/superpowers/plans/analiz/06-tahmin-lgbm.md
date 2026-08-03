# Task 6: Global LightGBM ve MF ablasyonu

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: TRD §5.
> **Önceki:** [Task 5](05-tahmin-temel.md) · **Sonraki:** [Task 7](07-notebook-a1-a2.md)

**Dosyalar:** `src/analysis/forecast.py` (genişletme) · **Test:** `tests/test_analysis_forecast.py`

## Interfaces

```python
MF_OZELLIKLERI = ["mf_lag_0", "mf_lag_1", "mf_roll_mean_3"]

def ozellik_matrisi(df) -> pd.DataFrame        # lag/roll/takvim/kategorik + MF
def lgbm_walk_forward(df, mf_dahil=True, ay_sayisi=TEST_AYLARI) -> pd.DataFrame
def mf_ablasyonu(df) -> pd.DataFrame           # pazar → lgbm vs lgbm_no_mf delta
```

Özellikler (TRD §5): `lag_1, lag_2, lag_3, lag_12`, `roll_mean_3, roll_mean_6, roll_std_3`,
`ay, ceyrek, yil_indeksi`, `pazar` + `urun` (kategorik), `seri_uzunlugu`, ve MF seti.

---

- [ ] **Adım 1: Kırmızı testler**

| Test | Doğruladığı |
|---|---|
| `test_ozellik_matrisi_gecmisten_gelecege_bakmiyor` | 🚨 `lag_1` gerçekten bir önceki ay; kaydırma yönü kurgu seride ispatlanır |
| `test_ozellik_matrisi_seri_sinirini_asmiyor` | 🚨 Bir serinin `lag_1`'i başka serinin son ayı **değil** (V6 anahtar) |
| `test_mf_ablasyonunda_mf_kolonlari_yok` | `mf_dahil=False` → `MF_OZELLIKLERI` matriste geçmiyor |
| `test_log_donusumu_geri_cevriliyor` | `expm1(log1p(x)) == x` ve tahminler negatif değil |
| `test_lgbm_kisa_serileri_egitim_havuzunda_tutuyor` | Global model onlardan da öğreniyor; per-seri tabloda "yetersiz geçmiş" etiketi |

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: Yaz.** Hedef `log1p(brut_kutu)` — hacimler pazarlar arası 3 mertebe
      farklı, log ölçek büyük serilerin kaybı domine etmesini engeller. Tahmin `expm1`
      ile geri çevrilir ve `clip(lower=0)` uygulanır. `random_state` sabitlenir;
      `verbose=-1` ile LightGBM çıktısı susturulur (notebook temiz kalsın).

- [ ] **Adım 4: Yeşili doğrula.** Testler **küçük kurgu veriyle** koşar — gerçek veri
      üstündeki eğitim notebook'ta, testte değil (süre).

- [ ] **Adım 5: Kalite kapısı ve commit** — `feat(forecast): add global LightGBM with an MF ablation`

## Definition of Done
- [ ] 5 test yeşil
- [ ] 🚨 Sızıntı ve seri-sınırı testleri geçiyor
- [ ] Ablasyon iki modeli **aynı katmanlarda** karşılaştırıyor (aynı walk-forward bölmeleri)
- [ ] LightGBM çıktısı notebook'u kirletmiyor
