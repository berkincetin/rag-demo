import matplotlib

matplotlib.use("Agg")  # Testler başsız koşar; pencere açılmamalı.

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from src.analysis.plots import (  # noqa: E402
    COMPANY_COLORS,
    FIGURE_DIR,
    MARKET_COLORS,
    apply_style,
    save_figure,
    tr_number,
)


def test_turkish_number_uses_dot_thousands_and_comma_decimals():
    assert tr_number(1234567.8, decimals=1) == "1.234.567,8"


def test_turkish_number_rounds_without_decimals():
    assert tr_number(1234.6) == "1.235"


def test_turkish_number_handles_negatives_and_zero():
    assert tr_number(-1234.5, decimals=1) == "-1.234,5"
    assert tr_number(0) == "0"


def test_all_four_markets_have_a_colour():
    # Grafiğin ortasında KeyError almamak için palet eksiksiz olmalı.
    for pazar in ("A Pazarı", "B Pazarı", "C Pazarı", "D Pazarı"):
        assert pazar in MARKET_COLORS


def test_all_three_companies_have_a_colour():
    for sirket in ("Şirket 1", "Şirket 2", "Diğer Şirket"):
        assert sirket in COMPANY_COLORS


def test_saving_writes_a_png_and_returns_its_path(tmp_path):
    fig, axis = plt.subplots()
    axis.plot([1, 2, 3], [1, 4, 9])

    path = save_figure(fig, "deneme", directory=tmp_path)
    plt.close(fig)

    assert path == tmp_path / "deneme.png"
    assert path.stat().st_size > 0


def test_applying_the_style_sets_the_shared_defaults():
    apply_style()

    assert plt.rcParams["axes.grid"] is True
    assert plt.rcParams["figure.dpi"] == pytest.approx(110)


def test_the_default_figure_directory_is_working_directory_independent(tmp_path, monkeypatch):
    # Notebook `notebooks/` içinden koşuyor; göreli varsayılan figürleri oraya yazardı.
    monkeypatch.chdir(tmp_path)

    assert FIGURE_DIR.is_absolute()
    assert FIGURE_DIR.name == "figures"
