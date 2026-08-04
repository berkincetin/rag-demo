"""Geniş formatlı satış çalışma kitabını tidy çerçeveye çevirir.

Kaynak sayfa 3 satırlık hiyerarşik başlık taşır (Yıl / Ay / Metrik) ve anahtarlar
ilk üç kolondadır; `pd.read_excel(header=0)` bu yapıyı yanlış okur. Bu modül ham
veriyi sadakatle okur — düzeltmelerin tamamı `clean.py`'nin işidir.

DataFrame kolon adları bilinçli olarak Türkçe: kaynak Excel başlıkları (`Brüt Kutu`,
`MF Oran`, `Net TL`) Türkçe ve bu ad eşlemesi veriye izlenebilirliği koruyor.
"""

from pathlib import Path

import pandas as pd

# Depo köküne göre mutlak yol: notebook `notebooks/` içinden koşuyor ve göreli bir
# yol oradan çözülmüyordu.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = _REPO_ROOT / "AI Engineer" / "bolum2_veriseti.xlsx"
KEY = ["pazar", "sirket", "urun"]

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


def load_raw(path: Path = DATA_PATH) -> pd.DataFrame:
    """Çalışma kitabını okur ve tidy çerçeve döndürür.

    Kolonlar: pazar, sirket, urun, tarih, brut_kutu, mf_oran, net_tl.
    Boş hücreler `NaN` kalır — sıfıra çevrilmez, çünkü ürünün henüz var olmadığı
    dönem ile gerçek sıfır satış farklı şeylerdir (bulgular §2.4).
    """
    raw = pd.read_excel(path, sheet_name=0, header=None)

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
