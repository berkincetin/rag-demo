import pandas as pd
import pytest

from src.analysis.load import AY_ADLARI, VERI_YOLU, yukle_ham


@pytest.fixture(scope="module")
def ham() -> pd.DataFrame:
    if not VERI_YOLU.exists():
        pytest.skip(f"veri seti yok: {VERI_YOLU}")
    return yukle_ham()


def test_ay_adlari_on_ikisi_de_var():
    # Ay adları veride doğrulandı (bulgular §2.1); eksik ad sessizce NaT üretir.
    assert len(AY_ADLARI) == 12
    assert AY_ADLARI["Ocak"] == 1
    assert AY_ADLARI["Aralık"] == 12


@pytest.mark.integration
def test_tidy_cerceve_beklenen_kolonlari_tasiyor(ham):
    assert list(ham.columns) == [
        "pazar",
        "sirket",
        "urun",
        "tarih",
        "brut_kutu",
        "mf_oran",
        "net_tl",
    ]


@pytest.mark.integration
def test_seri_ve_ay_sayisi_olculen_degerlerle_ayni(ham):
    # Bulgular §2.1: 374 seri × 124 ay.
    assert ham["tarih"].nunique() == 124
    assert len(ham.groupby(["pazar", "sirket", "urun"], observed=True)) == 374


@pytest.mark.integration
def test_tarih_araligi_2016_01_ile_2026_04_arasi(ham):
    assert ham["tarih"].min() == pd.Timestamp("2016-01-01")
    assert ham["tarih"].max() == pd.Timestamp("2026-04-01")


@pytest.mark.integration
def test_anahtar_ay_ciftleri_yinelenmiyor(ham):
    assert not ham.duplicated(["pazar", "sirket", "urun", "tarih"]).any()


@pytest.mark.integration
def test_bos_hucreler_sifira_cevrilmemis(ham):
    # Bulgular §2.4: 28.006 boş hücre ürün yaşam döngüsü, gerçek sıfır değil (V5).
    assert ham["brut_kutu"].isna().sum() > 0


@pytest.mark.integration
def test_sirket_1_on_sekiz_seriye_sahip(ham):
    # Bulgular §2.2: A'da 10, B'de 4, C'de 2, D'de 2.
    s1 = ham[ham["sirket"] == "Şirket 1"]
    assert len(s1.groupby(["pazar", "urun"], observed=True)) == 18


@pytest.mark.integration
def test_calisma_dizininden_bagimsiz_yukluyor(ham, tmp_path, monkeypatch):
    # Notebook `notebooks/` içinden koşuyor; göreli yol oradan çözülmezdi.
    monkeypatch.chdir(tmp_path)

    assert len(yukle_ham()) == len(ham)
