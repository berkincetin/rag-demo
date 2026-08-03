import numpy as np
import pandas as pd
import pytest

from src.analysis.clean import mf_olcek_tespit, temizle
from src.analysis.load import VERI_YOLU, yukle_ham


def _seri(pazar, sirket, urun, aylar, brut, mf, net_tl=None):
    """Tek bir (pazar, şirket, ürün) serisi için küçük kurgu çerçeve."""
    return pd.DataFrame(
        {
            "pazar": pazar,
            "sirket": sirket,
            "urun": urun,
            "tarih": pd.date_range("2020-01-01", periods=aylar, freq="MS"),
            "brut_kutu": brut,
            "mf_oran": mf,
            "net_tl": net_tl if net_tl is not None else [1000.0] * aylar,
        }
    )


@pytest.fixture(scope="module")
def ham() -> pd.DataFrame:
    if not VERI_YOLU.exists():
        pytest.skip(f"veri seti yok: {VERI_YOLU}")
    return yukle_ham()


@pytest.mark.integration
def test_mf_olcek_tespiti_yalnizca_b_pazarini_yuzde_kabul_eder(ham):
    # 🚨 Projenin en kritik testi. Bulgular §2.3: B'de medyan 5,9–7,4, diğerlerinde ~0.
    # Bu düzeltme olmadan Net Kutu negatife düşer ve A4/A6/A7 tamamen yanlış olur.
    faktorler = mf_olcek_tespit(ham)

    assert faktorler["B Pazarı"] == 100.0
    assert faktorler["A Pazarı"] == 1.0
    assert faktorler["C Pazarı"] == 1.0
    assert faktorler["D Pazarı"] == 1.0


def test_olcek_tespiti_sabit_pazar_adi_kullanmiyor():
    # Kural veriden gelmeli, addan değil: adı B olmayan yüzde ölçekli bir pazar da
    # yakalanmalı, adı B olan oran ölçekli bir pazar ise yakalanmamalı.
    df = pd.concat(
        [
            _seri("Z Pazarı", "Şirket 1", "Ürün-Z", 4, [10.0] * 4, [7.0, 6.0, 8.0, 5.0]),
            _seri("B Pazarı", "Şirket 1", "Ürün-B", 4, [10.0] * 4, [0.1, 0.2, 0.15, 0.05]),
        ]
    )

    faktorler = mf_olcek_tespit(df)

    assert faktorler["Z Pazarı"] == 100.0
    assert faktorler["B Pazarı"] == 1.0


def test_olcek_tespiti_sifirlari_medyana_katmiyor():
    # MF'in çoğu ayda 0 olduğu bir yüzde ölçekli seride, sıfırlar medyana katılırsa
    # medyan 0 çıkar ve ölçek sorunu gözden kaçar.
    df = _seri("Y Pazarı", "Şirket 1", "Ürün-Y", 6, [10.0] * 6, [0.0, 0.0, 0.0, 0.0, 8.0, 9.0])

    assert mf_olcek_tespit(df)["Y Pazarı"] == 100.0


@pytest.mark.integration
def test_duzeltme_sonrasi_b_pazari_birim_fiyati_pozitif(ham):
    # 🚨 Bulgular §2.3: düzeltmesiz 2016-01'de −0,88 TL, düzeltmeli 8,32 TL.
    temiz, _ = temizle(ham)
    satir = temiz[
        (temiz["pazar"] == "B Pazarı")
        & (temiz["sirket"] == "Şirket 1")
        & (temiz["urun"] == "Ürün-FR")
        & (temiz["tarih"] == pd.Timestamp("2016-01-01"))
    ].iloc[0]

    net_kutu = satir["brut_kutu"] * (1 - satir["mf_oran_temiz"])
    birim_fiyat = satir["net_tl"] / net_kutu

    assert birim_fiyat == pytest.approx(8.32, abs=0.05)


def test_urun_adlari_normalize_ediliyor():
    # Bulgular §2.4: C/D pazarlarında `Ürün  2` (çift boşluk) geçiyor.
    df = _seri("C Pazarı", "Şirket 1", "Ürün  2", 3, [1.0, 2.0, 3.0], [0.0] * 3)

    temiz, _ = temizle(df)

    assert temiz["urun"].unique().tolist() == ["Ürün 2"]


def test_mf_kirpma_ust_siniri_uyguluyor():
    # Bulgular §2.4: ölçek düzeltmesinden sonra bile 469,5 gibi imkânsız değerler var.
    df = _seri("A Pazarı", "Şirket 1", "Ürün-A", 3, [10.0] * 3, [0.2, 469.5, -0.3])

    temiz, rapor = temizle(df)

    assert temiz["mf_oran_temiz"].max() <= 0.95
    assert temiz["mf_oran_temiz"].min() >= 0.0
    assert temiz["mf_kirpildi"].sum() == 2
    assert rapor.mf_kirpilan == 2


def test_iadeler_silinmiyor_bayraklaniyor():
    # V4: iade kayıtları toplamlarda kalmalı, yoksa hacim şişer.
    df = _seri("A Pazarı", "Şirket 1", "Ürün-A", 3, [10.0, -5.0, 8.0], [0.0] * 3)

    temiz, rapor = temizle(df)

    assert len(temiz) == 3
    assert temiz["iade_mi"].sum() == 1
    assert rapor.iade_gozlem == 1


def test_ilk_satistan_onceki_aylar_atiliyor():
    # V5: ilk pozitif satıştan önceki dönem ürün yok demektir; sonraki sıfır gerçek sıfır.
    df = _seri("A Pazarı", "Şirket 1", "Ürün-A", 5, [0.0, 0.0, 7.0, 0.0, 3.0], [0.0] * 5)

    temiz, rapor = temizle(df)

    assert len(temiz) == 3
    assert temiz["tarih"].min() == pd.Timestamp("2020-03-01")
    assert rapor.ilk_satis_oncesi_atilan == 2


def test_hic_satis_gormemis_seri_tamamen_dusuyor():
    df = _seri("A Pazarı", "Şirket 1", "Ürün-A", 3, [0.0, np.nan, 0.0], [0.0] * 3)

    temiz, _ = temizle(df)

    assert temiz.empty


@pytest.mark.integration
def test_rapor_kisa_serileri_listeliyor(ham):
    # Bulgular §2.5: C/Ürün 1 tek satışlı, D/Ürün 78 on bir aylık — gizlenmemeli.
    # Uzunluk satır sayısıyla ölçülseydi C/Ürün 1 kırpma sonrası 27 satırla
    # "yeterli geçmişi var" görünürdü; oysa 26'sı gerçek sıfır.
    _, rapor = temizle(ham)

    assert rapor.kisa_seriler[("C Pazarı", "Şirket 1", "Ürün 1")] == 1
    assert rapor.kisa_seriler[("D Pazarı", "Şirket 1", "Ürün 78")] == 11


@pytest.mark.integration
def test_rapor_sayilari_gercek_veriyle_tutarli(ham):
    # Bulgular §2.4: 1.158 negatif Brüt Kutu, 1.168 negatif Net TL → birleşik bayrak.
    _, rapor = temizle(ham)

    assert rapor.olcek_duzeltilen_pazarlar == {"B Pazarı": 100.0}
    assert rapor.ham_gozlem > rapor.temiz_gozlem
    assert rapor.iade_gozlem > 1000
