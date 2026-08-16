"""Build notebooks/analiz_full.ipynb — a standalone version of analiz.ipynb.

Everything `src/analysis/` provides is inlined as notebook cells, so the file
runs with no project modules on the path. The analysis cells are copied from
analiz.ipynb verbatim, minus the two bootstrap cells (sys.path + imports),
which are replaced by a pip install cell and the inlined function definitions.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "notebooks" / "analiz.ipynb"
OUT = ROOT / "notebooks" / "analiz_full.ipynb"


def _lines(text: str) -> list[str]:
    """nbformat source lines: every line but the last keeps its newline."""
    return text.strip("\n").splitlines(keepends=True)


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _lines(text),
    }


def _joined(cell: dict) -> str:
    return "".join(cell["source"])


# --- the new opening cells ---------------------------------------------------

INTRO = """
# Bölüm 2 — İlaç Sektörü Satış ve Talep Analizi (tek dosya sürümü)

Dört pazar (A, B, C, D) × 124 ay (2016-01 → 2026-04) satış verisi üzerinde case'in
yedi analiz sorusu.

> 📦 **Bu notebook kendi kendine yeterlidir.** `src/analysis/` altındaki beş modülün
> (`load`, `clean`, `metrics`, `forecast`, `plots`) tamamı aşağıya fonksiyon olarak
> yazıldı; hiçbir proje modülü import edilmiyor. Tek gereken veri dosyası
> `bolum2_veriseti.xlsx`.

Her görevin altında iki ayrı yorum var: **Teknik yorum** (yöntem, sınırlılık,
istatistiksel güven) ve **İş yorumu** (ne yapılmalı).

> ⚠️ **Önce okunması gereken:** `MF Oran` kolonu B Pazarı'nda yüzde (0–100),
> diğer pazarlarda oran (0–1) ölçeğinde. Düzeltilmezse `Net Kutu = Brüt × (1 − MF)`
> negatife düşüyor ve birim fiyat 8,32 TL yerine **−0,88 TL** çıkıyor. A4, A6 ve A7
> bu düzeltme olmadan tamamen yanlış olurdu. Düzeltme sabit "B Pazarı" kuralıyla
> değil, **grup medyanına bakan program tespitiyle** yapılıyor.
"""

INSTALL_MD = """
---
## 0. Kurulum ve veri yolu

Aşağıdaki hücre gerekli kütüphaneleri kurar. Sürümler kurulu ortamdan (`pip freeze`)
birebir alındı, tahmin edilmedi.
"""

INSTALL_CODE = """
# Gerekli kütüphaneler. Ortamda zaten varsa pip bunları atlar.
%pip install --quiet \\
    "pandas==2.2.3" \\
    "numpy==2.2.6" \\
    "openpyxl==3.1.5" \\
    "matplotlib==3.10.9" \\
    "statsmodels==0.14.6" \\
    "scipy==1.15.3" \\
    "scikit-learn==1.7.2" \\
    "lightgbm==4.7.0"

print("Kurulum tamam.")
"""

DATA_PATH_CODE = """
# Veri dosyasının yeri. Notebook ile aynı klasörde ya da bir üstünde aranır;
# bulunamazsa DATA_PATH'i elle yazın.
from pathlib import Path

_CANDIDATES = [
    Path("bolum2_veriseti.xlsx"),
    Path("veri") / "bolum2_veriseti.xlsx",
    Path("..") / "bolum2_veriseti.xlsx",
    Path("..") / "AI Engineer" / "bolum2_veriseti.xlsx",
    Path("AI Engineer") / "bolum2_veriseti.xlsx",
]
DATA_PATH = next((p for p in _CANDIDATES if p.exists()), None)

if DATA_PATH is None:
    raise FileNotFoundError(
        "bolum2_veriseti.xlsx bulunamadı. Aranan yerler:\\n  "
        + "\\n  ".join(str(p.resolve()) for p in _CANDIDATES)
        + "\\n\\nDosyayı bu notebook'un yanına koyun ya da DATA_PATH'i elle atayın."
    )

# Figürler buraya yazılır.
FIGURE_DIR = Path("figures")
print(f"Veri : {DATA_PATH.resolve()}")
print(f"Figür: {FIGURE_DIR.resolve()}")
"""

FUNCS_MD = """
---
## 0.1 Analiz fonksiyonları

`src/analysis/` altındaki beş modülün tamamı burada. Sırasıyla: yükleme (`load`),
temizleme (`clean`), türetilmiş metrikler (`metrics`), tahmin (`forecast`) ve
grafik stili (`plots`).
"""

IMPORTS_CODE = """
import warnings
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 40)

