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

from src.analysis.load import ANAHTAR

TEST_AYLARI = 12
MIN_EGITIM_AYI = 6

Tahminci = Callable[[pd.Series], float]


def naive(gecmis: pd.Series) -> float:
    """ŷ(t+1) = y(t)."""
    return float(gecmis.iloc[-1])


def snaive(gecmis: pd.Series) -> float:
    """ŷ(t+1) = y(t−11). Geçmiş 12 aydan kısaysa `naive`'e düşer."""
    if len(gecmis) < 12:
        return naive(gecmis)
    return float(gecmis.iloc[-12])


def ma3(gecmis: pd.Series) -> float:
    """ŷ(t+1) = son üç ayın ortalaması."""
    return float(gecmis.iloc[-3:].mean())


def walk_forward(
    df: pd.DataFrame, tahminci: Tahminci, ay_sayisi: int = TEST_AYLARI
) -> pd.DataFrame:
    """Her seri için son `ay_sayisi` ayı bir ay ileri tahmin eder.

    Eğitim penceresi genişler ve **hedef ayı hiçbir zaman içermez** — sızıntı testi
    bunu doğrular. `MIN_EGITIM_AYI`'ndan kısa geçmişi olan seriler atlanır; tek
    gözlemli `C/Ürün 1` gibi seriler burada kodu kırardı.
    """
    satirlar = []
    for anahtar, grup in df.groupby(ANAHTAR, observed=True):
        seri = grup.sort_values("tarih").set_index("tarih")["brut_kutu"]
        seri = seri.fillna(0.0).clip(lower=0.0)  # V4: iadeler tahmin girdisinde 0'lanır
        if len(seri) < MIN_EGITIM_AYI + 1:
            continue
        hedefler = seri.index[-min(ay_sayisi, len(seri) - MIN_EGITIM_AYI) :]
        for hedef in hedefler:
            gecmis = seri.loc[seri.index < hedef]
            if len(gecmis) < MIN_EGITIM_AYI:
                continue
            satirlar.append(
                {
                    "pazar": anahtar[0],
                    "sirket": anahtar[1],
                    "urun": anahtar[2],
                    "tarih": hedef,
                    "gercek": float(seri.loc[hedef]),
                    "tahmin": float(tahminci(gecmis)),
                }
            )
    return pd.DataFrame(satirlar, columns=["pazar", "sirket", "urun", "tarih", "gercek", "tahmin"])


def hata_metrikleri(gercek: Sequence[float], tahmin: Sequence[float]) -> dict[str, float]:
    """MAE, RMSE, MAPE (%), WAPE (%), sMAPE (%).

    MAPE yalnız `gercek > 0` gözlemlerde hesaplanır; hiç yoksa `NaN` döner —
    sonsuz bir değer tabloyu okunamaz hale getirirdi.
    """
    y = np.asarray(gercek, dtype=float)
    yhat = np.asarray(tahmin, dtype=float)
    hata = np.abs(y - yhat)

    pozitif = y > 0
    mape = float(100.0 * np.mean(hata[pozitif] / y[pozitif])) if pozitif.any() else float("nan")
    wape = float(100.0 * hata.sum() / y.sum()) if y.sum() > 0 else float("nan")

    payda = np.abs(y) + np.abs(yhat)
    gecerli = payda > 0
    smape = float(100.0 * np.mean(2.0 * hata[gecerli] / payda[gecerli])) if gecerli.any() else 0.0

    return {
        "mae": float(hata.mean()),
        "rmse": float(np.sqrt(np.mean((y - yhat) ** 2))),
        "mape": mape,
        "wape": wape,
        "smape": smape,
    }


def pazar_bazinda_metrikler(sonuc: pd.DataFrame) -> pd.DataFrame:
    """Hata metriklerini pazar bazında tablolar.

    Genel ortalama tek başına yanıltıcıdır: Şirket 1'in 18 serisinin 10'u A
    Pazarı'nda, dolayısıyla toplu metrik A Pazarı'nın sonucunu gösterir.
    """
    satirlar = []
    for pazar, grup in sonuc.groupby("pazar", observed=True):
        satir = {"pazar": pazar, "gozlem": len(grup)}
        satir.update(hata_metrikleri(grup["gercek"].to_numpy(), grup["tahmin"].to_numpy()))
        satirlar.append(satir)
    return pd.DataFrame(satirlar)
