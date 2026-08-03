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

MF_OZELLIKLERI = ["mf_lag_0", "mf_lag_1", "mf_roll_mean_3"]
_TEMEL_OZELLIKLER = [
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
_KATEGORIKLER = ["pazar", "urun"]

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


def ozellik_matrisi(df: pd.DataFrame, mf_dahil: bool = True) -> pd.DataFrame:
    """Gecikme, hareketli ortalama, takvim ve kategorik özellikleri üretir.

    Bütün kaydırmalar `(pazar, sirket, urun)` içinde yapılır: bir serinin `lag_1`'i
    başka bir serinin son ayı olamaz (V6). Kaydırma yönü de kritik — ters çevrilirse
    model geleceği görür ve metrikler sahte biçimde iyi çıkar.
    """
    # İndeks burada sıfırlanır: hedef satırları etiketle seçiliyor ve çağıran taraf
    # (ör. iki çerçeveyi `concat` eden notebook hücresi) yinelenen etiket bırakmış
    # olabilir. Yinelenen etiket, hedef olmaması gereken kısa bir seriyi tahmin
    # setine sızdırıyordu — testle yakalandı.
    veri = df.sort_values([*ANAHTAR, "tarih"]).reset_index(drop=True)
    veri["brut_kutu"] = veri["brut_kutu"].fillna(0.0).clip(lower=0.0)
    grup = veri.groupby(ANAHTAR, observed=True)["brut_kutu"]

    for gecikme in (1, 2, 3, 12):
        veri[f"lag_{gecikme}"] = grup.shift(gecikme)
    kaydirilmis = grup.shift(1)
    veri["roll_mean_3"] = kaydirilmis.groupby([veri[k] for k in ANAHTAR], observed=True).transform(
        lambda s: s.rolling(3).mean()
    )
    veri["roll_mean_6"] = kaydirilmis.groupby([veri[k] for k in ANAHTAR], observed=True).transform(
        lambda s: s.rolling(6).mean()
    )
    veri["roll_std_3"] = kaydirilmis.groupby([veri[k] for k in ANAHTAR], observed=True).transform(
        lambda s: s.rolling(3).std()
    )

    veri["ay"] = veri["tarih"].dt.month
    veri["ceyrek"] = veri["tarih"].dt.quarter
    veri["yil_indeksi"] = veri["tarih"].dt.year - int(veri["tarih"].dt.year.min())
    veri["seri_uzunlugu"] = veri.groupby(ANAHTAR, observed=True)["tarih"].transform("size")

    if mf_dahil:
        mf = veri.groupby(ANAHTAR, observed=True)["mf_oran_temiz"]
        veri["mf_lag_0"] = veri["mf_oran_temiz"]
        veri["mf_lag_1"] = mf.shift(1)
        veri["mf_roll_mean_3"] = (
            mf.shift(1)
            .groupby([veri[k] for k in ANAHTAR], observed=True)
            .transform(lambda s: s.rolling(3).mean())
        )
    else:
        veri = veri.drop(columns=[s for s in MF_OZELLIKLERI if s in veri.columns])

    return veri


def lgbm_walk_forward(
    df: pd.DataFrame, mf_dahil: bool = True, ay_sayisi: int = TEST_AYLARI
) -> pd.DataFrame:
    """Global LightGBM'i walk-forward değerlendirir.

    Tek model bütün serileri birlikte öğrenir; kısa seriler eğitim havuzunda kalır
    ama hedef olarak seçilmez (geçmişleri yetersiz). Hedef `log1p` ölçeğinde:
    hacimler pazarlar arası üç mertebe farklı ve log ölçek olmadan büyük serilerin
    kaybı modeli domine eder. Tahmin `expm1` ile geri çevrilip 0'a kırpılır.
    """
    import lightgbm as lgb

    matris = ozellik_matrisi(df, mf_dahil=mf_dahil)
    ozellikler = list(_TEMEL_OZELLIKLER)
    if mf_dahil:
        ozellikler += MF_OZELLIKLERI
    for sutun in _KATEGORIKLER:
        matris[sutun] = matris[sutun].astype("category")

    hedef_tarihler = _hedef_tarihler(matris, ay_sayisi)
    satirlar = []
    for hedef in sorted(hedef_tarihler):
        egitim = matris[matris["tarih"] < hedef]
        test = matris[(matris["tarih"] == hedef) & (matris.index.isin(hedef_tarihler[hedef]))]
        if egitim.empty or test.empty:
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
            egitim[ozellikler + _KATEGORIKLER],
            np.log1p(egitim["brut_kutu"]),
            categorical_feature=_KATEGORIKLER,
        )
        tahmin = np.expm1(model.predict(test[ozellikler + _KATEGORIKLER])).clip(min=0.0)
        satirlar.append(
            pd.DataFrame(
                {
                    "pazar": test["pazar"].astype(str).to_numpy(),
                    "sirket": test["sirket"].astype(str).to_numpy(),
                    "urun": test["urun"].astype(str).to_numpy(),
                    "tarih": test["tarih"].to_numpy(),
                    "gercek": test["brut_kutu"].to_numpy(),
                    "tahmin": tahmin,
                }
            )
        )

    if not satirlar:
        return pd.DataFrame(columns=["pazar", "sirket", "urun", "tarih", "gercek", "tahmin"])
    return (
        pd.concat(satirlar).sort_values(["pazar", "sirket", "urun", "tarih"]).reset_index(drop=True)
    )


def _hedef_tarihler(matris: pd.DataFrame, ay_sayisi: int) -> dict[pd.Timestamp, list[int]]:
    """Hangi ayda hangi satırların tahmin edileceği.

    Temel modellerle **aynı** seri seçimini kullanır ki karşılaştırma adil olsun ve
    ablasyonun iki tarafı aynı katmanlarda değerlendirilsin.
    """
    hedefler: dict[pd.Timestamp, list[int]] = {}
    for _, grup in matris.groupby(ANAHTAR, observed=True):
        sirali = grup.sort_values("tarih")
        if len(sirali) < MIN_EGITIM_AYI + 1:
            continue
        secilen = sirali.iloc[-min(ay_sayisi, len(sirali) - MIN_EGITIM_AYI) :]
        for indeks, tarih in zip(secilen.index, secilen["tarih"], strict=True):
            hedefler.setdefault(tarih, []).append(indeks)
    return hedefler


def mf_ablasyonu(df: pd.DataFrame, ay_sayisi: int = TEST_AYLARI) -> pd.DataFrame:
    """`lgbm` ile `lgbm_no_mf`'i pazar bazında karşılaştırır."""
    mf_ile = pazar_bazinda_metrikler(lgbm_walk_forward(df, mf_dahil=True, ay_sayisi=ay_sayisi))
    mf_siz = pazar_bazinda_metrikler(lgbm_walk_forward(df, mf_dahil=False, ay_sayisi=ay_sayisi))
    birlesik = mf_ile.merge(mf_siz, on="pazar", suffixes=("_mf_ile", "_mf_siz"))
    birlesik["mae_farki"] = birlesik["mae_mf_siz"] - birlesik["mae_mf_ile"]
    birlesik["wape_farki"] = birlesik["wape_mf_siz"] - birlesik["wape_mf_ile"]
    return birlesik