MARKETS = ["A Pazarı", "B Pazarı", "C Pazarı", "D Pazarı"]
KEY = ["pazar", "sirket", "urun"]
"""

# --- inlined modules ---------------------------------------------------------

LOAD_CODE = '''
# ============================================================================
# src/analysis/load.py — geniş formatlı çalışma kitabını tidy çerçeveye çevirir
# ============================================================================
# Kaynak sayfa 3 satırlık hiyerarşik başlık taşır (Yıl / Ay / Metrik) ve anahtarlar
# ilk üç kolondadır; `pd.read_excel(header=0)` bu yapıyı yanlış okur. Bu bölüm ham
# veriyi sadakatle okur — düzeltmelerin tamamı temizleme adımının işidir.
#
# DataFrame kolon adları bilinçli olarak Türkçe: kaynak Excel başlıkları
# (`Brüt Kutu`, `MF Oran`, `Net TL`) Türkçe ve bu ad eşlemesi veriye
# izlenebilirliği koruyor.

MONTH_NAMES = {
    "Ocak": 1,
    "Şubat": 2,
    "Mart": 3,
    "Nisan": 4,
    "Mayıs": 5,
    "Haziran": 6,
    "Temmuz": 7,
    "Ağustos": 8,
    "Eylül": 9,
    "Ekim": 10,
    "Kasım": 11,
    "Aralık": 12,
}

EXPECTED_METRICS = {"Brüt Kutu", "MF Oran", "Net TL"}
_METRIC_COLUMNS = {"Brüt Kutu": "brut_kutu", "MF Oran": "mf_oran", "Net TL": "net_tl"}

_YEAR_ROW = 1
_MONTH_ROW = 2
_METRIC_ROW = 3
_FIRST_DATA_ROW = 4
_FIRST_VALUE_COL = 3


def load_raw(path=None) -> pd.DataFrame:
    """Çalışma kitabını okur ve tidy çerçeve döndürür.

    Kolonlar: pazar, sirket, urun, tarih, brut_kutu, mf_oran, net_tl.
    Boş hücreler `NaN` kalır — sıfıra çevrilmez, çünkü ürünün henüz var olmadığı
    dönem ile gerçek sıfır satış farklı şeylerdir (bulgular §2.4).
    """
    raw = pd.read_excel(DATA_PATH if path is None else path, sheet_name=0, header=None)

    years = raw.iloc[_YEAR_ROW, _FIRST_VALUE_COL:].ffill().astype(int)
    months = raw.iloc[_MONTH_ROW, _FIRST_VALUE_COL:].ffill().astype(str).str.strip()
    metrics = raw.iloc[_METRIC_ROW, _FIRST_VALUE_COL:].astype(str).str.strip()

    unknown_months = set(months) - set(MONTH_NAMES)
    if unknown_months:
        raise ValueError(f"bilinmeyen ay adı: {sorted(unknown_months)}")
    if set(metrics) != EXPECTED_METRICS:
        raise ValueError(f"beklenmeyen metrik adları: {sorted(set(metrics))}")

    dates = [
        pd.Timestamp(year=year, month=MONTH_NAMES[month], day=1)
        for year, month in zip(years, months, strict=True)
    ]

    body = raw.iloc[_FIRST_DATA_ROW:, :]
    keys = body.iloc[:, :_FIRST_VALUE_COL].copy()
    keys.columns = KEY

    values = body.iloc[:, _FIRST_VALUE_COL:].apply(pd.to_numeric, errors="coerce")
    values.columns = pd.MultiIndex.from_arrays([dates, metrics.tolist()], names=["tarih", "metrik"])
    values.index = pd.MultiIndex.from_frame(keys)

    tidy = values.stack("tarih", future_stack=True).reset_index()
    tidy = tidy.rename(columns=_METRIC_COLUMNS).rename_axis(columns=None)
    tidy["pazar"] = tidy["pazar"].astype("category")
    tidy["sirket"] = tidy["sirket"].astype("category")
    tidy["urun"] = tidy["urun"].astype(str)

    ordered = [*KEY, "tarih", "brut_kutu", "mf_oran", "net_tl"]
    return tidy[ordered].sort_values([*KEY, "tarih"]).reset_index(drop=True)
'''

CLEAN_CODE = '''
# ============================================================================
# src/analysis/clean.py — ölçülmüş yedi veri kalitesi sorununu düzeltir
# ============================================================================
# Her adım hem veriyi değiştirir hem de ne yaptığını sayar; `DataQualityReport`
# notebook'un açılışında yayımlanır. Hiçbir kayıt sessizce silinmez.
#
# 🚨 En kritik adım MF ölçek düzeltmesidir (`detect_mf_scale`). `MF Oran` kolonu
# B Pazarı'nda yüzde (0–100), diğerlerinde oran (0–1) ölçeğindedir. Düzeltme
# yapılmazsa `Net Kutu = Brüt × (1 − MF)` negatife düşer, birim fiyat 8,32 TL
# yerine −0,88 TL çıkar ve A4, A6, A7 görevlerinin tamamı yanlış olur.

MF_LOWER = 0.0
MF_UPPER = 0.95
SHORT_SERIES_THRESHOLD = 24


@dataclass
class DataQualityReport:
    """Temizlemenin ne yaptığının sayısal dökümü."""

    raw_rows: int = 0
    clean_rows: int = 0
    rescaled_markets: dict = field(default_factory=dict)
    mf_clipped: int = 0
    return_rows: int = 0
    pre_launch_dropped: int = 0
    short_series: dict = field(default_factory=dict)


def detect_mf_scale(df: pd.DataFrame) -> dict:
    """Her pazar için MF biriminin ölçek faktörünü döndürür (1.0 veya 100.0).

    Kural veriden çıkar, pazar adından değil: pozitif MF değerlerinin medyanı 1'i
    aşıyorsa o pazar yüzde ölçeğindedir. Sıfırlar medyana katılmaz — MF'in çoğu ayda
    0 olduğu bir seride sıfırlar medyanı 0'a çeker ve ölçek sorunu gözden kaçardı.
    """
    factors = {}
    for market, group in df.groupby("pazar", observed=True):
        positive = group.loc[group["mf_oran"].notna() & (group["mf_oran"] > 0), "mf_oran"]
        median = positive.median()
        factors[str(market)] = 100.0 if pd.notna(median) and median > 1 else 1.0
    return factors


def clean(df: pd.DataFrame):
    """Yedi düzeltmeyi sırayla uygular ve kalite raporuyla birlikte döndürür."""
    report = DataQualityReport(raw_rows=len(df))
    result = df.copy()

    # V7 — ürün adı normalizasyonu. Ölçek tespitinden önce gelir ki gruplama doğru olsun.
    result["urun"] = result["urun"].astype(str).str.replace(r"\\s+", " ", regex=True).str.strip()

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


def _short_series(df: pd.DataFrame) -> dict:
    """Mevsimsellik ve tahmin için yetersiz uzunluktaki seriler (V9).

    Uzunluk ölçüsü **satış görülen ay sayısı**dır, satır sayısı değil. Fark önemli:
    `C Pazarı/Ürün 1` kırpma sonrası 27 satır taşır ama bunların yalnız biri pozitif
    (2024-01'de 1 kutu), gerisi gerçek sıfır. Satır sayısıyla ölçülseydi seri
    "27 aylık geçmişi var" görünür ve mevsimsellik/tahmin için uygun sanılırdı.

    Bu seriler analizden **çıkarılmaz**; raporda listelenir ki notebook onları
    gizlemek yerine açıkça "yetersiz veri" diye gösterebilsin.
    """
    if df.empty:
        return {}
    with_sales = df[df["brut_kutu"] > 0].groupby(KEY, observed=True).size()
    return {
        tuple(map(str, key)): int(n) for key, n in with_sales.items() if n < SHORT_SERIES_THRESHOLD
    }
'''

METRICS_CODE = '''
# ============================================================================
# src/analysis/metrics.py — türetilmiş satış metrikleri ve analitik ölçüler
# ============================================================================
# Türetilmiş metrikler case'in tanımlarından gelir:
#
#     Net Kutu    = Brüt Kutu × (1 − MF Oran)
#     Birim Fiyat = Net TL / Net Kutu
#
# Birim fiyat hesabı `NaN` üretir, `inf` değil: Net Kutu sıfır veya negatifse fiyat
# tanımsızdır ve sonsuz bir değer bütün ortalamaları sessizce zehirlerdi (V8).

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


def seasonal_index(series: pd.Series):
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


def seasonality_strength(series: pd.Series):
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
'''

FORECAST_CODE = '''
# ============================================================================
# src/analysis/forecast.py — temel modeller ve walk-forward değerlendirme
# ============================================================================
# Değerlendirme genişleyen pencereli walk-forward'dır: son 12 ay tek tek tahmin
# edilir ve her adımda model yalnız o ana kadarki geçmişi görür. Zaman serisinde tek
# bir train/test bölmesi yanıltıcıdır — tek bir aya denk gelen şans, modelin
# sıralamasını değiştirebilir.
#
# MAPE case'in istediği metrik ama sıfıra yakın gerçek değerlerde patlar; bu veride
# 9.536 sıfır aylık gözlem var. Bu yüzden MAPE yalnız `y > 0` gözlemlerde hesaplanır
# ve yanına sıfır-dayanıklı WAPE ile sMAPE konur (V10).

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


def walk_forward(df: pd.DataFrame, forecaster, months: int = TEST_MONTHS) -> pd.DataFrame:
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


def error_metrics(actual, predicted) -> dict:
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
    # yinelenen etiket bırakmış olabilir. Yinelenen etiket, hedef olmaması gereken
    # kısa bir seriyi tahmin setine sızdırıyordu — testle yakalandı.
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


def _target_dates(matrix: pd.DataFrame, months: int) -> dict:
    """Hangi ayda hangi satırların tahmin edileceği.

    Temel modellerle **aynı** seri seçimini kullanır ki karşılaştırma adil olsun ve
    ablasyonun iki tarafı aynı katmanlarda değerlendirilsin.
    """
    targets = {}
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
'''

PLOTS_CODE = '''
# ============================================================================
# src/analysis/plots.py — ortak grafik stili, Türkçe sayı biçimi, PNG yazıcı
# ============================================================================
# Her grafik buradan geçer ki dört pazarın rengi her figürde aynı olsun ve sayılar
# Türkçe biçimde (binlik nokta, ondalık virgül) yazılsın.

MARKET_COLORS = {
    "A Pazarı": "#1f77b4",
    "B Pazarı": "#d62728",
    "C Pazarı": "#2ca02c",
    "D Pazarı": "#9467bd",
}

# Şirket 1 analizin öznesi olduğu için vurgulu; rakipler kasıtlı olarak nötr.
COMPANY_COLORS = {
    "Şirket 1": "#d62728",
    "Şirket 2": "#7f7f7f",
    "Diğer Şirket": "#c7c7c7",
}


def apply_style() -> None:
    """Notebook genelinde geçerli matplotlib ayarlarını kurar."""
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "figure.figsize": (11, 5),
            "axes.grid": True,
            "grid.alpha": 0.3,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.frameon": False,
            "font.size": 10,
        }
    )


def tr_number(x: float, decimals: int = 0) -> str:
    """Türkçe sayı biçimi: binlik ayracı nokta, ondalık ayracı virgül."""
    text = f"{x:,.{decimals}f}"
    return text.replace(",", "\\x00").replace(".", ",").replace("\\x00", ".")


def save_figure(fig, name: str, directory=None):
    """Figürü PNG olarak yazar ve yolunu döndürür."""
    directory = Path(FIGURE_DIR if directory is None else directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    return path


apply_style()
print("Analiz fonksiyonları hazır.")
'''


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    original = source["cells"]

    # Cell 0 = title, cell 1 = executive summary, cells 2-3 = bootstrap
    # (sys.path + project imports). Everything from cell 4 on is the analysis.
    bootstrap = _joined(original[2]) + _joined(original[3])
    if "src.analysis" not in bootstrap:
        raise SystemExit("beklenen bootstrap hücreleri bulunamadı — kaynak notebook değişmiş")

    cells = [
        md(INTRO),
        original[1],  # executive summary, unchanged
        md(INSTALL_MD),
        code(INSTALL_CODE),
        code(DATA_PATH_CODE),
        md(FUNCS_MD),
        code(IMPORTS_CODE),
        code(LOAD_CODE),
        code(CLEAN_CODE),
        code(METRICS_CODE),
        code(FORECAST_CODE),
        code(PLOTS_CODE),
        *original[4:],  # the analysis, verbatim
    ]

    # nbformat >= 4.5 requires a unique cell id; without one Jupyter emits a
    # MissingIDFieldWarning on every open. Assigned by position rather than
    # kept, because cells copied from the source would collide.
    for position, cell in enumerate(cells):
        cell["id"] = f"cell-{position:03d}"
        cell.pop("attachments", None)
        # Ship unexecuted: outputs are regenerated by Restart & Run All, and
        # stale counters from the source notebook would be misleading.
        if cell["cell_type"] == "code":
            cell["execution_count"] = None
            cell["outputs"] = []

    notebook = {
        "cells": cells,
        "metadata": source.get("metadata", {}),
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")

    n_code = sum(1 for c in cells if c["cell_type"] == "code")
    print(f"{OUT.name}: {len(cells)} hücre ({n_code} kod, {len(cells) - n_code} markdown)")
    print(f"kaynaktan alınan analiz hücresi: {len(original[4:])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
