"""Geniş formatlı satış çalışma kitabını tidy çerçeveye çevirir.

Kaynak sayfa 3 satırlık hiyerarşik başlık taşır (Yıl / Ay / Metrik) ve anahtarlar
ilk üç kolondadır; `pd.read_excel(header=0)` bu yapıyı yanlış okur. Bu modül ham
veriyi sadakatle okur — düzeltmelerin tamamı `clean.py`'nin işidir.
"""

from pathlib import Path

import pandas as pd

# Depo köküne göre mutlak yol: notebook `notebooks/` içinden koşuyor ve göreli bir
# yol oradan çözülmüyordu.
_DEPO_KOKU = Path(__file__).resolve().parents[2]
VERI_YOLU = _DEPO_KOKU / "AI Engineer" / "bolum2_veriseti.xlsx"
ANAHTAR = ["pazar", "sirket", "urun"]

AY_ADLARI = {
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

BEKLENEN_METRIKLER = {"Brüt Kutu", "MF Oran", "Net TL"}
_METRIK_ADLARI = {"Brüt Kutu": "brut_kutu", "MF Oran": "mf_oran", "Net TL": "net_tl"}

_YIL_SATIRI = 1
_AY_SATIRI = 2
_METRIK_SATIRI = 3
_ILK_VERI_SATIRI = 4
_ILK_OLCUM_KOLONU = 3


def yukle_ham(yol: Path = VERI_YOLU) -> pd.DataFrame:
    """Çalışma kitabını okur ve tidy çerçeve döndürür.

    Kolonlar: pazar, sirket, urun, tarih, brut_kutu, mf_oran, net_tl.
    Boş hücreler `NaN` kalır — sıfıra çevrilmez, çünkü ürünün henüz var olmadığı
    dönem ile gerçek sıfır satış farklı şeylerdir (bulgular §2.4).
    """
    ham = pd.read_excel(yol, sheet_name=0, header=None)

    yillar = ham.iloc[_YIL_SATIRI, _ILK_OLCUM_KOLONU:].ffill().astype(int)
    aylar = ham.iloc[_AY_SATIRI, _ILK_OLCUM_KOLONU:].ffill().astype(str).str.strip()
    metrikler = ham.iloc[_METRIK_SATIRI, _ILK_OLCUM_KOLONU:].astype(str).str.strip()

    bilinmeyen_aylar = set(aylar) - set(AY_ADLARI)
    if bilinmeyen_aylar:
        raise ValueError(f"bilinmeyen ay adı: {sorted(bilinmeyen_aylar)}")
    if set(metrikler) != BEKLENEN_METRIKLER:
        raise ValueError(f"beklenmeyen metrik adları: {sorted(set(metrikler))}")

    tarihler = [
        pd.Timestamp(year=yil, month=AY_ADLARI[ay], day=1)
        for yil, ay in zip(yillar, aylar, strict=True)
    ]

    veri = ham.iloc[_ILK_VERI_SATIRI:, :]
    anahtarlar = veri.iloc[:, :_ILK_OLCUM_KOLONU].copy()
    anahtarlar.columns = ANAHTAR

    degerler = veri.iloc[:, _ILK_OLCUM_KOLONU:].apply(pd.to_numeric, errors="coerce")
    degerler.columns = pd.MultiIndex.from_arrays(
        [tarihler, metrikler.tolist()], names=["tarih", "metrik"]
    )
    degerler.index = pd.MultiIndex.from_frame(anahtarlar)

    tidy = degerler.stack("tarih", future_stack=True).reset_index()
    tidy = tidy.rename(columns=_METRIK_ADLARI).rename_axis(columns=None)
    tidy["pazar"] = tidy["pazar"].astype("category")
    tidy["sirket"] = tidy["sirket"].astype("category")
    tidy["urun"] = tidy["urun"].astype(str)

    sirali = [*ANAHTAR, "tarih", "brut_kutu", "mf_oran", "net_tl"]
    return tidy[sirali].sort_values([*ANAHTAR, "tarih"]).reset_index(drop=True)
