"""Talep tahmini: temel modeller ve walk-forward değerlendirme.

Değerlendirme genişleyen pencereli walk-forward'dır: son 12 ay tek tek tahmin
edilir ve her adımda model yalnız o ana kadarki geçmişi görür. Zaman serisinde tek
bir train/test bölmesi yanıltıcıdır — tek bir aya denk gelen şans, modelin
sıralamasını değiştirebilir.

MAPE case'in istediği metrik ama sıfıra yakın gerçek değerlerde patlar; bu veride
9.536 sıfır aylık gözlem var. Bu yüzden MAPE yalnız `y > 0` gözlemlerde hesaplanır
ve yanına sıfır-dayanıklı WAPE ile sMAPE konur (V10).
"""

from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd

from src.analysis.load import KEY

TEST_MONTHS = 12
MIN_TRAIN_MONTHS = 6

MF_FEATURES = ["mf_lag_0", "mf_lag_1", "mf_roll_mean_3"]
_BASE_FEATURES = [
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_12",
    "roll_mean_3",
    "roll_mean_6",
    "roll_std_3",
    "ay",
    "ceyrek",
    "yil_indeksi",
    "seri_uzunlugu",
]
_CATEGORICALS = ["pazar", "urun"]

Forecaster = Callable[[pd.Series], float]


def naive(history: pd.Series) -> float:
    """ŷ(t+1) = y(t)."""
    return float(history.iloc[-1])


def snaive(history: pd.Series) -> float:
    """ŷ(t+1) = y(t−11). Geçmiş 12 aydan kısaysa `naive`'e düşer."""
    if len(history) < 12:
        return naive(history)
    return float(history.iloc[-12])


def ma3(history: pd.Series) -> float:
    """ŷ(t+1) = son üç ayın ortalaması."""
    return float(history.iloc[-3:].mean())


def walk_forward(
    df: pd.DataFrame, forecaster: Forecaster, months: int = TEST_MONTHS
) -> pd.DataFrame:
    """Her seri için son `months` ayı bir ay ileri tahmin eder.

    Eğitim penceresi genişler ve **hedef ayı hiçbir zaman içermez** — sızıntı testi
    bunu doğrular. `MIN_TRAIN_MONTHS`'tan kısa geçmişi olan seriler atlanır; tek
    gözlemli `C/Ürün 1` gibi seriler burada kodu kırardı.
    """
    rows = []
    for key, group in df.groupby(KEY, observed=True):
        series = group.sort_values("tarih").set_index("tarih")["brut_kutu"]
        series = series.fillna(0.0).clip(lower=0.0)  # V4: iadeler tahminde 0'lanır
        if len(series) < MIN_TRAIN_MONTHS + 1:
            continue
        targets = series.index[-min(months, len(series) - MIN_TRAIN_MONTHS) :]
        for target in targets:
            history = series.loc[series.index < target]
            if len(history) < MIN_TRAIN_MONTHS:
                continue
            rows.append(
                {
                    "pazar": key[0],
                    "sirket": key[1],
                    "urun": key[2],
                    "tarih": target,
                    "gercek": float(series.loc[target]),
                    "tahmin": float(forecaster(history)),
                }
            )
    return pd.DataFrame(rows, columns=["pazar", "sirket", "urun", "tarih", "gercek", "tahmin"])


def error_metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, float]:
    """MAE, RMSE, MAPE (%), WAPE (%), sMAPE (%).

    MAPE yalnız `actual > 0` gözlemlerde hesaplanır; hiç yoksa `NaN` döner —
    sonsuz bir değer tabloyu okunamaz hale getirirdi.
    """
    y = np.asarray(actual, dtype=float)
    yhat = np.asarray(predicted, dtype=float)
    error = np.abs(y - yhat)

    positive = y > 0
    mape = float(100.0 * np.mean(error[positive] / y[positive])) if positive.any() else float("nan")
    wape = float(100.0 * error.sum() / y.sum()) if y.sum() > 0 else float("nan")

    denominator = np.abs(y) + np.abs(yhat)
    valid = denominator > 0
    smape = float(100.0 * np.mean(2.0 * error[valid] / denominator[valid])) if valid.any() else 0.0

    return {
        "mae": float(error.mean()),
        "rmse": float(np.sqrt(np.mean((y - yhat) ** 2))),
        "mape": mape,
        "wape": wape,
        "smape": smape,
    }


def metrics_by_market(result: pd.DataFrame) -> pd.DataFrame:
    """Hata metriklerini pazar bazında tablolar.

    Genel ortalama tek başına yanıltıcıdır: Şirket 1'in 18 serisinin 10'u A
    Pazarı'nda, dolayısıyla toplu metrik A Pazarı'nın sonucunu gösterir.
    """
    rows = []
    for market, group in result.groupby("pazar", observed=True):
        row = {"pazar": market, "gozlem": len(group)}
        row.update(error_metrics(group["gercek"].to_numpy(), group["tahmin"].to_numpy()))
        rows.append(row)
    return pd.DataFrame(rows)


