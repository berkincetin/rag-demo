import numpy as np
import pandas as pd
import pytest

from src.analysis.forecast import MF_FEATURES, feature_matrix, lgbm_walk_forward


def _series(pazar, urun, months_=40, start=100.0):
    tarih = pd.date_range("2020-01-01", periods=months_, freq="MS")
    return pd.DataFrame(
        {
            "pazar": pazar,
            "sirket": "Şirket 1",
            "urun": urun,
            "tarih": tarih,
            "brut_kutu": [start + i + 10 * (t.month == 12) for i, t in enumerate(tarih)],
            "mf_oran_temiz": np.linspace(0.05, 0.25, months_),
        }
    )


def test_the_lag_features_point_backwards_in_time():
    # 🚨 lag_1 gerçekten bir önceki ay olmalı; ters kaydırma sızıntıdır.
    df = _series("A Pazarı", "Ürün-A", months_=6, start=100.0)

    matrix = feature_matrix(df).sort_values("tarih").reset_index(drop=True)

    assert np.isnan(matrix.loc[0, "lag_1"])
    assert matrix.loc[1, "lag_1"] == pytest.approx(matrix.loc[0, "brut_kutu"])
    assert matrix.loc[2, "lag_2"] == pytest.approx(matrix.loc[0, "brut_kutu"])


def test_lags_never_cross_a_series_boundary():
    # 🚨 V6: bir serinin lag_1'i başka bir serinin son ayı olamaz.
    a = _series("A Pazarı", "Ürün-A", months_=4, start=100.0)
    b = _series("D Pazarı", "Ürün 77", months_=4, start=9000.0)

    matrix = feature_matrix(pd.concat([a, b]))
    first_b = matrix[(matrix["urun"] == "Ürün 77")].sort_values("tarih").iloc[0]

    assert np.isnan(first_b["lag_1"])


def test_the_ablation_drops_every_mf_feature():
    df = _series("A Pazarı", "Ürün-A", months_=8)

    matrix = feature_matrix(df, with_mf=False)

    assert not set(MF_FEATURES) & set(matrix.columns)


def test_mf_features_are_present_when_requested():
    df = _series("A Pazarı", "Ürün-A", months_=8)

    matrix = feature_matrix(df, with_mf=True)

    assert set(MF_FEATURES) <= set(matrix.columns)


def test_lgbm_predictions_are_never_negative():
    # Hedef log1p ile dönüştürülüyor; geri çevirmede negatif çıkmamalı.
    df = pd.concat([_series("A Pazarı", "Ürün-A"), _series("B Pazarı", "Ürün-FR", start=50.0)])

    result = lgbm_walk_forward(df, months=2)

    assert len(result) > 0
    assert (result["tahmin"] >= 0).all()


def test_the_ablation_compares_the_same_folds():
    # İki model aynı hedef aylarda değerlendirilmezse delta anlamsız olur.
    df = pd.concat([_series("A Pazarı", "Ürün-A"), _series("B Pazarı", "Ürün-FR", start=50.0)])

    mf_ile = lgbm_walk_forward(df, with_mf=True, months=2)
    mf_siz = lgbm_walk_forward(df, with_mf=False, months=2)

    anahtar = ["pazar", "urun", "tarih"]
    assert mf_ile[anahtar].reset_index(drop=True).equals(mf_siz[anahtar].reset_index(drop=True))


def test_short_series_train_the_model_but_are_never_targets():
    short = _series("C Pazarı", "Ürün 1", months_=3, start=5.0)
    long_ = _series("A Pazarı", "Ürün-A")

    result = lgbm_walk_forward(pd.concat([short, long_]), months=2)

    assert set(result["urun"]) == {"Ürün-A"}


def test_target_selection_does_not_rely_on_index_labels():
    # Çağıran taraf indeksi sıfırlamamış olabilir. Aynı etiketi taşıyan ve aynı aya
    # düşen kısa bir series, long_ serinin hedef satırıyla karışmamalı.
    long_ = _series("A Pazarı", "Ürün-A", months_=40)
    short = _series("C Pazarı", "Ürün 1", months_=3, start=5.0)
    short["tarih"] = long_["tarih"].to_numpy()[-3:]
    short.index = long_.index[-3:]

    result = lgbm_walk_forward(pd.concat([long_, short]), months=2)

    assert set(result["urun"]) == {"Ürün-A"}
    assert len(result) == 2
