import numpy as np
import pandas as pd
import pytest

from src.analysis.metrics import (
    fiyat_sapmasi,
    hhi,
    mevsimsel_indeks,
    mevsimsellik_gucu,
    pazar_payi,
    promosyon_gelir_kaybi,
    turetilmis_metrikler,
    yillik_buyume,
)


def _cerceve(satirlar: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(satirlar)


def test_net_kutu_formulu():
    # Case tanımı: Net Kutu = Brüt Kutu × (1 − MF Oran).
    df = _cerceve([{"brut_kutu": 100.0, "mf_oran_temiz": 0.2, "net_tl": 800.0}])

    sonuc = turetilmis_metrikler(df)

    assert sonuc["net_kutu"].iloc[0] == pytest.approx(80.0)
    assert sonuc["birim_fiyat"].iloc[0] == pytest.approx(10.0)


def test_mf_bir_oldugunda_birim_fiyat_nan():
    # 🚨 V8: Net Kutu 0 → sıfıra bölme. Sonuç `inf` değil `NaN` olmalı.
    df = _cerceve([{"brut_kutu": 100.0, "mf_oran_temiz": 1.0, "net_tl": 800.0}])

    sonuc = turetilmis_metrikler(df)

    assert np.isnan(sonuc["birim_fiyat"].iloc[0])
    assert not np.isinf(sonuc["birim_fiyat"].iloc[0])


def test_negatif_net_kutu_birim_fiyati_nan_yapar():
    df = _cerceve([{"brut_kutu": -50.0, "mf_oran_temiz": 0.1, "net_tl": 800.0}])

    sonuc = turetilmis_metrikler(df)

    assert np.isnan(sonuc["birim_fiyat"].iloc[0])


def test_pazar_paylari_her_ay_yuze_toplaniyor():
    df = _cerceve(
        [
            {"pazar": "A", "sirket": "Şirket 1", "tarih": "2020-01-01", "brut_kutu": 20.0},
            {"pazar": "A", "sirket": "Şirket 2", "tarih": "2020-01-01", "brut_kutu": 30.0},
            {"pazar": "A", "sirket": "Diğer Şirket", "tarih": "2020-01-01", "brut_kutu": 50.0},
            {"pazar": "A", "sirket": "Şirket 1", "tarih": "2020-02-01", "brut_kutu": 10.0},
            {"pazar": "A", "sirket": "Şirket 2", "tarih": "2020-02-01", "brut_kutu": 10.0},
        ]
    )
    df["tarih"] = pd.to_datetime(df["tarih"])

    paylar = pazar_payi(df)

    toplamlar = paylar.groupby(["pazar", "tarih"], observed=True)["pay"].sum()
    assert toplamlar.round(9).eq(100.0).all()
    ocak_s1 = paylar[(paylar["tarih"] == "2020-01-01") & (paylar["sirket"] == "Şirket 1")]
    assert ocak_s1["pay"].iloc[0] == pytest.approx(20.0)


def test_hhi_tek_oyunculu_pazarda_on_bin():
    df = _cerceve([{"pazar": "A", "sirket": "Şirket 1", "tarih": "2020-01-01", "brut_kutu": 42.0}])
    df["tarih"] = pd.to_datetime(df["tarih"])

    assert hhi(df)["hhi"].iloc[0] == pytest.approx(10000.0)


def test_yillik_buyume_bilinen_seride_dogru():
    df = _cerceve(
        [
            {"pazar": "A", "sirket": "Şirket 1", "tarih": "2020-06-01", "brut_kutu": 100.0},
            {"pazar": "A", "sirket": "Şirket 1", "tarih": "2021-06-01", "brut_kutu": 150.0},
        ]
    )
    df["tarih"] = pd.to_datetime(df["tarih"])

    buyume = yillik_buyume(df)

    assert buyume[buyume["yil"] == 2021]["buyume"].iloc[0] == pytest.approx(50.0)


def test_mevsimsel_indeks_kisa_seride_none_doner():
    # 🚨 V9: 24 aydan kısa seride mevsimsellik hesaplanamaz. `C/Ürün 1` kodu kırmasın.
    seri = pd.Series(
        range(12), index=pd.date_range("2020-01-01", periods=12, freq="MS"), dtype=float
    )

    assert mevsimsel_indeks(seri) is None
    assert mevsimsellik_gucu(seri) is None


def test_mevsimsel_indeks_bilinen_deseni_yakalar():
    # Aralık ayları belirgin şekilde yüksek; indeks o ayı en yüksek göstermeli.
    aylar = pd.date_range("2018-01-01", periods=48, freq="MS")
    degerler = [100.0 + (60.0 if t.month == 12 else 0.0) for t in aylar]
    seri = pd.Series(degerler, index=aylar)

    indeks = mevsimsel_indeks(seri)

    assert indeks.idxmax() == 12
    assert indeks.loc[12] > indeks.loc[6]


def test_mevsimsellik_gucu_duz_seride_sifira_yakin():
    aylar = pd.date_range("2018-01-01", periods=48, freq="MS")
    seri = pd.Series(np.linspace(100.0, 200.0, 48), index=aylar)

    assert mevsimsellik_gucu(seri) < 0.4


def test_promosyon_gelir_kaybi_bilinen_degeri_uretir():
    # bedava_kutu = 100 × 0,2 = 20; birim fiyat = 800 / 80 = 10 → kayıp 200 TL.
    df = _cerceve(
        [
            {
                "pazar": "A",
                "sirket": "Şirket 1",
                "urun": "Ürün-A",
                "tarih": "2020-01-01",
                "brut_kutu": 100.0,
                "mf_oran_temiz": 0.2,
                "net_tl": 800.0,
            }
        ]
    )
    df["tarih"] = pd.to_datetime(df["tarih"])

    kayip = promosyon_gelir_kaybi(turetilmis_metrikler(df))

    assert kayip["gelir_kaybi_tl"].iloc[0] == pytest.approx(200.0)


def test_fiyat_sapmasi_ayni_fiyatta_sifir():
    df = _cerceve(
        [
            {"pazar": "A", "urun": "Ürün-X", "birim_fiyat": 10.0},
            {"pazar": "B", "urun": "Ürün-X", "birim_fiyat": 10.0},
        ]
    )

    assert fiyat_sapmasi(df)["cv"].iloc[0] == pytest.approx(0.0)
