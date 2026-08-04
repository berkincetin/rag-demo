import numpy as np
import pandas as pd
import pytest

from src.analysis.metrics import (
    derived_metrics,
    hhi,
    market_share,
    price_dispersion,
    promo_revenue_loss,
    seasonal_index,
    seasonality_strength,
    yoy_growth,
)


def _frame(satirlar: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(satirlar)


def test_the_net_units_formula():
    # Case tanımı: Net Kutu = Brüt Kutu × (1 − MF Oran).
    df = _frame([{"brut_kutu": 100.0, "mf_oran_temiz": 0.2, "net_tl": 800.0}])

    result = derived_metrics(df)

    assert result["net_kutu"].iloc[0] == pytest.approx(80.0)
    assert result["birim_fiyat"].iloc[0] == pytest.approx(10.0)


def test_unit_price_is_nan_when_mf_is_one():
    # 🚨 V8: Net Kutu 0 → sıfıra bölme. Sonuç `inf` değil `NaN` olmalı.
    df = _frame([{"brut_kutu": 100.0, "mf_oran_temiz": 1.0, "net_tl": 800.0}])

    result = derived_metrics(df)

    assert np.isnan(result["birim_fiyat"].iloc[0])
    assert not np.isinf(result["birim_fiyat"].iloc[0])


def test_negative_net_units_make_the_unit_price_nan():
    df = _frame([{"brut_kutu": -50.0, "mf_oran_temiz": 0.1, "net_tl": 800.0}])

    result = derived_metrics(df)

    assert np.isnan(result["birim_fiyat"].iloc[0])


def test_market_shares_sum_to_a_hundred_each_month():
    df = _frame(
        [
            {"pazar": "A", "sirket": "Şirket 1", "tarih": "2020-01-01", "brut_kutu": 20.0},
            {"pazar": "A", "sirket": "Şirket 2", "tarih": "2020-01-01", "brut_kutu": 30.0},
            {"pazar": "A", "sirket": "Diğer Şirket", "tarih": "2020-01-01", "brut_kutu": 50.0},
            {"pazar": "A", "sirket": "Şirket 1", "tarih": "2020-02-01", "brut_kutu": 10.0},
            {"pazar": "A", "sirket": "Şirket 2", "tarih": "2020-02-01", "brut_kutu": 10.0},
        ]
    )
    df["tarih"] = pd.to_datetime(df["tarih"])

    paylar = market_share(df)

    toplamlar = paylar.groupby(["pazar", "tarih"], observed=True)["pay"].sum()
    assert toplamlar.round(9).eq(100.0).all()
    ocak_s1 = paylar[(paylar["tarih"] == "2020-01-01") & (paylar["sirket"] == "Şirket 1")]
    assert ocak_s1["pay"].iloc[0] == pytest.approx(20.0)


def test_hhi_is_ten_thousand_in_a_single_player_market():
    df = _frame([{"pazar": "A", "sirket": "Şirket 1", "tarih": "2020-01-01", "brut_kutu": 42.0}])
    df["tarih"] = pd.to_datetime(df["tarih"])

    assert hhi(df)["hhi"].iloc[0] == pytest.approx(10000.0)


def test_yoy_growth_is_correct_on_a_known_series():
    df = _frame(
        [
            {"pazar": "A", "sirket": "Şirket 1", "tarih": "2020-06-01", "brut_kutu": 100.0},
            {"pazar": "A", "sirket": "Şirket 1", "tarih": "2021-06-01", "brut_kutu": 150.0},
        ]
    )
    df["tarih"] = pd.to_datetime(df["tarih"])

    buyume = yoy_growth(df)

    assert buyume[buyume["yil"] == 2021]["buyume"].iloc[0] == pytest.approx(50.0)


def test_seasonality_returns_none_for_a_short_series():
    # 🚨 V9: 24 aydan kısa seride mevsimsellik hesaplanamaz. `C/Ürün 1` kodu kırmasın.
    series = pd.Series(
        range(12), index=pd.date_range("2020-01-01", periods=12, freq="MS"), dtype=float
    )

    assert seasonal_index(series) is None
    assert seasonality_strength(series) is None


def test_the_seasonal_index_finds_a_known_pattern():
    # Aralık ayları belirgin şekilde yüksek; indeks o ayı en yüksek göstermeli.
    months_ = pd.date_range("2018-01-01", periods=48, freq="MS")
    values_ = [100.0 + (60.0 if t.month == 12 else 0.0) for t in months_]
    series = pd.Series(values_, index=months_)

    indeks = seasonal_index(series)

    assert indeks.idxmax() == 12
    assert indeks.loc[12] > indeks.loc[6]


def test_seasonality_strength_is_near_zero_on_a_flat_series():
    months_ = pd.date_range("2018-01-01", periods=48, freq="MS")
    series = pd.Series(np.linspace(100.0, 200.0, 48), index=months_)

    assert seasonality_strength(series) < 0.4


def test_promo_revenue_loss_matches_a_hand_computed_value():
    # bedava_kutu = 100 × 0,2 = 20; birim fiyat = 800 / 80 = 10 → kayıp 200 TL.
    df = _frame(
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

    loss = promo_revenue_loss(derived_metrics(df))

    assert loss["gelir_kaybi_tl"].iloc[0] == pytest.approx(200.0)


def test_price_dispersion_is_zero_at_an_identical_price():
    df = _frame(
        [
            {"pazar": "A", "urun": "Ürün-X", "birim_fiyat": 10.0},
            {"pazar": "B", "urun": "Ürün-X", "birim_fiyat": 10.0},
        ]
    )

    assert price_dispersion(df)["cv"].iloc[0] == pytest.approx(0.0)


def test_seasonality_does_not_count_months_without_sales_as_history():
    # 🚨 `C Pazarı/Ürün 1` kırpma sonrası 28 satır taşıyor ama yalnız BİR ayında
    # satış var. Satır sayısına bakan bir eşik bunu "yeterli geçmiş" sayıyor ve STL
    # tek sıçramayı mevsimsellik diye raporluyordu: güç 0,987, zirve indeksi 8,72.
    # Uydurulmuş mevsimsellik, eksik veriden daha kötüdür.
    months_ = pd.date_range("2024-01-01", periods=28, freq="MS")
    values_ = [1.0] + [0.0] * 27
    series = pd.Series(values_, index=months_)

    assert seasonal_index(series) is None
    assert seasonality_strength(series) is None
