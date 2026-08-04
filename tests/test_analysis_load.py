import pandas as pd
import pytest

from src.analysis.load import DATA_PATH, MONTH_NAMES, load_raw


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    if not DATA_PATH.exists():
        pytest.skip(f"veri seti yok: {DATA_PATH}")
    return load_raw()


def test_all_twelve_month_names_are_mapped():
    # Ay adları veride doğrulandı (bulgular §2.1); eksik ad sessizce NaT üretir.
    assert len(MONTH_NAMES) == 12
    assert MONTH_NAMES["Ocak"] == 1
    assert MONTH_NAMES["Aralık"] == 12


@pytest.mark.integration
def test_the_tidy_frame_carries_the_expected_columns(raw):
    assert list(raw.columns) == [
        "pazar",
        "sirket",
        "urun",
        "tarih",
        "brut_kutu",
        "mf_oran",
        "net_tl",
    ]


@pytest.mark.integration
def test_series_and_month_counts_match_the_measured_values(raw):
    # Bulgular §2.1: 374 series × 124 ay.
    assert raw["tarih"].nunique() == 124
    assert len(raw.groupby(["pazar", "sirket", "urun"], observed=True)) == 374


@pytest.mark.integration
def test_the_date_range_spans_2016_01_to_2026_04(raw):
    assert raw["tarih"].min() == pd.Timestamp("2016-01-01")
    assert raw["tarih"].max() == pd.Timestamp("2026-04-01")


@pytest.mark.integration
def test_key_month_pairs_are_unique(raw):
    assert not raw.duplicated(["pazar", "sirket", "urun", "tarih"]).any()


@pytest.mark.integration
def test_empty_cells_are_not_turned_into_zeros(raw):
    # Bulgular §2.4: 28.006 boş hücre ürün yaşam döngüsü, gerçek sıfır değil (V5).
    assert raw["brut_kutu"].isna().sum() > 0


@pytest.mark.integration
def test_company_one_has_eighteen_series(raw):
    # Bulgular §2.2: A'da 10, B'de 4, C'de 2, D'de 2.
    s1 = raw[raw["sirket"] == "Şirket 1"]
    assert len(s1.groupby(["pazar", "urun"], observed=True)) == 18


@pytest.mark.integration
def test_loading_does_not_depend_on_the_working_directory(raw, tmp_path, monkeypatch):
    # Notebook `notebooks/` içinden koşuyor; göreli path oradan çözülmezdi.
    monkeypatch.chdir(tmp_path)

    assert len(load_raw()) == len(raw)
