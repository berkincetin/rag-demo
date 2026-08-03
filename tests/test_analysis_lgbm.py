import numpy as np
import pandas as pd
import pytest

from src.analysis.forecast import MF_OZELLIKLERI, lgbm_walk_forward, ozellik_matrisi


def _seri(pazar, urun, aylar=40, baslangic=100.0):
    tarih = pd.date_range("2020-01-01", periods=aylar, freq="MS")
    return pd.DataFrame(
        {
            "pazar": pazar,
            "sirket": "Şirket 1",
            "urun": urun,
            "tarih": tarih,
            "brut_kutu": [baslangic + i + 10 * (t.month == 12) for i, t in enumerate(tarih)],
            "mf_oran_temiz": np.linspace(0.05, 0.25, aylar),
        }
    )


def test_ozellik_matrisi_lag_yonu_dogru():
    # 🚨 lag_1 gerçekten bir önceki ay olmalı; ters kaydırma sızıntıdır.
    df = _seri("A Pazarı", "Ürün-A", aylar=6, baslangic=100.0)

    matris = ozellik_matrisi(df).sort_values("tarih").reset_index(drop=True)

    assert np.isnan(matris.loc[0, "lag_1"])
    assert matris.loc[1, "lag_1"] == pytest.approx(matris.loc[0, "brut_kutu"])
    assert matris.loc[2, "lag_2"] == pytest.approx(matris.loc[0, "brut_kutu"])


def test_ozellik_matrisi_seri_sinirini_asmiyor():
    # 🚨 V6: bir serinin lag_1'i başka bir serinin son ayı olamaz.
    a = _seri("A Pazarı", "Ürün-A", aylar=4, baslangic=100.0)
    b = _seri("D Pazarı", "Ürün 77", aylar=4, baslangic=9000.0)

    matris = ozellik_matrisi(pd.concat([a, b]))
    ilk_b = matris[(matris["urun"] == "Ürün 77")].sort_values("tarih").iloc[0]

    assert np.isnan(ilk_b["lag_1"])


def test_mf_ablasyonunda_mf_kolonlari_yok():
    df = _seri("A Pazarı", "Ürün-A", aylar=8)

    matris = ozellik_matrisi(df, mf_dahil=False)

    assert not set(MF_OZELLIKLERI) & set(matris.columns)


def test_mf_dahilken_mf_kolonlari_var():
    df = _seri("A Pazarı", "Ürün-A", aylar=8)

    matris = ozellik_matrisi(df, mf_dahil=True)

    assert set(MF_OZELLIKLERI) <= set(matris.columns)


def test_lgbm_tahminleri_negatif_degil():
    # Hedef log1p ile dönüştürülüyor; geri çevirmede negatif çıkmamalı.
    df = pd.concat([_seri("A Pazarı", "Ürün-A"), _seri("B Pazarı", "Ürün-FR", baslangic=50.0)])

    sonuc = lgbm_walk_forward(df, ay_sayisi=2)

    assert len(sonuc) > 0
    assert (sonuc["tahmin"] >= 0).all()


def test_lgbm_ablasyonu_ayni_katmanlarda_karsilastiriyor():
    # İki model aynı hedef aylarda değerlendirilmezse delta anlamsız olur.
    df = pd.concat([_seri("A Pazarı", "Ürün-A"), _seri("B Pazarı", "Ürün-FR", baslangic=50.0)])

    mf_ile = lgbm_walk_forward(df, mf_dahil=True, ay_sayisi=2)
    mf_siz = lgbm_walk_forward(df, mf_dahil=False, ay_sayisi=2)

    anahtar = ["pazar", "urun", "tarih"]
    assert mf_ile[anahtar].reset_index(drop=True).equals(mf_siz[anahtar].reset_index(drop=True))


def test_lgbm_kisa_seriyi_hedef_yapmiyor_ama_egitimde_tutuyor():
    kisa = _seri("C Pazarı", "Ürün 1", aylar=3, baslangic=5.0)
    uzun = _seri("A Pazarı", "Ürün-A")

    sonuc = lgbm_walk_forward(pd.concat([kisa, uzun]), ay_sayisi=2)

    assert set(sonuc["urun"]) == {"Ürün-A"}


def test_hedef_secimi_indeks_etiketine_guvenmiyor():
    # Çağıran taraf indeksi sıfırlamamış olabilir. Aynı etiketi taşıyan ve aynı aya
    # düşen kısa bir seri, uzun serinin hedef satırıyla karışmamalı.
    uzun = _seri("A Pazarı", "Ürün-A", aylar=40)
    kisa = _seri("C Pazarı", "Ürün 1", aylar=3, baslangic=5.0)
    kisa["tarih"] = uzun["tarih"].to_numpy()[-3:]
    kisa.index = uzun.index[-3:]

    sonuc = lgbm_walk_forward(pd.concat([uzun, kisa]), ay_sayisi=2)

    assert set(sonuc["urun"]) == {"Ürün-A"}
    assert len(sonuc) == 2
