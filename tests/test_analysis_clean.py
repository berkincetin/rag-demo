import numpy as np
import pandas as pd
import pytest

from src.analysis.clean import clean, detect_mf_scale
from src.analysis.load import DATA_PATH, load_raw


def _series(pazar, sirket, urun, months_, brut, mf, net_tl=None):
    """Tek bir (pazar, şirket, ürün) serisi için küçük kurgu çerçeve."""
    return pd.DataFrame(
        {
            "pazar": pazar,
            "sirket": sirket,
            "urun": urun,
            "tarih": pd.date_range("2020-01-01", periods=months_, freq="MS"),
            "brut_kutu": brut,
            "mf_oran": mf,
            "net_tl": net_tl if net_tl is not None else [1000.0] * months_,
        }
    )


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    if not DATA_PATH.exists():
        pytest.skip(f"veri seti yok: {DATA_PATH}")
    return load_raw()


@pytest.mark.integration
def test_only_market_b_is_detected_as_percent_scaled(raw):
    # 🚨 Projenin en kritik testi. Bulgular §2.3: B'de medyan 5,9–7,4, diğerlerinde ~0.
    # Bu düzeltme olmadan Net Kutu negatife düşer ve A4/A6/A7 tamamen yanlış olur.
    factors = detect_mf_scale(raw)

    assert factors["B Pazarı"] == 100.0
    assert factors["A Pazarı"] == 1.0
    assert factors["C Pazarı"] == 1.0
    assert factors["D Pazarı"] == 1.0


def test_scale_detection_never_hardcodes_a_market_name():
    # Kural veriden gelmeli, addan değil: adı B olmayan yüzde ölçekli bir pazar da
    # yakalanmalı, adı B olan oran ölçekli bir pazar ise yakalanmamalı.
    df = pd.concat(
        [
            _series("Z Pazarı", "Şirket 1", "Ürün-Z", 4, [10.0] * 4, [7.0, 6.0, 8.0, 5.0]),
            _series("B Pazarı", "Şirket 1", "Ürün-B", 4, [10.0] * 4, [0.1, 0.2, 0.15, 0.05]),
        ]
    )

    factors = detect_mf_scale(df)

    assert factors["Z Pazarı"] == 100.0
    assert factors["B Pazarı"] == 1.0


def test_scale_detection_excludes_zeros_from_the_median():
    # MF'in çoğu ayda 0 olduğu bir yüzde ölçekli seride, sıfırlar medyana katılırsa
    # medyan 0 çıkar ve ölçek sorunu gözden kaçar.
    df = _series("Y Pazarı", "Şirket 1", "Ürün-Y", 6, [10.0] * 6, [0.0, 0.0, 0.0, 0.0, 8.0, 9.0])

    assert detect_mf_scale(df)["Y Pazarı"] == 100.0


@pytest.mark.integration
def test_market_b_unit_price_is_positive_after_the_fix(raw):
    # 🚨 Bulgular §2.3: düzeltmesiz 2016-01'de −0,88 TL, düzeltmeli 8,32 TL.
    cleaned, _ = clean(raw)
    row = cleaned[
        (cleaned["pazar"] == "B Pazarı")
        & (cleaned["sirket"] == "Şirket 1")
        & (cleaned["urun"] == "Ürün-FR")
        & (cleaned["tarih"] == pd.Timestamp("2016-01-01"))
    ].iloc[0]

    net_kutu = row["brut_kutu"] * (1 - row["mf_oran_temiz"])
    birim_fiyat = row["net_tl"] / net_kutu

    assert birim_fiyat == pytest.approx(8.32, abs=0.05)


def test_product_names_are_whitespace_normalised():
    # Bulgular §2.4: C/D pazarlarında `Ürün  2` (çift boşluk) geçiyor.
    df = _series("C Pazarı", "Şirket 1", "Ürün  2", 3, [1.0, 2.0, 3.0], [0.0] * 3)

    cleaned, _ = clean(df)

    assert cleaned["urun"].unique().tolist() == ["Ürün 2"]


def test_mf_clipping_applies_the_upper_bound():
    # Bulgular §2.4: ölçek düzeltmesinden sonra bile 469,5 gibi imkânsız değerler var.
    df = _series("A Pazarı", "Şirket 1", "Ürün-A", 3, [10.0] * 3, [0.2, 469.5, -0.3])

    cleaned, report = clean(df)

    assert cleaned["mf_oran_temiz"].max() <= 0.95
    assert cleaned["mf_oran_temiz"].min() >= 0.0
    assert cleaned["mf_kirpildi"].sum() == 2
    assert report.mf_clipped == 2


def test_returns_are_flagged_not_deleted():
    # V4: iade kayıtları toplamlarda kalmalı, yoksa hacim şişer.
    df = _series("A Pazarı", "Şirket 1", "Ürün-A", 3, [10.0, -5.0, 8.0], [0.0] * 3)

    cleaned, report = clean(df)

    assert len(cleaned) == 3
    assert cleaned["iade_mi"].sum() == 1
    assert report.return_rows == 1


def test_months_before_the_first_sale_are_dropped():
    # V5: ilk pozitif satıştan önceki dönem ürün yok demektir; sonraki sıfır gerçek sıfır.
    df = _series("A Pazarı", "Şirket 1", "Ürün-A", 5, [0.0, 0.0, 7.0, 0.0, 3.0], [0.0] * 5)

    cleaned, report = clean(df)

    assert len(cleaned) == 3
    assert cleaned["tarih"].min() == pd.Timestamp("2020-03-01")
    assert report.pre_launch_dropped == 2


def test_a_series_that_never_sold_is_dropped_entirely():
    df = _series("A Pazarı", "Şirket 1", "Ürün-A", 3, [0.0, np.nan, 0.0], [0.0] * 3)

    cleaned, _ = clean(df)

    assert cleaned.empty


@pytest.mark.integration
def test_the_report_lists_the_short_series(raw):
    # Bulgular §2.5: C/Ürün 1 tek satışlı, D/Ürün 78 on bir aylık — gizlenmemeli.
    # Uzunluk satır sayısıyla ölçülseydi C/Ürün 1 kırpma sonrası 27 satırla
    # "yeterli geçmişi var" görünürdü; oysa 26'sı gerçek sıfır.
    _, report = clean(raw)

    assert report.short_series[("C Pazarı", "Şirket 1", "Ürün 1")] == 1
    assert report.short_series[("D Pazarı", "Şirket 1", "Ürün 78")] == 11


@pytest.mark.integration
def test_report_counts_agree_with_the_real_data(raw):
    # Bulgular §2.4: 1.158 negatif Brüt Kutu, 1.168 negatif Net TL → birleşik bayrak.
    _, report = clean(raw)

    assert report.rescaled_markets == {"B Pazarı": 100.0}
    assert report.raw_rows > report.clean_rows
    assert report.return_rows > 1000
