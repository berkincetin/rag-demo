# Task 1: İskelet, bağımlılıklar, geniş → tidy yükleme

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: TRD §2.
> **Sonraki:** [Task 2](02-temizleme.md)

**Dosyalar:** `src/analysis/__init__.py`, `src/analysis/load.py`, `requirements-analysis.txt`
**Test:** `tests/test_analysis_load.py`

## Interfaces (sonraki task'lar bunlara dayanır)

```python
VERI_YOLU = Path("AI Engineer/bolum2_veriseti.xlsx")
ANAHTAR = ["pazar", "sirket", "urun"]
AY_ADLARI: dict[str, int]                     # 'Ocak' → 1 … 'Aralık' → 12

def yukle_ham(yol: Path = VERI_YOLU) -> pd.DataFrame:
    """Geniş formatlı sayfayı tidy çerçeveye çevirir.
    Kolonlar: pazar, sirket, urun, tarih, brut_kutu, mf_oran, net_tl."""
```

---

- [ ] **Adım 1: Kırmızı testler**

```python
# tests/test_analysis_load.py
import pandas as pd
import pytest

from src.analysis.load import AY_ADLARI, VERI_YOLU, yukle_ham


@pytest.fixture(scope="module")
def ham() -> pd.DataFrame:
    if not VERI_YOLU.exists():
        pytest.skip(f"veri seti yok: {VERI_YOLU}")
    return yukle_ham()


def test_ay_adlari_on_ikisi_de_var():
    # Ay adları veride doğrulandı (bulgular §2.1); eksik ad sessiz NaT üretir.
    assert len(AY_ADLARI) == 12
    assert AY_ADLARI["Ocak"] == 1
    assert AY_ADLARI["Aralık"] == 12


@pytest.mark.integration
def test_tidy_cerceve_beklenen_kolonlari_tasiyor(ham):
    assert list(ham.columns) == [
        "pazar", "sirket", "urun", "tarih", "brut_kutu", "mf_oran", "net_tl"
    ]


@pytest.mark.integration
def test_seri_ve_ay_sayisi_olculen_degerlerle_ayni(ham):
    # Bulgular §2.1: 374 seri × 124 ay.
    assert ham["tarih"].nunique() == 124
    assert len(ham.groupby(["pazar", "sirket", "urun"], observed=True)) == 374


@pytest.mark.integration
def test_tarih_araligi_2016_01_ile_2026_04_arasi(ham):
    assert ham["tarih"].min() == pd.Timestamp("2016-01-01")
    assert ham["tarih"].max() == pd.Timestamp("2026-04-01")


@pytest.mark.integration
def test_anahtar_ay_ciftleri_yinelenmiyor(ham):
    assert not ham.duplicated(["pazar", "sirket", "urun", "tarih"]).any()


@pytest.mark.integration
def test_bos_hucreler_sifira_cevrilmemis(ham):
    # Bulgular §2.4: 28.006 boş hücre ürün yaşam döngüsü, gerçek sıfır değil (V5).
    assert ham["brut_kutu"].isna().sum() > 0


@pytest.mark.integration
def test_sirket_1_on_sekiz_seriye_sahip(ham):
    s1 = ham[ham["sirket"] == "Şirket 1"]
    assert len(s1.groupby(["pazar", "urun"], observed=True)) == 18
```

- [ ] **Adım 2: Kırmızıyı doğrula** — `ModuleNotFoundError: src.analysis.load` beklenir

- [ ] **Adım 3: `src/analysis/load.py` yaz**

`pd.read_excel(..., header=None)` ile ham oku. Satır indeksleri (0-tabanlı):
`1 = Yıl`, `2 = Ay`, `3 = Metrik`, `4+` = veri; kolon `0..2` = anahtar, `3+` = 372 ölçüm.
Yıl ve ay satırları birleştirilmiş hücreler yüzünden seyrek → `ffill()`.
Metrik adları tam olarak `{'Brüt Kutu', 'MF Oran', 'Net TL'}` olmalı — değilse `ValueError`.
Uzun formata çevir, metrikleri pivotla, kolon adlarını Türkçe snake_case'e eşle.

⚠️ **Ürün adı normalizasyonu burada YAPILMAZ** — o Task 2'nin işi (V7). Bu modül ham veriyi
sadakatle okur; düzeltmeler tek yerde toplanır.

- [ ] **Adım 4: Yeşili doğrula** — 7 test

- [ ] **Adım 5: `requirements-analysis.txt`**

TRD §7 listesi, `plotly` **hariç** (overview'daki gerekçe). Sürümler `pip freeze`'den
birebir alınır — tahmin edilmez.

- [ ] **Adım 6: Kalite kapısı ve commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git commit -m "feat(load): add wide-to-tidy loader for the sales workbook"
```

## Definition of Done
- [ ] 7 test yeşil
- [ ] `yukle_ham()` gerçek veri setinde 374 seri × 124 ay döndürüyor
- [ ] Boş hücreler `NaN` kalmış, 0'a çevrilmemiş
- [ ] Metrik adı beklenenden farklıysa `ValueError` fırlatılıyor
- [ ] `requirements-analysis.txt` gerçek kurulu sürümlerle yazıldı
