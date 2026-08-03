import numpy as np
import pandas as pd
import pytest

from src.analysis.forecast import (
    hata_metrikleri,
    ma3,
    naive,
    pazar_bazinda_metrikler,
    snaive,
    walk_forward,
)


def _seri(pazar="A Pazarı", urun="Ürün-A", aylar=36, baslangic=100.0, artis=1.0):
    tarih = pd.date_range("2020-01-01", periods=aylar, freq="MS")
    return pd.DataFrame(
        {
            "pazar": pazar,
            "sirket": "Şirket 1",
            "urun": urun,
            "tarih": tarih,
            "brut_kutu": [baslangic + artis * i for i in range(aylar)],
            "mf_oran_temiz": 0.1,
        }
    )


def test_naive_son_gozlemi_donduruyor():
    assert naive(pd.Series([5.0, 9.0, 12.0])) == pytest.approx(12.0)


def test_snaive_on_iki_ay_oncesini_donduruyor():
    gecmis = pd.Series(range(24), dtype=float)

    assert snaive(gecmis) == pytest.approx(12.0)


def test_snaive_kisa_gecmiste_naive_e_dusuyor():
    # 12 aydan kısa geçmişte mevsimsel referans yok; sessizce hata vermemeli.
    gecmis = pd.Series([3.0, 7.0])

    assert snaive(gecmis) == pytest.approx(7.0)


def test_ma3_son_uc_ayin_ortalamasi():
    assert ma3(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])) == pytest.approx(4.0)


def test_walk_forward_gelecegi_sizdirmiyor():
    # 🚨 Her katmanda tahminci yalnız t anına kadarki geçmişi görmeli.
    gorulen_son_tarihler = []

    def kaydeden_tahminci(gecmis: pd.Series) -> float:
        gorulen_son_tarihler.append(gecmis.index.max())
        return float(gecmis.iloc[-1])

    df = _seri(aylar=36)
    sonuc = walk_forward(df, kaydeden_tahminci, ay_sayisi=3)

    for gorulen, hedef in zip(gorulen_son_tarihler, sonuc["tarih"], strict=True):
        assert gorulen < hedef


def test_walk_forward_bir_ay_ileri_tahmin_ediyor():
    df = _seri(aylar=36)

    sonuc = walk_forward(df, naive, ay_sayisi=3)

    assert len(sonuc) == 3
    assert sonuc["tarih"].tolist() == df["tarih"].tolist()[-3:]
    # naive: t+1 tahmini t'nin değeri → gerçek her zaman 1 fazla (artis=1.0).
    assert (sonuc["gercek"] - sonuc["tahmin"]).round(6).eq(1.0).all()


def test_walk_forward_kisa_seriyi_atliyor():
    # `C/Ürün 1` gibi tek gözlemli seriler kodu kırmamalı.
    kisa = _seri(pazar="C Pazarı", urun="Ürün 1", aylar=1)
    uzun = _seri(aylar=36)

    sonuc = walk_forward(pd.concat([kisa, uzun]), naive, ay_sayisi=3)

    assert set(sonuc["urun"]) == {"Ürün-A"}


def test_mape_sifir_gercek_degerde_patlamiyor():
    # 🚨 V10: y = 0 gözlemler MAPE'den dışlanır, `inf` üretmez.
    metrikler = hata_metrikleri(np.array([0.0, 100.0]), np.array([5.0, 90.0]))

    assert np.isfinite(metrikler["mape"])
    assert metrikler["mape"] == pytest.approx(10.0)


def test_wape_sifir_dayanikli():
    metrikler = hata_metrikleri(np.array([0.0, 100.0]), np.array([5.0, 90.0]))

    # Σ|hata| = 5 + 10 = 15; Σy = 100 → %15.
    assert metrikler["wape"] == pytest.approx(15.0)


def test_hic_pozitif_gercek_yoksa_mape_nan():
    metrikler = hata_metrikleri(np.array([0.0, 0.0]), np.array([1.0, 2.0]))

    assert np.isnan(metrikler["mape"])


def test_hata_metrikleri_bilinen_degerlerle():
    metrikler = hata_metrikleri(np.array([10.0, 20.0]), np.array([12.0, 18.0]))

    assert metrikler["mae"] == pytest.approx(2.0)
    assert metrikler["rmse"] == pytest.approx(2.0)


def test_pazar_bazinda_metrikler_her_pazari_ayri_veriyor():
    # 🚨 Bulgular §2.5: 18 serinin 10'u A Pazarı'nda; genel ortalama diğerlerini maskeler.
    sonuc = pd.DataFrame(
        {
            "pazar": ["A Pazarı", "A Pazarı", "D Pazarı"],
            "sirket": "Şirket 1",
            "urun": ["Ürün-A", "Ürün-A", "Ürün 77"],
            "tarih": pd.to_datetime(["2026-01-01", "2026-02-01", "2026-01-01"]),
            "gercek": [100.0, 100.0, 10.0],
            "tahmin": [110.0, 90.0, 20.0],
        }
    )

    tablo = pazar_bazinda_metrikler(sonuc)

    assert set(tablo["pazar"]) == {"A Pazarı", "D Pazarı"}
    assert tablo[tablo["pazar"] == "D Pazarı"]["mae"].iloc[0] == pytest.approx(10.0)
