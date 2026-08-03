"""Türetilmiş satış metrikleri ve analitik ölçüler.

Türetilmiş metrikler case'in tanımlarından gelir:

    Net Kutu    = Brüt Kutu × (1 − MF Oran)
    Birim Fiyat = Net TL / Net Kutu

Birim fiyat hesabı `NaN` üretir, `inf` değil: Net Kutu sıfır veya negatifse fiyat
tanımsızdır ve sonsuz bir değer bütün ortalamaları sessizce zehirlerdi (V8).
"""

import numpy as np
import pandas as pd

from src.analysis.load import ANAHTAR

MEVSIMSELLIK_MIN_AY = 24
_PERIYOT = 12


def turetilmis_metrikler(df: pd.DataFrame) -> pd.DataFrame:
    """`net_kutu` ve `birim_fiyat` kolonlarını ekler."""
    sonuc = df.copy()
    sonuc["net_kutu"] = sonuc["brut_kutu"] * (1 - sonuc["mf_oran_temiz"])
    sonuc["birim_fiyat"] = np.where(
        sonuc["net_kutu"] > 0,
        sonuc["net_tl"] / sonuc["net_kutu"].where(sonuc["net_kutu"] > 0),
        np.nan,
    )
    return sonuc


def pazar_payi(df: pd.DataFrame, metrik: str = "brut_kutu") -> pd.DataFrame:
    """Pazar-ay bazında şirket payı (%)."""
    toplam = df.groupby(["pazar", "tarih", "sirket"], observed=True)[metrik].sum().reset_index()
    pazar_toplami = toplam.groupby(["pazar", "tarih"], observed=True)[metrik].transform("sum")
    toplam["pay"] = 100.0 * toplam[metrik] / pazar_toplami
    return toplam


def hhi(df: pd.DataFrame, metrik: str = "brut_kutu") -> pd.DataFrame:
    """Herfindahl-Hirschman endeksi (0–10.000) — pazar-ay bazında yoğunlaşma."""
    paylar = pazar_payi(df, metrik)
    sonuc = paylar.groupby(["pazar", "tarih"], observed=True)["pay"].apply(
        lambda p: float((p**2).sum())
    )
    return sonuc.rename("hhi").reset_index()


def yillik_buyume(df: pd.DataFrame, metrik: str = "brut_kutu") -> pd.DataFrame:
    """Pazar-şirket-yıl bazında yıllık büyüme (%)."""
    yillik = df.copy()
    yillik["yil"] = yillik["tarih"].dt.year
    toplam = yillik.groupby(["pazar", "sirket", "yil"], observed=True)[metrik].sum().reset_index()
    toplam = toplam.sort_values(["pazar", "sirket", "yil"])
    onceki = toplam.groupby(["pazar", "sirket"], observed=True)[metrik].shift(1)
    toplam["buyume"] = np.where(onceki > 0, 100.0 * (toplam[metrik] - onceki) / onceki, np.nan)
    return toplam


def mevsimsel_indeks(seri: pd.Series) -> pd.Series | None:
    """Ay bazında mevsimsel çarpan (ortalama 1,0 civarı). Kısa seride `None`.

    STL kullanılır (`robust=True`): veride promosyon kaynaklı sıçramalar var ve
    klasik ayrıştırma onlara aşırı tepki verip mevsimselliği çarpıtıyor. 24 aydan
    kısa serilerde hesap **yapılmaz** — 12 aylık döngünün en az iki tekrarı gerekir,
    yoksa uydurulmuş bir mevsimsellik raporlanır (V9).
    """
    bileşen = _stl_bileseni(seri)
    if bileşen is None:
        return None
    mevsimsel = bileşen.seasonal
    ortalama = seri.mean()
    if not np.isfinite(ortalama) or ortalama == 0:
        return None
    indeks = (mevsimsel + ortalama) / ortalama
    return indeks.groupby(indeks.index.month).mean().rename_axis("ay")


def mevsimsellik_gucu(seri: pd.Series) -> float | None:
    """Hyndman mevsimsellik gücü: `max(0, 1 − Var(kalan) / Var(kalan + mevsimsel))`."""
    bileşen = _stl_bileseni(seri)
    if bileşen is None:
        return None
    kalan = bileşen.resid
    toplam = kalan + bileşen.seasonal
    if toplam.var() == 0:
        return 0.0
    return float(max(0.0, 1.0 - kalan.var() / toplam.var()))


def _stl_bileseni(seri: pd.Series):
    """STL ayrıştırması; bilgilendirici geçmiş yetersizse `None`.

    Eşik **satış görülen ay** sayısına bakar, satır sayısına değil. Fark ölçüldü:
    `C Pazarı/Ürün 1` kırpma sonrası 28 satır taşıyor ama yalnız bir ayında satış
    var; satır sayısına bakan bir eşik bunu kabul ediyor ve STL o tek sıçramayı
    mevsimsellik olarak raporluyordu (güç 0,987, zirve indeksi 8,72). Uydurulmuş
    mevsimsellik, "hesaplanamadı" demekten daha kötüdür.
    """
    from statsmodels.tsa.seasonal import STL

    temiz = seri.dropna()
    satisli_ay = int((temiz > 0).sum())
    if len(temiz) < MEVSIMSELLIK_MIN_AY or satisli_ay < MEVSIMSELLIK_MIN_AY:
        return None
    if temiz.nunique() <= 1:
        return None
    return STL(temiz, period=_PERIYOT, robust=True).fit()


def promosyon_gelir_kaybi(df: pd.DataFrame) -> pd.DataFrame:
    """Bedava verilen kutuların TL karşılığı — yıl × pazar × ürün toplamı."""
    hesap = df.copy()
    hesap["bedava_kutu"] = hesap["brut_kutu"] * hesap["mf_oran_temiz"]
    hesap["gelir_kaybi_tl"] = hesap["bedava_kutu"] * hesap["birim_fiyat"]
    hesap["yil"] = hesap["tarih"].dt.year
    return (
        hesap.groupby(["yil", "pazar", "urun"], observed=True)["gelir_kaybi_tl"].sum().reset_index()
    )


def fiyat_sapmasi(df: pd.DataFrame) -> pd.DataFrame:
    """Aynı ürünün pazarlar arası fiyat varyasyon katsayısı (CV).

    Anahtar `urun` değil `(pazar, urun)`; `Ürün-A` birden fazla şirkette geçtiği için
    ortalama önce pazar-ürün bazında alınır (V6).
    """
    pazar_ortalamasi = (
        df.groupby(["urun", "pazar"], observed=True)["birim_fiyat"].mean().reset_index()
    )
    ozet = pazar_ortalamasi.groupby("urun", observed=True)["birim_fiyat"].agg(
        ["mean", "std", "count"]
    )
    ozet["cv"] = np.where(ozet["mean"] > 0, ozet["std"].fillna(0.0) / ozet["mean"], np.nan)
    return ozet.reset_index()


__all__ = [
    "ANAHTAR",
    "fiyat_sapmasi",
    "hhi",
    "mevsimsel_indeks",
    "mevsimsellik_gucu",
    "pazar_payi",
    "promosyon_gelir_kaybi",
    "turetilmis_metrikler",
    "yillik_buyume",
]
