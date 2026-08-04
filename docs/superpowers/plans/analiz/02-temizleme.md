# Task 2: 🚨 Temizleme boru hattı ve veri kalitesi raporu

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: TRD §3, PRD §5 (V2–V8).
> **Önceki:** [Task 1](01-iskelet-yukleme.md) · **Sonraki:** [Task 3](03-metrikler.md)

**Bu projenin en kritik task'ı.** MF ölçek düzeltmesi atlanırsa A4, A6 ve A7 **tamamen
yanlış** sonuç verir — negatif net kutu, negatif birim fiyat, anlamsız promosyon maliyeti.

**Dosyalar:** `src/analysis/clean.py` · **Test:** `tests/test_analysis_clean.py`

## Interfaces

```python
@dataclass
class DataQualityReport:
    raw_rows: int
    clean_rows: int
    rescaled_markets: dict[str, float]   # {'B Pazarı': 100.0}
    mf_clipped: int
    return_rows: int
    pre_launch_dropped: int
    short_series: dict[tuple[str, str, str], int]  # anahtar → dolu ay sayısı

def detect_mf_scale(df) -> dict[str, float]:      # pazar → 1.0 veya 100.0
def clean(df) -> tuple[pd.DataFrame, DataQualityReport]
```

Temiz çerçevenin eklediği kolonlar: `mf_oran_olcekli`, `mf_oran_temiz`, `mf_kirpildi`,
`iade_mi`.

---

- [ ] **Adım 1: Kırmızı testler** (sıra önemli — ilk üçü ölçek düzeltmesini korur)

| Test | Doğruladığı |
|---|---|
| `test_only_market_b_is_detected_as_percent_scaled` | 🚨 `{'B Pazarı': 100.0}`, diğer üçü `1.0` — bulgular §2.3 medyanları |
| `test_olcek_tespiti_sabit_pazar_adi_kullanmiyor` | Uydurma bir pazarın medyanı > 1 yapıldığında da 100 dönüyor (kural veriden, addan değil) |
| `test_duzeltme_sonrasi_b_pazari_birim_fiyati_pozitif` | B/Şirket 1/Ürün-FR 2016-01 → ~8,32 TL (±0,05); düzeltmesiz −0,88 TL |
| `test_urun_adlari_normalize_ediliyor` | `Ürün  2` → `Ürün 2`; normalizasyon sonrası anahtar çakışması yok (V7) |
| `test_mf_kirpma_ust_siniri_uyguluyor` | Ölçek sonrası kalan 469,5 gibi değerler 0,95'e kırpılıyor, `mf_kirpildi` bayraklı (V3) |
| `test_iadeler_silinmiyor_bayraklaniyor` | Negatif satırlar çerçevede duruyor, `iade_mi == True` (V4) |
| `test_ilk_satistan_onceki_aylar_atiliyor` | Sentetik series: ilk pozitiften önceki satırlar yok, sonraki sıfırlar duruyor (V5) |
| `test_rapor_kisa_serileri_listeliyor` | `('C Pazarı', 'Şirket 1', 'Ürün 1')` → 1 ay (bulgular §2.5) |
| `test_rapor_sayilari_gercek_veriyle_tutarli` | `iade_gozlem` ≈ 1.158 (entegrasyon) |

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: `clean.py` yaz** — sıra: V7 ad normalizasyonu → V2 ölçek → V3 kırpma →
      V4 iade bayrağı → V5 seri kırpma → rapor. Her adım hem veriyi değiştirir hem sayar.

⚠️ `detect_mf_scale` yalnız `mf_oran > 0` olan gözlemlerin medyanına bakar; sıfırlar
medyanı aşağı çekip B'yi de "oran" gibi gösterirdi.

- [ ] **Adım 4: Yeşili doğrula**

- [ ] **Adım 5: Kalite kapısı ve commit** — `fix(clean): detect and correct the percent-scaled MF ratio`

## Definition of Done
- [ ] 9 test yeşil
- [ ] 🚨 Ölçek tespiti **sabit pazar adı kullanmıyor** — test bunu kanıtlıyor
- [ ] B/Ürün-FR birim fiyatı düzeltme sonrası pozitif ve 8–150 TL bandında
- [ ] Rapor: kaç gözlem kırpıldı, kaç iade, kaç seri kısa — hepsi sayıyla
- [ ] Kısa seriler **silinmemiş**, raporda listelenmiş