def feature_matrix(df: pd.DataFrame, with_mf: bool = True) -> pd.DataFrame:
    """Gecikme, hareketli ortalama, takvim ve kategorik özellikleri üretir.

    Bütün kaydırmalar `(pazar, sirket, urun)` içinde yapılır: bir serinin `lag_1`'i
    başka bir serinin son ayı olamaz (V6). Kaydırma yönü de kritik — ters çevrilirse
    model geleceği görür ve metrikler sahte biçimde iyi çıkar.
    """
    # İndeks burada sıfırlanır: hedef satırları etiketle seçiliyor ve çağıran taraf
    # (ör. iki çerçeveyi `concat` eden notebook hücresi) yinelenen etiket bırakmış
    # olabilir. Yinelenen etiket, hedef olmaması gereken kısa bir seriyi tahmin
    # setine sızdırıyordu — testle yakalandı.
    data = df.sort_values([*KEY, "tarih"]).reset_index(drop=True)
    data["brut_kutu"] = data["brut_kutu"].fillna(0.0).clip(lower=0.0)
    grouped = data.groupby(KEY, observed=True)["brut_kutu"]

    for lag in (1, 2, 3, 12):
        data[f"lag_{lag}"] = grouped.shift(lag)
    shifted = grouped.shift(1)
    by_series = shifted.groupby([data[k] for k in KEY], observed=True)
    data["roll_mean_3"] = by_series.transform(lambda s: s.rolling(3).mean())
    data["roll_mean_6"] = by_series.transform(lambda s: s.rolling(6).mean())
    data["roll_std_3"] = by_series.transform(lambda s: s.rolling(3).std())

    data["ay"] = data["tarih"].dt.month
    data["ceyrek"] = data["tarih"].dt.quarter
    data["yil_indeksi"] = data["tarih"].dt.year - int(data["tarih"].dt.year.min())
    data["seri_uzunlugu"] = data.groupby(KEY, observed=True)["tarih"].transform("size")

    if with_mf:
        mf_shifted = data.groupby(KEY, observed=True)["mf_oran_temiz"].shift(1)
        data["mf_lag_0"] = data["mf_oran_temiz"]
        data["mf_lag_1"] = mf_shifted
        data["mf_roll_mean_3"] = mf_shifted.groupby(
            [data[k] for k in KEY], observed=True
        ).transform(lambda s: s.rolling(3).mean())
    else:
        data = data.drop(columns=[c for c in MF_FEATURES if c in data.columns])

    return data


def lgbm_walk_forward(
    df: pd.DataFrame, with_mf: bool = True, months: int = TEST_MONTHS
) -> pd.DataFrame:
    """Global LightGBM'i walk-forward değerlendirir.

    Tek model bütün serileri birlikte öğrenir; kısa seriler eğitim havuzunda kalır
    ama hedef olarak seçilmez (geçmişleri yetersiz). Hedef `log1p` ölçeğinde:
    hacimler pazarlar arası üç mertebe farklı ve log ölçek olmadan büyük serilerin
    kaybı modeli domine eder. Tahmin `expm1` ile geri çevrilip 0'a kırpılır.
    """
    import lightgbm as lgb

    matrix = feature_matrix(df, with_mf=with_mf)
    features = list(_BASE_FEATURES)
    if with_mf:
        features += MF_FEATURES
    for column in _CATEGORICALS:
        matrix[column] = matrix[column].astype("category")

    targets = _target_dates(matrix, months)
    frames = []
    for target in sorted(targets):
        train = matrix[matrix["tarih"] < target]
        test = matrix[(matrix["tarih"] == target) & (matrix.index.isin(targets[target]))]
        if train.empty or test.empty:
            continue
        model = lgb.LGBMRegressor(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=10,
            random_state=42,
            verbose=-1,
        )
        model.fit(
            train[features + _CATEGORICALS],
            np.log1p(train["brut_kutu"]),
            categorical_feature=_CATEGORICALS,
        )
        predicted = np.expm1(model.predict(test[features + _CATEGORICALS])).clip(min=0.0)
        frames.append(
            pd.DataFrame(
                {
                    "pazar": test["pazar"].astype(str).to_numpy(),
                    "sirket": test["sirket"].astype(str).to_numpy(),
                    "urun": test["urun"].astype(str).to_numpy(),
                    "tarih": test["tarih"].to_numpy(),
                    "gercek": test["brut_kutu"].to_numpy(),
                    "tahmin": predicted,
                }
            )
        )

    if not frames:
        return pd.DataFrame(columns=["pazar", "sirket", "urun", "tarih", "gercek", "tahmin"])
    return (
        pd.concat(frames).sort_values(["pazar", "sirket", "urun", "tarih"]).reset_index(drop=True)
    )


def _target_dates(matrix: pd.DataFrame, months: int) -> dict[pd.Timestamp, list[int]]:
    """Hangi ayda hangi satırların tahmin edileceği.

    Temel modellerle **aynı** seri seçimini kullanır ki karşılaştırma adil olsun ve
    ablasyonun iki tarafı aynı katmanlarda değerlendirilsin.
    """
    targets: dict[pd.Timestamp, list[int]] = {}
    for _, group in matrix.groupby(KEY, observed=True):
        ordered = group.sort_values("tarih")
        if len(ordered) < MIN_TRAIN_MONTHS + 1:
            continue
        selected = ordered.iloc[-min(months, len(ordered) - MIN_TRAIN_MONTHS) :]
        for index, date in zip(selected.index, selected["tarih"], strict=True):
            targets.setdefault(date, []).append(index)
    return targets


def mf_ablation(df: pd.DataFrame, months: int = TEST_MONTHS) -> pd.DataFrame:
    """`lgbm` ile `lgbm_no_mf`'i pazar bazında karşılaştırır."""
    with_mf = metrics_by_market(lgbm_walk_forward(df, with_mf=True, months=months))
    without_mf = metrics_by_market(lgbm_walk_forward(df, with_mf=False, months=months))
    merged = with_mf.merge(without_mf, on="pazar", suffixes=("_mf_ile", "_mf_siz"))
    merged["mae_farki"] = merged["mae_mf_siz"] - merged["mae_mf_ile"]
    merged["wape_farki"] = merged["wape_mf_siz"] - merged["wape_mf_ile"]
    return merged
