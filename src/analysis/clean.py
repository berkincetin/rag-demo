"""Ölçülmüş yedi veri kalitesi sorununu düzelten temizleme boru hattı.

Her adım hem veriyi değiştirir hem de ne yaptığını sayar; `DataQualityReport`
notebook'un açılışında olduğu gibi yayımlanır. Hiçbir kayıt sessizce silinmez.

🚨 En kritik adım MF ölçek düzeltmesidir (`detect_mf_scale`). `MF Oran` kolonu
B Pazarı'nda yüzde (0–100), diğerlerinde oran (0–1) ölçeğindedir. Düzeltme
yapılmazsa `Net Kutu = Brüt × (1 − MF)` negatife düşer, birim fiyat 8,32 TL yerine
−0,88 TL çıkar ve A4, A6, A7 görevlerinin tamamı yanlış olur (bulgular §2.3).
"""

from dataclasses import dataclass, field

import pandas as pd

from src.analysis.load import KEY

MF_LOWER = 0.0
MF_UPPER = 0.95
SHORT_SERIES_THRESHOLD = 24


@dataclass
class DataQualityReport:
    """Temizlemenin ne yaptığının sayısal dökümü."""

    raw_rows: int = 0
    clean_rows: int = 0
    rescaled_markets: dict[str, float] = field(default_factory=dict)
    mf_clipped: int = 0
    return_rows: int = 0
    pre_launch_dropped: int = 0
    short_series: dict[tuple[str, str, str], int] = field(default_factory=dict)


def detect_mf_scale(df: pd.DataFrame) -> dict[str, float]:
    """Her pazar için MF biriminin ölçek faktörünü döndürür (1.0 veya 100.0).

    Kural veriden çıkar, pazar adından değil: pozitif MF değerlerinin medyanı 1'i
    aşıyorsa o pazar yüzde ölçeğindedir. Sıfırlar medyana katılmaz — MF'in çoğu ayda
    0 olduğu bir seride sıfırlar medyanı 0'a çeker ve ölçek sorunu gözden kaçardı.
    """
    factors: dict[str, float] = {}
    for market, group in df.groupby("pazar", observed=True):
        positive = group.loc[group["mf_oran"].notna() & (group["mf_oran"] > 0), "mf_oran"]
        median = positive.median()
        factors[str(market)] = 100.0 if pd.notna(median) and median > 1 else 1.0
    return factors


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, DataQualityReport]:
    """Yedi düzeltmeyi sırayla uygular ve kalite raporuyla birlikte döndürür."""
    report = DataQualityReport(raw_rows=len(df))
    result = df.copy()

    # V7 — ürün adı normalizasyonu. Ölçek tespitinden önce gelir ki gruplama doğru olsun.
    result["urun"] = result["urun"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    # V2 — 🚨 MF ölçek düzeltmesi.
    factors = detect_mf_scale(result)
    report.rescaled_markets = {m: f for m, f in factors.items() if f != 1.0}
    divisor = result["pazar"].astype(str).map(factors)
    result["mf_oran_olcekli"] = result["mf_oran"] / divisor

    # V3 — ölçek düzeltmesinden sonra bile kalan imkânsız değerleri kırp ve bayrakla.
    result["mf_kirpildi"] = result["mf_oran_olcekli"].notna() & (
        (result["mf_oran_olcekli"] < MF_LOWER) | (result["mf_oran_olcekli"] > MF_UPPER)
    )
    result["mf_oran_temiz"] = result["mf_oran_olcekli"].clip(MF_LOWER, MF_UPPER)
    report.mf_clipped = int(result["mf_kirpildi"].sum())

    # V4 — iadeler. Silinmez; toplamlarda kalır, tahmin girdisinde 0'lanır.
    result["iade_mi"] = (result["brut_kutu"] < 0) | (result["net_tl"] < 0)
    report.return_rows = int(result["iade_mi"].sum())

    # V5 — serinin ilk pozitif satışından önceki dönem ürünün var olmadığı dönemdir.
    before = len(result)
    first_sale = result[result["brut_kutu"] > 0].groupby(KEY, observed=True)["tarih"].min()
    key_index = pd.MultiIndex.from_frame(result[KEY].astype(str))
    launch = pd.Series(
        key_index.map(first_sale.rename_axis(first_sale.index.names)), index=result.index
    )
    result = result[launch.notna() & (result["tarih"] >= launch)]
    report.pre_launch_dropped = before - len(result)

    result = result.reset_index(drop=True)
    report.clean_rows = len(result)
    report.short_series = _short_series(result)
    return result, report


def _short_series(df: pd.DataFrame) -> dict[tuple[str, str, str], int]:
    """Mevsimsellik ve tahmin için yetersiz uzunluktaki seriler (V9).

    Uzunluk ölçüsü **satış görülen ay sayısı**dır, satır sayısı değil. Fark önemli:
    `C Pazarı/Ürün 1` kırpma sonrası 27 satır taşır ama bunların yalnız biri pozitif
    (2024-01'de 1 kutu), gerisi gerçek sıfır. Satır sayısıyla ölçülseydi seri
    "27 aylık geçmişi var" görünür ve mevsimsellik/tahmin için uygun sanılırdı.
    Bulgular §2.5'teki ölçülen değerler de bu tanımla uyumlu: C/Ürün 1 → 1,
    D/Ürün 78 → 11.

    Bu seriler analizden **çıkarılmaz**; raporda listelenir ki notebook onları
    gizlemek yerine açıkça "yetersiz veri" diye gösterebilsin.
    """
    if df.empty:
        return {}
    with_sales = df[df["brut_kutu"] > 0].groupby(KEY, observed=True).size()
    return {
        tuple(map(str, key)): int(n) for key, n in with_sales.items() if n < SHORT_SERIES_THRESHOLD
    }
