import matplotlib

matplotlib.use("Agg")  # Testler başsız koşar; pencere açılmamalı.

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from src.analysis.plots import (  # noqa: E402
    FIGUR_DIZINI,
    PAZAR_RENKLERI,
    SIRKET_RENKLERI,
    kaydet,
    stil_uygula,
    tr_sayi,
)


def test_tr_sayi_binlik_nokta_ondalik_virgul():
    assert tr_sayi(1234567.8, ondalik=1) == "1.234.567,8"


def test_tr_sayi_ondaliksiz_yuvarliyor():
    assert tr_sayi(1234.6) == "1.235"


def test_tr_sayi_negatif_ve_sifir():
    assert tr_sayi(-1234.5, ondalik=1) == "-1.234,5"
    assert tr_sayi(0) == "0"


def test_dort_pazarin_da_rengi_tanimli():
    # Grafiğin ortasında KeyError almamak için palet eksiksiz olmalı.
    for pazar in ("A Pazarı", "B Pazarı", "C Pazarı", "D Pazarı"):
        assert pazar in PAZAR_RENKLERI


def test_uc_sirketin_de_rengi_tanimli():
    for sirket in ("Şirket 1", "Şirket 2", "Diğer Şirket"):
        assert sirket in SIRKET_RENKLERI


def test_kaydet_png_uretiyor_ve_yol_donduruyor(tmp_path):
    fig, eksen = plt.subplots()
    eksen.plot([1, 2, 3], [1, 4, 9])

    yol = kaydet(fig, "deneme", dizin=tmp_path)
    plt.close(fig)

    assert yol == tmp_path / "deneme.png"
    assert yol.stat().st_size > 0


def test_stil_uygula_turkce_eksen_ayirici_kuruyor():
    stil_uygula()

    assert plt.rcParams["axes.grid"] is True
    assert plt.rcParams["figure.dpi"] == pytest.approx(110)


def test_varsayilan_figur_dizini_calisma_dizininden_bagimsiz(tmp_path, monkeypatch):
    # Notebook `notebooks/` içinden koşuyor; göreli varsayılan figürleri oraya yazardı.
    monkeypatch.chdir(tmp_path)

    assert FIGUR_DIZINI.is_absolute()
    assert FIGUR_DIZINI.name == "figures"
