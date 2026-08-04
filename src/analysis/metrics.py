"""Türetilmiş satış metrikleri ve analitik ölçüler.

Türetilmiş metrikler case'in tanımlarından gelir:

    Net Kutu    = Brüt Kutu × (1 − MF Oran)
    Birim Fiyat = Net TL / Net Kutu

Birim fiyat hesabı `NaN` üretir, `inf` değil: Net Kutu sıfır veya negatifse fiyat
tanımsızdır ve sonsuz bir değer bütün ortalamaları sessizce zehirlerdi (V8).
"""

import numpy as np
import pandas as pd

SEASONALITY_MIN_MONTHS = 24
_PERIOD = 12


def derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """`net_kutu` ve `birim_fiyat` kolonlarını ekler."""
    result = df.copy()
    result["net_kutu"] = result["brut_kutu"] * (1 - result["mf_oran_temiz"])
    result["birim_fiyat"] = np.where(
        result["net_kutu"] > 0,
        result["net_tl"] / result["net_kutu"].where(result["net_kutu"] > 0),
        np.nan,
    )
    return result


def market_share(df: pd.DataFrame, metric: str = "brut_kutu") -> pd.DataFrame:
    """Pazar-ay bazında şirket payı (%)."""
    totals = df.groupby(["pazar", "tarih", "sirket"], observed=True)[metric].sum().reset_index()
    market_total = totals.groupby(["pazar", "tarih"], observed=True)[metric].transform("sum")
    totals["pay"] = 100.0 * totals[metric] / market_total
    return totals


def hhi(df: pd.DataFrame, metric: str = "brut_kutu") -> pd.DataFrame:
    """Herfindahl-Hirschman endeksi (0–10.000) — pazar-ay bazında yoğunlaşma."""
    shares = market_share(df, metric)
    result = shares.groupby(["pazar", "tarih"], observed=True)["pay"].apply(
        lambda p: float((p**2).sum())
    )
    return result.rename("hhi").reset_index()


def yoy_growth(df: pd.DataFrame, metric: str = "brut_kutu") -> pd.DataFrame:
    """Pazar-şirket-yıl bazında yıllık büyüme (%)."""
    yearly = df.copy()
    yearly["yil"] = yearly["tarih"].dt.year
    totals = yearly.groupby(["pazar", "sirket", "yil"], observed=True)[metric].sum().reset_index()
    totals = totals.sort_values(["pazar", "sirket", "yil"])
    previous = totals.groupby(["pazar", "sirket"], observed=True)[metric].shift(1)
    totals["buyume"] = np.where(
        previous > 0, 100.0 * (totals[metric] - previous) / previous, np.nan
    )
    return totals


def seasonal_index(series: pd.Series) -> pd.Series | None:
    """Ay bazında mevsimsel çarpan (ortalama 1,0 civarı). Kısa seride `None`.

    STL kullanılır (`robust=True`): veride promosyon kaynaklı sıçramalar var ve
    klasik ayrıştırma onlara aşırı tepki verip mevsimselliği çarpıtıyor. 24 aydan
    kısa serilerde hesap **yapılmaz** — 12 aylık döngünün en az iki tekrarı gerekir,
    yoksa uydurulmuş bir mevsimsellik raporlanır (V9).
    """
    components = _stl_components(series)
    if components is None:
        return None
    seasonal = components.seasonal
    mean = series.mean()
    if not np.isfinite(mean) or mean == 0:
        return None
    index = (seasonal + mean) / mean
    return index.groupby(index.index.month).mean().rename_axis("ay")


def seasonality_strength(series: pd.Series) -> float | None:
    """Hyndman mevsimsellik gücü: `max(0, 1 − Var(kalan) / Var(kalan + mevsimsel))`."""
    components = _stl_components(series)
    if components is None:
        return None
    residual = components.resid
    total = residual + components.seasonal
    if total.var() == 0:
        return 0.0
    return float(max(0.0, 1.0 - residual.var() / total.var()))


def _stl_components(series: pd.Series):
    """STL ayrıştırması; bilgilendirici geçmiş yetersizse `None`.

    Eşik **satış görülen ay** sayısına bakar, satır sayısına değil. Fark ölçüldü:
    `C Pazarı/Ürün 1` kırpma sonrası 28 satır taşıyor ama yalnız bir ayında satış
    var; satır sayısına bakan bir eşik bunu kabul ediyor ve STL o tek sıçramayı
    mevsimsellik olarak raporluyordu (güç 0,987, zirve indeksi 8,72). Uydurulmuş
    mevsimsellik, "hesaplanamadı" demekten daha kötüdür.
    """
    from statsmodels.tsa.seasonal import STL

    clean_series = series.dropna()
    months_with_sales = int((clean_series > 0).sum())
    if len(clean_series) < SEASONALITY_MIN_MONTHS or months_with_sales < SEASONALITY_MIN_MONTHS:
        return None
    if clean_series.nunique() <= 1:
        return None
    return STL(clean_series, period=_PERIOD, robust=True).fit()


def promo_revenue_loss(df: pd.DataFrame) -> pd.DataFrame:
    """Bedava verilen kutuların TL karşılığı — yıl × pazar × ürün toplamı."""
    result = df.copy()
    result["bedava_kutu"] = result["brut_kutu"] * result["mf_oran_temiz"]
    result["gelir_kaybi_tl"] = result["bedava_kutu"] * result["birim_fiyat"]
    result["yil"] = result["tarih"].dt.year
    return (
        result.groupby(["yil", "pazar", "urun"], observed=True)["gelir_kaybi_tl"]
        .sum()
        .reset_index()
    )


def price_dispersion(df: pd.DataFrame) -> pd.DataFrame:
    """Aynı ürünün pazarlar arası fiyat varyasyon katsayısı (CV).

    Anahtar `urun` değil `(pazar, urun)`; `Ürün-A` birden fazla şirkette geçtiği için
    ortalama önce pazar-ürün bazında alınır (V6).
    """
    per_market = df.groupby(["urun", "pazar"], observed=True)["birim_fiyat"].mean().reset_index()
    summary = per_market.groupby("urun", observed=True)["birim_fiyat"].agg(["mean", "std", "count"])
    summary["cv"] = np.where(
        summary["mean"] > 0, summary["std"].fillna(0.0) / summary["mean"], np.nan
    )
    return summary.reset_index()
