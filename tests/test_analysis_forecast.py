import numpy as np
import pandas as pd
import pytest

from src.analysis.forecast import (
    error_metrics,
    ma3,
    metrics_by_market,
    naive,
    snaive,
    walk_forward,
)


def _series(pazar="A Pazarı", urun="Ürün-A", months_=36, start=100.0, step=1.0):
    tarih = pd.date_range("2020-01-01", periods=months_, freq="MS")
    return pd.DataFrame(
        {
            "pazar": pazar,
            "sirket": "Şirket 1",
            "urun": urun,
            "tarih": tarih,
            "brut_kutu": [start + step * i for i in range(months_)],
            "mf_oran_temiz": 0.1,
        }
    )


def test_naive_returns_the_last_observation():
    assert naive(pd.Series([5.0, 9.0, 12.0])) == pytest.approx(12.0)


def test_snaive_returns_the_value_twelve_months_back():
    history = pd.Series(range(24), dtype=float)

    assert snaive(history) == pytest.approx(12.0)


def test_snaive_falls_back_to_naive_on_short_history():
    # 12 aydan kısa geçmişte mevsimsel referans yok; sessizce hata vermemeli.
    history = pd.Series([3.0, 7.0])

    assert snaive(history) == pytest.approx(7.0)


def test_ma3_averages_the_last_three_months():
    assert ma3(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])) == pytest.approx(4.0)


def test_walk_forward_never_leaks_the_future():
    # 🚨 Her katmanda tahminci yalnız t anına kadarki geçmişi görmeli.
    seen_last_dates = []

    def recording_forecaster(history: pd.Series) -> float:
        seen_last_dates.append(history.index.max())
        return float(history.iloc[-1])

    df = _series(months_=36)
    result = walk_forward(df, recording_forecaster, months=3)

    for gorulen, hedef in zip(seen_last_dates, result["tarih"], strict=True):
        assert gorulen < hedef


def test_walk_forward_predicts_one_month_ahead():
    df = _series(months_=36)

    result = walk_forward(df, naive, months=3)

    assert len(result) == 3
    assert result["tarih"].tolist() == df["tarih"].tolist()[-3:]
    # naive: t+1 tahmini t'nin değeri → gerçek her zaman 1 fazla (step=1.0).
    assert (result["gercek"] - result["tahmin"]).round(6).eq(1.0).all()


def test_walk_forward_skips_a_series_that_is_too_short():
    # `C/Ürün 1` gibi tek gözlemli seriler kodu kırmamalı.
    short = _series(pazar="C Pazarı", urun="Ürün 1", months_=1)
    long_ = _series(months_=36)

    result = walk_forward(pd.concat([short, long_]), naive, months=3)

    assert set(result["urun"]) == {"Ürün-A"}


def test_mape_does_not_explode_on_zero_actuals():
    # 🚨 V10: y = 0 gözlemler MAPE'den dışlanır, `inf` üretmez.
    measures = error_metrics(np.array([0.0, 100.0]), np.array([5.0, 90.0]))

    assert np.isfinite(measures["mape"])
    assert measures["mape"] == pytest.approx(10.0)


def test_wape_is_robust_to_zeros():
    measures = error_metrics(np.array([0.0, 100.0]), np.array([5.0, 90.0]))

    # Σ|hata| = 5 + 10 = 15; Σy = 100 → %15.
    assert measures["wape"] == pytest.approx(15.0)


def test_mape_is_nan_when_no_actual_is_positive():
    measures = error_metrics(np.array([0.0, 0.0]), np.array([1.0, 2.0]))

    assert np.isnan(measures["mape"])


def test_error_metrics_on_hand_computed_values():
    measures = error_metrics(np.array([10.0, 20.0]), np.array([12.0, 18.0]))

    assert measures["mae"] == pytest.approx(2.0)
    assert measures["rmse"] == pytest.approx(2.0)


def test_metrics_are_reported_per_market():
    # 🚨 Bulgular §2.5: 18 serinin 10'u A Pazarı'nda; genel ortalama diğerlerini maskeler.
    result = pd.DataFrame(
        {
            "pazar": ["A Pazarı", "A Pazarı", "D Pazarı"],
            "sirket": "Şirket 1",
            "urun": ["Ürün-A", "Ürün-A", "Ürün 77"],
            "tarih": pd.to_datetime(["2026-01-01", "2026-02-01", "2026-01-01"]),
            "gercek": [100.0, 100.0, 10.0],
            "tahmin": [110.0, 90.0, 20.0],
        }
    )

    table = metrics_by_market(result)

    assert set(table["pazar"]) == {"A Pazarı", "D Pazarı"}
    assert table[table["pazar"] == "D Pazarı"]["mae"].iloc[0] == pytest.approx(10.0)
