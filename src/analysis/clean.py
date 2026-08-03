"""Ölçülmüş yedi veri kalitesi sorununu düzelten temizleme boru hattı.

Her adım hem veriyi değiştirir hem de ne yaptığını sayar; `VeriKalitesiRaporu`
notebook'un açılışında olduğu gibi yayımlanır. Hiçbir kayıt sessizce silinmez.

🚨 En kritik adım MF ölçek düzeltmesidir (`mf_olcek_tespit`). `MF Oran` kolonu
B Pazarı'nda yüzde (0–100), diğerlerinde oran (0–1) ölçeğindedir. Düzeltme
yapılmazsa `Net Kutu = Brüt × (1 − MF)` negatife düşer, birim fiyat 8,32 TL yerine
−0,88 TL çıkar ve A4, A6, A7 görevlerinin tamamı yanlış olur (bulgular §2.3).
"""

from dataclasses import dataclass, field

import pandas as pd

from src.analysis.load import ANAHTAR

MF_ALT_SINIR = 0.0
MF_UST_SINIR = 0.95
KISA_SERI_ESIGI = 24


@dataclass
class VeriKalitesiRaporu:
    """Temizlemenin ne yaptığının sayısal dökümü."""

    ham_gozlem: int = 0
    temiz_gozlem: int = 0
    olcek_duzeltilen_pazarlar: dict[str, float] = field(default_factory=dict)
    mf_kirpilan: int = 0
    iade_gozlem: int = 0
    ilk_satis_oncesi_atilan: int = 0
    kisa_seriler: dict[tuple[str, str, str], int] = field(default_factory=dict)


def mf_olcek_tespit(df: pd.DataFrame) -> dict[str, float]:
    """Her pazar için MF biriminin ölçek faktörünü döndürür (1.0 veya 100.0).

    Kural veriden çıkar, pazar adından değil: pozitif MF değerlerinin medyanı 1'i
    aşıyorsa o pazar yüzde ölçeğindedir. Sıfırlar medyana katılmaz — MF'in çoğu ayda
    0 olduğu bir seride sıfırlar medyanı 0'a çeker ve ölçek sorunu gözden kaçardı.
    """
    faktorler: dict[str, float] = {}
    for pazar, grup in df.groupby("pazar", observed=True):
        pozitif = grup.loc[grup["mf_oran"].notna() & (grup["mf_oran"] > 0), "mf_oran"]
        medyan = pozitif.median()
        faktorler[str(pazar)] = 100.0 if pd.notna(medyan) and medyan > 1 else 1.0
    return faktorler


def temizle(df: pd.DataFrame) -> tuple[pd.DataFrame, VeriKalitesiRaporu]:
    """Yedi düzeltmeyi sırayla uygular ve kalite raporuyla birlikte döndürür."""
    rapor = VeriKalitesiRaporu(ham_gozlem=len(df))
    temiz = df.copy()

    # V7 — ürün adı normalizasyonu. Ölçek tespitinden önce gelir ki gruplama doğru olsun.
    temiz["urun"] = temiz["urun"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    # V2 — 🚨 MF ölçek düzeltmesi.
    faktorler = mf_olcek_tespit(temiz)
    rapor.olcek_duzeltilen_pazarlar = {p: f for p, f in faktorler.items() if f != 1.0}
    bolen = temiz["pazar"].astype(str).map(faktorler)
    temiz["mf_oran_olcekli"] = temiz["mf_oran"] / bolen

    # V3 — ölçek düzeltmesinden sonra bile kalan imkânsız değerleri kırp ve bayrakla.
    temiz["mf_kirpildi"] = temiz["mf_oran_olcekli"].notna() & (
        (temiz["mf_oran_olcekli"] < MF_ALT_SINIR) | (temiz["mf_oran_olcekli"] > MF_UST_SINIR)
    )
    temiz["mf_oran_temiz"] = temiz["mf_oran_olcekli"].clip(MF_ALT_SINIR, MF_UST_SINIR)
    rapor.mf_kirpilan = int(temiz["mf_kirpildi"].sum())

    # V4 — iadeler. Silinmez; toplamlarda kalır, tahmin girdisinde 0'lanır.
    temiz["iade_mi"] = (temiz["brut_kutu"] < 0) | (temiz["net_tl"] < 0)
    rapor.iade_gozlem = int(temiz["iade_mi"].sum())

    # V5 — serinin ilk pozitif satışından önceki dönem ürünün var olmadığı dönemdir.
    once = len(temiz)
    ilk_satis = temiz[temiz["brut_kutu"] > 0].groupby(ANAHTAR, observed=True)["tarih"].min()
    anahtar_indeks = pd.MultiIndex.from_frame(temiz[ANAHTAR].astype(str))
    baslangic = pd.Series(
        anahtar_indeks.map(ilk_satis.rename_axis(ilk_satis.index.names)), index=temiz.index
    )
    temiz = temiz[baslangic.notna() & (temiz["tarih"] >= baslangic)]
    rapor.ilk_satis_oncesi_atilan = once - len(temiz)

    temiz = temiz.reset_index(drop=True)
    rapor.temiz_gozlem = len(temiz)
    rapor.kisa_seriler = _kisa_seriler(temiz)
    return temiz, rapor


def _kisa_seriler(df: pd.DataFrame) -> dict[tuple[str, str, str], int]:
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
    satisli = df[df["brut_kutu"] > 0].groupby(ANAHTAR, observed=True).size()
    return {
        tuple(map(str, anahtar)): int(n) for anahtar, n in satisli.items() if n < KISA_SERI_ESIGI
    }
