"""Ortak grafik stili: Türkçe etiketler, sabit palet, PNG yazıcı.

Notebook'taki her grafik buradan geçer ki dört pazarın rengi her figürde aynı olsun
ve sayılar Türkçe biçimde (binlik nokta, ondalık virgül) yazılsın.
"""

from pathlib import Path

import matplotlib.pyplot as plt

# Depo köküne göre mutlak: notebook `notebooks/` içinden koşuyor ve göreli bir
# varsayılan figürleri `notebooks/figures/` altına yazıyordu.
FIGURE_DIR = Path(__file__).resolve().parents[2] / "figures"

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
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def save_figure(fig, name: str, directory: Path = FIGURE_DIR) -> Path:
    """Figürü PNG olarak yazar ve yolunu döndürür."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    return path
